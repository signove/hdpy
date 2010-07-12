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

# TODO remove this hack someday
sys.path.insert(0, "..")

from mcap.mcap_instance import MCAPInstance
import mcap.misc

_BlueZ = None

def BlueZ():
	if not _BlueZ:
		_BlueZ = mcap.misc.BlueZ()
	return _BlueZ


class HealthManager(object):
	def __init__(self):
		self.applications = []
		pass

	def RegisterApplication(self, agent, config): # -> HealthApplication
		application = HealthApplication(agent, config)
		if not application:
			return None
		self.applications.append(application)
		return application

	def UnregisterApplication(self, application):
		application.stop()
		self.applications.remove(application)

	def UpdateServices(self):
		# TODO searches remote devices
		pass


class HealthApplication(MCAPInstance):
	def __init__(self, agent, config):
		if not isinstance(agent, HealthApplicationAgent):
			raise HealthError("Bad agent superclass")
		self.agent = agent

		self.endpoints = {}
		self.sdp_record = {'features': []}
		self.sdp_handle = None

		err = self.process_config(config)
		if err:
			raise HealthError("Bad config: %s" % err)

		listen = len(self.endpoints > 0)
		adapter = ""
		MCAPInstance.__init__(self, adapter, listen)
		self.mdl_watch(False)

		self.services = [] # relationship 1:(0,1) with MCL
		self.channels = [] # relationship 1:1 with MDL
		self.stopped = False

		self.publish()

	def process_config(self, config):
		'''
		{
		  "end_points" : [{ (optional)
			"agent": path,  (mapped with HealthAgent)
			"role" : ("source" or "sink"), (mandatory)
			"specs" :[{ (mandatory)
				"data_type" : uint16, (mandatory)
				"description" : string, (optional)
			}]
		  }]
		}
		'''

		if 'end_points' not in config:
			return None

		auto_mdepid = 1
		is_auto_id = True

		for endpoint in self.config['end_points']:
			agent = end_point["agent"]
			role = end_point["role"].lower()

			if not isinstance(agent, HealtEndPointAgent):
				return "Endpoint agent not appropriate subclass"

			if role not in ("source", "sink"):
				return "Role must be 'source' or 'sink'"

			if 'mdepid' not in end_point:
				mdepid = auto_mdepid
				auto_mdepid += 1
			else:
				mdepid = end_point['mdepid']

			if 'config' not in end_point:
				config = 0x01 # reliable
			else:
				config = end_point['config']

			if config not in (0x01, 0x02):
				return "Config not 0x01 or 0x02"

			if mdepid in self.endpoints:
				return "MDEP ID %d mentioned twice!"

			sink = (role == "sink" and 1 or 0)

			data_types = []
			self.endpoint[mdepid] = {'agent': agent,
						'config': config}

			for spec in end_point["specs"]:
				data_type = spec["data_type"]
				description = ""

				if 'description' in spec:
					description = spec["description"][:254]

				if data_type < 0 or data_type > 65535:
					return "Bad data type"

				self.sdp_record['features'].append({
					'mdep_id': mdepid,
					'role': role,
					'data_type': data_type,
					'description': description})

		return None

	def publish(self):
		self.sdp_handle = None

		r = self.sdp_record
		r['mcap_control_psm'] = self.cpsm
                r['mcap_data_psm'] = self.dpsm
                r['name'] = 'HDPy',
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
		BlueZ().remove_record(self.sdp_handle)
		self.sdp_handle = None

	def stop(self):	
		self.stopped = True

		self.agent.Release()
		self.agent = None

		for mdepid, endpoint in self.endpoints.items():
			endpoint['agent'].Release()
			endpoint['agent'] = None

		while self.services:
			self.remove_service(self.services[-1])

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
		channel = HealthDataChannel(service, mdl, acceptor)
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
					mcl.remote_addr_dc)
		self.add_service(service)
		return service

	def create_service(self, control_addr, data_addr):
		service = HealthService(self, control_addr, data_addr)
		self.add_service(service)
		return service

	def add_service(self, service):
		if service not in services:
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

		ok = mdepid in self.endpoints

		if not ok:
			print "requested MDEP ID %d not in our list" % mdepid

		our_config = self.endpoints[mdepid].config
		reliable = (our_config == 0x01)

		if config and (config != our_config)
			print "MDEP reqs config %d, we offer %d, nak" \
				% (config, our_config)
			ok = False

		return ok, reliable, our_config

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

		channel = self.got_channel_by_mdl(mdl)
		reconn = channel is not None

		if not reconn:
			channel = self.create_channel(mdl, mdl.acceptor)

		if mdl.acceptor:
			agent = self.endpoint_agent(mdl.mdepid)
			agent.DataChannelCreated(channel, reconn)

		service.mdl_connected(mdl, channel, err)

	def MDLDeleted(self, mdl):
		if self.stopped:
			return

		channel = self.got_channel_by_mdl(mdl)
		if channel:
			service = self.service_by_mcl(mdl.mcl)
			self.remove_channel(channel)
			self.agent.DataChannelRemoved(service, channel)

	def MDLClosed(self, mdl):
		# Application discovers this via fd closure
		pass


