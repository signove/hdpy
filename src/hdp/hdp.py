#!/usr/bin/env python
# -*- coding: utf-8

################################################################
#
# Copyright (c) 2010 Signove. All rights reserved.
# See the COPYING file for licensing details.
#
# Autors: Elvis Pfützenreuter < epx at signove dot com >
#         Raul Herbster < raul dot herbster at signove dot com >
################################################################

import sys
from mcap.mcap_instance import MCAPInstance
from mcap.mcap_loop import watch_fd, IO_IN, schedule
from mcap.misc import BlueZ
from . import hdp_record


class HealthError(Exception):
	pass


class HealthManager(object):
	def __init__(self):
		self.applications = []
		pass

	def CreateApplication(self, agent, config): # -> HealthApplication
		application = HealthApplication(agent, config)
		if not application:
			return None
		self.applications.append(application)
		return application

	def DestroyApplication(self, application):
		application.stop()
		self.applications.remove(application)

	def UpdateServices(self):
		# TODO searches remote devices
		pass


class HealthApplication(MCAPInstance):
	def __init__(self, agent, config):
		if not isinstance(agent, HealthAgent):
			raise HealthError("Bad agent superclass")

		self.agent = agent

		err = self.process_config(config)
		if err:
			raise HealthError("Bad config: %s" % err)

		MCAPInstance.__init__(self, adapter="", listen=True)

		self.mdl_watch(False)

		self.services = [] # relationship 1:(0,1) with MCL
		self.channels = [] # relationship 1:1 with MDL
		self.stopped = False

		self.publish()

	def process_config(self, config):
		self.sdp_record = {'features': []}
		self.sdp_handle = None

		auto_mdepid = 1
		is_auto_id = True

		role = config["Role"]

		if role not in ("Source", "Sink"):
			return "Role must be 'Source' or 'Sink'"

		self.sink = (role == "Sink" and 1 or 0)

		if 'MDEPID' not in config:
			self.mdepid = 1
		else:
			self.mdepid = config['MDEPID']
			if self.mdepid <= 0:
				return "MDEP ID must be positive"

		if self.sink:
			if 'ChannelType' in config:
				return "Sinks don't specify config"
			self.channel_type = 0 # Any
		else:
			self.channel_type = 'Reliable'
			if 'ChannelType' in config:
				self.channel_type = config['ChannelType']
			if self.channel_type == 'Reliable':
				self.channel_type = 1
			elif self.channel_type == 'Streaming':
				self.channel_type = 2
			else:
				return "Source channel type must be " \
					"Reliable or Streaming"

		self.data_type = config["DataType"]

		if self.data_type < 0 or self.data_type > 65535:
			return "Bad data type"

		self.description = ""

		if 'Description' in config: 
			self.description = config["Description"][:240]

		self.sdp_record['features'].append({
			'mdep_id': self.mdepid,
			'role': role.lower(),
			'data_type': self.data_type,
			'description': self.description})

		return None

	def publish(self):
		self.sdp_handle = None

		r = self.sdp_record
		r['mcap_control_psm'] = self.cpsm
                r['mcap_data_psm'] = self.dpsm
                r['name'] = 'HDPy'
                r['provider'] = 'HDPy'
                r['description'] = 'HDPy'

		procedures = []
		if self.reconn_enabled:
			procedures.append('reconnect_init')
			procedures.append('reconnect_accept')
		if self.csp_enabled:
			procedures.append('csp')
			procedures.append('csp_master')
			
                r['mcap_procedures'] = tuple(procedures)

		xml_record = hdp_record.gen_xml(self.sdp_record)
		self.sdp_handle = BlueZ().add_record("any", xml_record)

	def unpublish(self):
		if not self.sdp_handle:
			return
		try:
			BlueZ().remove_record("any", self.sdp_handle)
		except:
			pass
		self.sdp_handle = None

	def stop(self):	
		self.stopped = True

		while self.services:
			self.remove_service(self.services[-1])

		self.agent.Release()
		self.agent = None

		self.unpublish()
		MCAPInstance.stop(self)

	def channel_by_mdl(self, mdl):
		channel = self.got_channel_by_mdl(mdl)
		if not channel:
			print "WARNING: No channel for the given MDL"
		return channel

	def got_channel_by_mdl(self, mdl):
		channel = None
		for candidate in self.channels:
			if candidate.mdl is mdl:
				channel = candidate
				break
		return channel

	def create_channel(self, mdl, acceptor):
		service = self.service_by_mcl(mdl.mcl)
		channel = HealthChannel(service, mdl, acceptor)
		self.add_channel(channel)
		return channel

	def add_channel(self, channel):
		if channel not in self.channels:
			self.channels.append(channel)

	def remove_channel(self, channel):
		try:
			self.channels.remove(channel)
		except ValueError:
			print "WARNING: Channel unknown, not removed"

	def service_by_mcl(self, mcl):
		service = None
		for candidate in self.services:
			if candidate.mcl is mcl:
				service = candidate
				break
		if not service:
			# Case when we are acceptors of MCL
			service = self.create_service_by_mcl(mcl)
		return service

	def create_service_by_mcl(self, mcl):
		service = HealthService(self, mcl.remote_addr,
					mcl.remote_addr_dc, 0)
		self.add_service(service)
		return service

	def create_service(self, control_addr, data_addr, mdepid):
		service = HealthService(self, control_addr, data_addr, mdepid)
		self.add_service(service)
		return service

	def add_service(self, service):
		if service not in self.services:
			self.services.append(service)
			self.agent.ServiceDiscovered(service)

	def remove_service(self, service):
		try:
			service.kill()
			self.services.remove(service)
			self.agent.ServiceRemoved(service)
		except ValueError:
			print "Warning: service %s unkown, not removed"

	def MCLConnected(self, mcl, err):
		if self.stopped:
			return

		service = self.service_by_mcl(mcl)
		service.mcl_connected(mcl, err, False)

	def MCLDisconnected(self, mcl):
		if self.stopped:
			return

		service = self.service_by_mcl(mcl)
		service.mcl_disconnected(mcl)

	def MCLReconnected(self, mcl, err):
		if self.stopped:
			return

		service = self.service_by_mcl(mcl)
		service.mcl_connected(mcl, err, True)

	def MCLUncached(self, mcl):
		if self.stopped:
			return

		service = self.service_by_mcl(mcl)
		service.mcl_deleted(mcl)

	def MDLInquire(self, mdepid, config):
		if self.stopped:
			return

		if mdepid == 0:
			# echo channel
			ok = True
			final_config = config or 0x01
			reliable = (final_config == 0x01)
			return ok, reliable, final_config

		ok = mdepid == self.mdepid

		if not ok:
			print "requested MDEP ID %d not in our list" % mdepid

		our_config = self.channel_type
		final_config = config or our_config

		if not final_config:
			print "Remove side should have chosen config, nak"
			ok = False
		elif our_config and (final_config != our_config):
			print "MDEP reqs config %d, we want %d, nak" \
				% (config, our_config)
			ok = False

		reliable = (final_config == 0x01)

		return ok, reliable, final_config

	def MDLReady(self, mcl, mdl, err):
		if self.stopped:
			return

		if err:
			service = self.service_by_mcl(mcl)
			service.mdl_ready(mdl, err)
			return

		# Nothing to do except go ahead
		self.ConnectMDL(mdl)

	def MDLRequested(self, mcl, mdl, mdep_id, conf):
		# already dealt with in MDLInquire
		pass

	def MDLReconnected(self, mdl):
		# we are only interested in MDLConnected
		pass

	def MDLAborted(self, mcl, mdl):
		# we do not initiate AbortMDL() and 
		# we are only interested in MDLConnected
		pass

	def MDLConnected(self, mdl, err):
		if self.stopped:
			return

		service = self.service_by_mcl(mdl.mcl)
		channel = self.got_channel_by_mdl(mdl)
		reconn = channel is not None

		if err:
			service.mdl_connected(mdl, channel, reconn, err)
			return

		if mdl.mdepid == 0:
			return self.MDLConnectedEcho(mdl)

		if mdl.acceptor:
			if mdl.mdepid != self.mdepid:
				print "MDLConnected: bad MDEP ID received"
				mdl.close()
				return

		if not reconn:
			channel = self.create_channel(mdl, mdl.acceptor)

		if mdl.acceptor:
			self.agent.ChannelConnected(channel)

		service.mdl_connected(mdl, channel, reconn, err)

	def MDLConnectedEcho(self, mdl):
		watch_fd(mdl.sk, self.echo_watch, mdl)
		if not mdl.acceptor:
			service = self.service_by_mcl(mdl.mcl)
			service.mdlecho_connected(mdl)

	def echo_watch(self, sk, evt, mdl):
		data = ""
		if evt & IO_IN:
			data = sk.recv()

		if not mdl.acceptor:
			service = self.service_by_mcl(mdl.mcl)
			service.mdlecho_pong(mdl, data)
		else:
			if data:
				# send back the same data and close
				mdl.write(data)

		self.DeleteMDL(mdl)
		return False

	def MDLDeleted(self, mdl):
		if self.stopped:
			return

		if mdl.mdepid == 0:
			return

		channel = self.got_channel_by_mdl(mdl)
		if channel:
			service = self.service_by_mcl(mdl.mcl)
			self.remove_channel(channel)
			self.agent.ChannelDeleted(channel)

	def MDLClosed(self, mdl):
		# Application discovers this via fd closure
		pass

	### Public HealthApplication API

	def Echo(self, service, reply_handler, error_handler):
		"""
		Sends an echo petition to the remote service. Calls error
		handler in case of error.
		"""
		service._Echo(reply_handler, error_handler)

	def CreateChannel(self, service, conf, reply_handler, error_handler):
		"""
		Creates a data channel with the given service
		"""
		if not service.mdepid:
			raise HealthError("This service is acceptor-only")

		try:
			conf = {"Reliable": 1, "Streaming": 2, "Any": 0}[conf]
		except KeyError:
			raise HealthError("Invalid channel config")

		service._CreateChannel(conf, reply_handler, error_handler)

	def DestroyChannel(self, channel):
		if channel.valid:
			channel.valid = False
			channel.service._DeleteChannel(channel)
		return True


