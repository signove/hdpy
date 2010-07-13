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
		# FIXME do this for every adapter
		self.sdp_handle = BlueZ().add_record(None, xml_record)

	def unpublish(self):
		if not self.sdp_handle:
			return
		# FIXME do this for every adapter
		BlueZ().remove_record("", self.sdp_handle)
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

		if err:
			service.mdl_connected(mdl, None, err)
			return

		if mdl.mdepid == 0:
			return self.MDLConnectedEcho(mdl)

		if mdl.acceptor:
			if mdl.mdepid != self.mdepid:
				print "MDLConnected: bad MDEP ID received"
				mdl.close()
				return

		channel = self.got_channel_by_mdl(mdl)
		reconn = channel is not None

		if not reconn:
			channel = self.create_channel(mdl, mdl.acceptor)

		if mdl.acceptor:
			self.agent.ChannelConnected(channel)

		service.mdl_connected(mdl, channel, err)

	def MDLConnectedEcho(self, mdl):
		# FIXME set up watch
		if not mdl.acceptor:
			service.mdlecho_connected(mdl)

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
			channel.service._DeleteMDL(self.mdl)
		return True


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

	def mcl_connected(self, mcl, err, reconn):
		'''
		Called back by app when related MCL is connected
		'''
		self.mcl = mcl
		self.process_queue(self.CONNECTION, err, None)

	def mcl_disconnected(self, mcl):
		'''
		Called back by app when MCL is disconnected
		'''
		self.process_queue(self.DISCONNECTION, 0, None)

	def mcl_deleted(self, mcl):
		'''
		Called back by app when MCL is invalidated
		'''
		self.mcl = None
		self.process_queue(self.DELETION, 0, None)

	def mdl_ready(self, mdl, err):
		'''
		Called back by app when MDLReady triggers
		'''
		self.process_queue(self.MDL_READY, err, None)

	def mdl_connected(self, mdl, channel, err):
		'''
		Called back by app when MDLConnected triggers
		'''
		self.process_queue(self.MDL_CONNECTION, err, channel)

	def mdlecho_connected(self, mdl):
		'''
		Called back when an Echo MDL initiated by us has connected
		'''
		self.process_queue(self.MDL_ECHO_CONNECTION, 0, None)

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

	def process_queue(self, event, err, other):
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
		if event == self.DISCONNECTION:
			self.queue_fail(-998)
		if event == self.DELETION:
			self.queue_fail(-999)
		elif event == self.MDL_READY:
			pass
		elif event == self.MDL_CONNECTION:
			self.queue_mdl_conn_up(other)
		elif event == self.MDL_ECHO_CONNECTION:
			self.queue_mdl_echo_conn_up(mdl)

	def queue_mcl_conn_up(self):
		'''
		Called when a connection is successful
		'''
		if self.queue_status == self.WAITING_MCL:
			self.queue_status = self.IDLE

		self.dispatch_queue()

	def queue_mdl_conn_up(self, channel):
		if self.queue[0][0] is self._OpenChannel:
			# we are expecting for this
			self.queue[0][2](self.new_channel)

	def queue_mdl_echo_conn_up(self, mdl):
		if self.queue_status == self.WAITING_MDL:
			self.queue_status = self.IDLE

		self.echo_mdl = mdl
		self.dispatch_queue()

	def queue_fail(self, err):
		if self.queue_status != self.IDLE:
			self.queue[0][3](err)
			del self.queue[0]
			self.queue_status = self.IDLE

		self.dispatch_queue()

	def dispatch_queue(self):
		if not self.queue:
			return

		# FIXME protection against crossing requests
		# FIXME easy way: 1-second timeout -> stop() consequences

		if self.queue_status != self.IDLE:
			# waiting for something to happen
			return

		if not self.mcl or not self.mcl.active():
			self.queue_status = self.WAITING_MCL
			self.mcl = self.app.CreateMCL(self.addr_control,
						self.addr_data[1])
			return

		if self.queue[0][0] is self.__Echo:
			if not self.mdl_echo:
				self.queue_status = self.WAITING_MDL
				mdlid = self.app.CreateMDLID(self.mcl)
				self.app.CreateMDL(self.mcl, mdlid,
							0, 1, True)

		self.queue_execute()

	def queue_execute(self):
		self.queue_status = self.IN_FLIGHT
		command, args, reply_cb, error_cb = self.queue[0]
		command(args, reply_cb, error_cb)

	def _Echo(self, reply_handler, error_handler):
		self.queue.append(self.__Echo, reply_handler, error_handler)
		self.dispatch_queue()

	def __Echo(self, args, reply_handler, error_handler):
		self.mdl_echo.send(data)
		# FIXME where feedback comes from?

	def _CreateChannel(self, conf, reply_handler, error_handler):
		try:
			conf = {"Reliable": 1, "Streaming": 2, "Any": 0}[conf]
			reliable = (conf == 0x01)
		except KeyError:
			raise HealthError("Invalid channel config")

		self.queue.append(self.__CreateChannel,
				(conf, reliable),
				reply_handler, error_handler)

		self.dispatch_queue()

	def __CreateChannel(self, args, reply_handler, error_handler):
		conf, reliable = args
		mdlid = self.app.CreateMDLID(self.mcl)
		self.app.CreateMDL(self.mcl, mdlid, self.mdepid, conf, reliable)

	def _DeleteMDL(self, mdl):
		self.queue.append(self.__DeleteMDL, (mdl,), None, None)
		self.dispatch_queue()

	def __DeleteMDL(self, args, reply_handler, error_handler):
		mdl = args[0]
		app.DeleteMDL(mdl)

	def _ReconnectMDL(self, mdl, reply_handler, error_handler):
		self.queue.append(self.__ReconnectMDL, (mdl,), reply_handler,
								error_handler)
		self.dispatch_queue()

	def __ReconnectMDL(self, args, reply_handler, error_handler):
		mdl = args[0]
		self.app.ReconnectMDL(self.mdl)
		# FIXME Reconnection feedback? and err?


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

	def Acquire(self):
		if not self.valid:
			raise HealthError("Data channel deleted")
		return self.mdl.sk

		# FIXME reconnect if closed
		# FIXME reconection locally not supported
		# FIXME reconnection remotely not supported
		# self.service._ReconnectMDL(self.mdl, reply_handler,
		#					error_handler)

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