class HealthService(object):
	# Current queue processing status
	IDLE = 0
	WAITING_MCL = 1
	WAITING_MDL = 2 # used by Echo() only
	IN_FLIGHT = 3

	CONNECTION = 1
	DISCONNECTION = 2
	DELETION = 3
	MDL_READY = 4
	MDL_CONNECTION = 5

	def __init__(self, instance, addr_control, addr_data):
		self.addr = addr
		self.addr_control = addr_control
		self.addr_data = addr_data
		self.instance = instance
		self.mcl = None
		self.queue = []
		self.queue_status = self.IDLE
		self.endpoints = None
		self.valid = True
		# FIXME use endpoints format from SDP 

	def mcl_connected(self, mcl, err, reconn):
		'''
		Called back by instance when related MCL is connected
		'''
		self.mcl = mcl
		self.process_queue(self.CONNECTION, err, None)

	def mcl_disconnected(self, mcl):
		'''
		Called back by instance when MCL is disconnected
		'''
		self.process_queue(self.DISCONNECTION, 0, None)

	def mcl_deleted(self, mcl):
		'''
		Called back by instance when MCL is invalidated
		'''
		self.mcl = None
		self.process_queue(self.DELETION, 0, None)

	def mdl_ready(self, mdl, err):
		'''
		Called back by instance when MDLReady triggers
		'''
		self.process_queue(self.MDL_READY, err, None)

	def mdl_connected(self, mdl, channel, err):
		'''
		Called back by instance when MDLConnected triggers
		'''
		self.process_queue(self.MDL_CONNECTION, err, channel)

	def stop(self):
		'''
		Called back by instance when it is being stopped
		'''
		self.queue = []
		self.queue_state = IDLE

	def kill(self):
		self.stop()
		if self.mcl:
			self.instance.DeleteMCL(self.mcl)
		self.valid = False
		self.mcl = None
		self.instance = None

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
		elif event == self.MCL_READY:
			pass
		elif event == self.MCL_CONNECTION:
			self.queue_mdl_conn_up(other)

		else:
			# disconnection/deletion
			self.queue_fail(-999)

	def queue_mcl_conn_up(self):
		'''
		Called when a connection is successful
		'''
		if self.queue_status == self.WAITING_MCL:
			self.queue_status = self.IDLE

		self.dispatch_queue()

	def queue_mdl_conn_up(self, channel):
		if self.queue[0] is self._OpenDataChannel:
			# we are expecting for this
			self.queue[0][2](self.new_channel)
			

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
			self.mcl = self.instance.CreateMCL(self.addr_control,
						self.addr_data[1])
		else:
			self.queue_execute()

	def queue_execute(self):
		self.queue_status = self.IN_FLIGHT
		command, args, reply_cb, error_cb = self.queue[0]
		command(args, reply_cb, error_cb)

	def Echo(self, data, reply_handler, error_handler):
		"""
		Sends an echo petition to the remote service. Returns True if
		response matches with the buffer sent. If some error is detected
		False value is returned and the associated MCL is closed.
		"""
		# FIXME
		# FIXME Echo acceptor side inside Instance
		# FIXME Add Echo feature to MCAP (read spec)
		self.queue.append(self._Echo, (data,),
				reply_handler, error_handler)
		self.dispatch_queue()

	def _Echo(self, args, reply_handler, error_handler):
		data = args[0]
		# FIXME wait for mdl?
		# FIXME where feedback comes from?
		pass

	def OpenDataChannel(args, reply_handler, error_handler):
		end_point, conf = args
		try:
			conf = conf.lower()
			conf = {"reliable": 1, "streaming": 2, "any": 0}[conf]
		except KeyError:
			raise HealthError("Invalid channel config")

		try:
			end_point = int(end_point.split("/")[-1])
		except ValueError:
			raise HealthError("Invalid endpoing identifier")
			
		self.queue.append(self._OpenDataChannel,
				(end_point, conf, reliable),
				reply_handler, error_handler)

		self.dispatch_queue()

	def _OpenDataChannel(self, args, reply_handler, error_handler):
		mdepid, conf, reliable = args
		mdlid = self.instance.CreateMDLID(self.mcl)
		self.instance.CreateMDL(self.mcl, mdlid, mdepid, conf, reliable)
		# FIXME where feedback comes from?
		# FIXME return HealthDataChannel in the end

	def DeleteAllDataChannels(self):
		"""
		Deletes all data channels so they will not be available for
		future use.
		"""
		self.queue.append(self._DeleteAllDataChannels, (), None, None)
		self.dispatch_queue()

	def _DeleteAllDataChannels(self, args, reply_handler, error_handler):
		self.instance.DeleteAll(self.mcl)

	def _DeleteMDL(self, mdl):
		self.queue.append(self.__DeleteMDL, (mdl,), None, None)
		self.dispatch_queue()

	def __DeleteMDL(self, args, reply_handler, error_handler):
		mdl = args[0]
		instance.DeleteMDL(mdl)

	def _ReconnectMDL(self, mdl, reply_handler, error_handler):
		self.queue.append(self.__ReconnectMDL, (mdl,), reply_handler,
								error_handler)
		self.dispatch_queue()

	def __ReconnectMDL(self, args, reply_handler, error_handler):
		mdl = args[0]
		self.instance.ReconnectMDL(self.mdl)
		# FIXME Reconnection feedback? and err?

	def GetProperties(self):
		# FIXME convert SDP record format to this
		pass
		"""
		EndPoints array of {
			"end_point": string,
			"role"  : "source" or "sink" ,
			"specs" : [{
				"dtype"       : uint16,
				"description" : string, (optional)
				}]
		}
		"""