class QueueItem(object):
	'''
	This is an auxiliary class that represents a queued
	operation.

	operation: function/method to be called when queue dispatches.
		   Prototype is op(arg, queue_item)
	arg: a single argument for operation. May be a tuple if several
		arguments must be passed, but it is NOT expanded.
	cb_ok, cb_err: callbacks to be notified on success or failure,
		   respectively
	ident: some 'cargo' data that may be needed when async operation
 		completes, so we can check if the completed operation
		matches with the queue item being processed.
	'''
	def __init__(self, operation, arg, cb_ok, cb_err, ident):
		self.operation = operation
		self.arg = arg
		self.cb_ok = cb_ok
		self.cb_err = cb_err
		self.ident = ident

	def start():
		self.operation(self.arg, self)

	def ok(*args):
		if self.cb_ok:
			self.cb_ok(*args)
			self.cb_ok = None

	def nok(*args):
		if self.cb_nok:
			self.cb_nok(*args)
			self.cb_nok = None


class HealthService(object):
	'''
	The HealthService is a class with no public APIs that encapsulates
	the MCL. Moreover, in this API, it represents a single (endpoint,
	role, data_type) in the remote device.

	Each service is bound to a given HealthApplication object, so
	data_type and role are implicitly defined (being the remote device's
	role the opposite of our application's).

	The MDEP ID is also known by this class, if the remote device
	publishes a SDP record. If not, or if this service is created
	automatically when we are acceptors, MDEP ID is zero.
	'''

	# Current queue processing status
	IDLE = 0
	WAITING_MCL = 1
	WAITING_MDL = 2 # used by _Echo() only
	IN_FLIGHT = 3

	CONNECTION = 1
	DISCONNECTION = 2
	DELETION = 3
	MDL_READY = 4
	MDL_CONNECTION = 5
	MDL_ECHO_CONNECTION = 6

	def __init__(self, app, addr_control, addr_data, mdepid):
		self.addr_control = addr_control
		self.addr_data = addr_data
		self.mdepid = mdepid
		self.app = app
		self.mcl = None
		self.queue = []
		self.queue_status = self.IDLE
		self.valid = True
		self.mdl_echo = None

	def in_flight(self):
		if self.queue_status == self.IDLE or not self.queue:
			return None
		return self.queue[0]

	def mcl_connected(self, mcl, err, reconn):
		'''
		Called back by app when related MCL is connected
		'''
		self.mcl = mcl
		self.queue_event_process(self.CONNECTION, err)

	def mcl_disconnected(self, mcl):
		'''
		Called back by app when MCL is disconnected
		'''
		self.queue_event_process(self.DISCONNECTION, 0)

	def mcl_deleted(self, mcl):
		'''
		Called back by app when MCL is invalidated
		'''
		self.mcl = None
		self.queue_event_process(self.DELETION, 0)

	def mdl_ready(self, mdl, err):
		'''
		Called back by app when MDLReady triggers
		'''
		self.queue_event_process(self.MDL_READY, err)

	def mdl_connected(self, mdl, channel, reconn, err):
		'''
		Called back by app when MDLConnected triggers
		'''
		self.queue_event_process(self.MDL_CONNECTION, err,
			{"channel": channel, "reconn": reconn})

	def mdlecho_connected(self, mdl):
		'''
		Called back when an Echo MDL initiated by us has connected
		'''
		self.queue_event_process(self.MDL_ECHO_CONNECTION, 0,
			{"mdl": mdl})

	def mdlecho_pong(self, mdl, data):
		'''
		Called back when an Echo MDL returned data
		'''
		pending = self.in_flight()
		if not pending:
			return

		if pending.operation is self.__Echo:
			if data == pending.ident:
				pending.ok()
			else:
				pending.nok(-99)
			self.queue_flush()

	def stop(self):
		'''
		Called back by app when it is being stopped
		'''
		self.queue = []
		self.queue_state = self.IDLE

	def kill(self):
		self.stop()
		if self.mcl:
			self.app.DeleteMCL(self.mcl)
		self.valid = False
		self.mcl = None
		self.app = None

	def queue_event_process(self, event, err, details={}):
		'''
		Handles queue in face of events
		'''

		if not self.queue or not event:
			return

		if err:
			self.queue_fail(err)
			return

		if event == self.CONNECTION:
			self.queue_mcl_conn_up()

		elif event == self.DISCONNECTION:
			self.queue_fail(-998)

		elif event == self.DELETION:
			self.queue_fail(-999)

		elif event == self.MDL_READY:
			pass

		elif event == self.MDL_CONNECTION:
			self.queue_mdl_conn_up(details["channel"],
						details["reconn"])

		elif event == self.MDL_ECHO_CONNECTION:
			self.queue_mdl_echo_conn_up(details["mdl"])

	def queue_mcl_conn_up(self):
		'''
		Called when a connection is successful
		'''
		if self.queue_status == self.WAITING_MCL:
			self.queue_status = self.IDLE

		self.queue_dispatch()

	def queue_mdl_conn_up(self, channel, reconn):
		pending = self.in_flight()
		if not pending:
			return

		op = pending.operation

		if not reconn and op is self._OpenChannel:
			mdlid = channel.mdl.mdlid
			if pending.ident == mdlid:
				pending.ok(channel)
				self.queue_flush()
			else:
				print "queue_mdl_conn_up bad ID %d" % mdlid

		if reconn and op is self._ReconnectChannel:
			if channel is pending.ident:
				pending.ok()
				self.queue_flush()
			else:
				print "queue_mdl_conn_up reconn diff chan"

	def queue_mdl_echo_conn_up(self, mdl):
		if self.queue_status == self.WAITING_MDL:
			self.queue_status = self.IDLE

		self.echo_mdl = mdl
		self.queue_dispatch()

	def queue_fail(self, err):
		pending = self.in_flight()
		if pending:
			pending.nok(err)
			self.queue_flush()
		else:
			self.queue_dispatch()

	def queue_flush(self):
		del self.queue[0]
		self.queue_status = self.IDLE
		self.queue_priv = None
		self.queue_dispatch()

	def queue_dispatch(self):
		if not self.queue:
			return False

		if self.queue_status != self.IDLE:
			# waiting for something to happen
			return False

		if not self.mcl or not self.mcl.active():
			# we can't do nothing if MCL is not up
			self.queue_status = self.WAITING_MCL
			self.mcl = self.app.CreateMCL(self.addr_control,
						self.addr_data[1])
			return False

		if not self.mcl.clear_to_send():
			# some other MCL operation in flight, might have been
			# initiated by remote, we wait a bit and try again
			timeout_call(1000, self.queue_dispatch)
			return False

		if self.queue[0][0] is self.__Echo:
			# for Echo, we need the echo MDL up, too
			if not self.mdl_echo:
				self.queue_status = self.WAITING_MDL
				mdlid = self.app.CreateMDLID(self.mcl)
				self.app.CreateMDL(self.mcl, mdlid,
							0, 1, True)
				return False

		self.queue_execute()
		return False

	def queue_execute(self):
		self.queue_status = self.IN_FLIGHT
		pending = self.in_flight()
		if pending:
			pending.start()

	def enqueue(self, op, arg, reply, error, ident=None):
		qitem = QueueItem(op, arg, reply, error, ident)
		self.queue.append(qitem)
		self.queue_dispatch()

	def _Echo(self, reply_handler, error_handler):
		self.enqueue(self.__Echo, None, reply_handler, error_handler)

	def __Echo(self, dummy, queueop):
		length = random.randint(1, 48)
		data = [ chr(random.randint(0, 255)) for x in range(0, length) ]
		data = "".join(data)
		queueop.ident = data
		self.mdl_echo.send(data)

	def _CreateChannel(self, conf, reply_handler, error_handler):
		try:
			conf = {"Reliable": 1, "Streaming": 2, "Any": 0}[conf]
			reliable = (conf == 0x01)
		except KeyError:
			raise HealthError("Invalid channel config")

		self.enqueue(self.__CreateChannel, (conf, reliable),
				reply_handler, error_handler)

	def __CreateChannel(self, args, queueop):
		conf, reliable = args
		mdlid = self.app.CreateMDLID(self.mcl)
		queueop.ident = mdlid
		self.app.CreateMDL(self.mcl, mdlid, self.mdepid, conf, reliable)

	def _DeleteChannel(self, channel):
		self.enqueue(self.__DeleteChannel, channel, None, None)

	def __DeleteChannel(self, channel, queueop):
		app.DeleteMDL(channel.mdl)

	def _ReconnectChannel(self, channel, reply_handler, error_handler):
		self.enqueue(self.__ReconnectChannel, channel,
				reply_handler, error_handler)

	def __ReconnectChannel(self, channel, queueop):
		mdl = channel.mdl
		queueop.ident = channel
		self.app.ReconnectMDL(mdl)