class HealthDataChannel(object):
	def __init__(self, service, mdl, acceptor):
		self.service = service
		self.mdl = mdl
		self.acceptor = acceptor
		self.valid = True
		self.fd_acquired = None

	def GetProperties(self):
		if not self.valid:
			raise HealthError("Data channel deleted")
		qos = "Reliable"
		if not self.mdl.reliable:
			qos = "Streaming"
		conn = self.mdl.active()
		return {"QualityOfService": qos, "Connected": conn}

	def Acquire(self):
		if not self.valid:
			raise HealthError("Data channel deleted")
		if self.fd_acquired:
			raise HealthError("File descriptor already acquired")
		try:
			self.fd_acquired = os.dup2(mdl.sk)
		except IOError:
			raise HealthError("File descriptor could not be duped")
		return fd

	def Release(self):
		if not self.fd_acquired:
			return
		fd, self.fd_acquired = self.fd_acquired, None
		try:
			fd.close()
		except IOError:
			pass

	def Delete(self):
		if not self.valid:
			raise HealthError("Data channel deleted")
		self.valid = False
		self.service._DeleteMDL(self.mdl)

	def Reconnect(self, reply_handler, error_handler):
		if not self.valid:
			raise HealthError("Data channel deleted")
		# FIXME reconection locally not supported
		# FIXME reconnection remotely not supported
		self.service._ReconnectMDL(self.mdl, reply_handler,
							error_handler)

	def stop(self):
		self.Release()
		self.mdl.close()


class HealthApplicationAgent(object):
	def __init__(self):
		pass

	def Release(self):
		print "HealthApplicationAgent.Release not overridden"
		pass

	def ServiceDiscovered(service):
		print "HealthApplicationAgent.ServiceDiscovered not overridden"
		pass

	def ServiceRemoved(self, service):
		print "HealthApplicationAgent.ServiceRemoved not overridden"

	def DataChannelRemoved(service, data_channel):
		print "HealthApplicationAgent.DataChannelRemoved not overridden"
		pass


def HealthEndPointAgent(object):
	def __init__(self):
		pass

	def Release(self):
		print "HealthEndPointAgent.Release not overridden"
		pass

	def DataChannelCreated(self, data_channel, reconn):
		print "HealthEndPointAgent.DataChannelCreated not overridden"
		pass

# FIXME capture all "normal" InvalidOperation exceptions