class HealthChannel(object):
	def __init__(self, service, mdl, acceptor):
		self.service = service
		self.mdl = mdl
		self.acceptor = acceptor
		self.valid = True

	def GetProperties(self):
		if not self.valid:
			raise HealthError("Data channel deleted")
		data_type = self.mdl.reliable and "Reliable" or "Streaming"
		return {"Type": data_type, "Service": self.service}

	def Acquire(self, reply_handler, error_handler):
		if not self.valid:
			raise HealthError("Data channel deleted")

		if self.mdl.active():
			schedule(reply_handler, self.mdl.sk)
			return

		# Pass this closure as reply handler
		def reconnected():
			reply_handler(self.mdl.sk)

		self.service._ReconnectChannel(self, reconnected,
							error_handler)

	def Release(self):
		self.mdl.close()

	def stop(self):
		self.Release()


# This agent has two methods (ServiceDiscovered and ServiceRemoved)
# that are actually signals in BlueZ Health API.

class HealthAgent(object):
	def Release(self):
		pass

	def ServiceDiscovered(self, service):
		print "HealthAgent.ServiceDiscovered not overridden"
		pass

	def ServiceRemoved(self, service):
		print "HealthAgent.ServiceRemoved not overridden"
		pass

	def ChannelConnected(self, channel):
		print "HealthAgent.ChannelConnected not overridden"
		pass

	def ChannelDeleted(service, channel):
		print "HealthAgent.ChannelDeleted not overridden"
		pass

# FIXME capture all "normal" InvalidOperation exceptions
# FIXME test echo between two HDPys, and HDPy x instance
