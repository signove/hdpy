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
		# FIXME searches remote devices
		pass

	def ServiceDiscovered(self, service):
		print "HealthManager.ServiceDiscovered not overridden"

	def ServiceRemoved(self, service):
		print "HealthManager.ServiceRemoved not overridden"


class HealthApplication(MCAPInstance):
	def __init__(self, agent, config):
		if not isinstance(agent, HealthApplicationAgent):
			raise HealthError("Bad agent superclass")
		self.agent = agent

		err = self.process_config(config)
		if err:
			raise HealthError("Bad config: %s" % err)

		listen = len(self.endpoints > 0)
		adapter = ""
		MCAPInstance.__init__(self, adapter, listen)
		self.mdl_watch(False)

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
		self.endpoints = []

		if 'end_points' not in config:
			return None

		auto_mdepid = 1
		is_auto_id = True

		for end_point in config["end_points"]:
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

			specs = []
			sink = role == "sink" and 1 or 0
			# FIXME use a format amenable for SDP record 
			self.endpoints.append((agent, sink, mdepid, specs))

			for spec in end_point["specs"]:
				data_type = spec["data_type"]
				description = ""

				if 'description' in spec:
					description = spec["description"][:254]

				if data_type < 0 or data_type > 65535:
					return "Bad data type"

				specs.append((data_type, description))

		return None

	def publish(self):
		self.sdp_handle = None
		pass
		# FIXME create and publish SDP record

	def unpublish(self):
		if not self.sdp_handle:
			return
		# FIXME remove SDP record
		self.sdp_handle = None

	def stop(self):	
		# FIXME release agents
		# FIXME call HealthService stop()
		# FIXME call DeleteMCL()
		self.unpublish()
		MCAPInstance.stop(self)

	def MCLConnected(self, mcl, err):
		# FIXME
		pass
	def MCLDisconnected(self, mcl):
		# FIXME
		pass
	def MCLReconnected(self, mcl, err):
		# FIXME
		pass
	def MCLUncached(self, mcl):
		# FIXME
		pass
	def MDLInquire(self, mdepid, config):
		# FIXME
		pass
	def MDLReady(self, mcl, mdl, err):
		# FIXME
		pass
	def MDLRequested(self, mcl, mdl, mdep_id, conf):
		# FIXME
		pass
	def MDLAborted(self, mcl, mdl):
		# FIXME
		pass
	def MDLConnected(self, mdl, err):
		# FIXME
		pass
	def MDLDeleted(self, mdl):
		# FIXME
		pass
	def MDLClosed(self, mdl):
		# FIXME
		pass
	def MDLReconnected(self, mdl):
		# FIXME
		pass


# TODO CSP API, implementation

"""
	def SyncTimestamp(self, mcl):

	def SyncBtClock(self, mcl):

	def SyncCapabilities(self, mcl, reqaccuracy):

	def SyncSet(self, mcl, update, btclock, timestamp):

	def SyncCapabilitiesResponse(self, mcl, err, btclockres, synclead,
				tmstampres, tmstampacc):

	def SyncSetResponse(self, mcl, err, btclock, tmstamp, tmstampacc):

	def SyncInfoIndication(self, mcl, btclock, tmstamp, accuracy):
"""


class HealthService(object):
	# Current queue processing status
	IDLE = 0
	WAITING_MCL = 1
	WAITING_MDL = 2
	IN_FLIGHT = 3

	CONNECTION = 1
	DISCONNECTION = 2
	DELETION = 3

	def __init__(self, instance, addr, cpsm, dpsm):
		self.addr = addr
		self.cpsm = cpsm
		self.dpsm = dpsm
		self.instance = instance
		self.mcl = None
		self.queue = []
		self.queue_status = self.IDLE
		self.endpoints = None
		# FIXME use endpoints format from SDP 

	def mcl_connected(self, mcl, err, reconn):
		'''
		Called back by instance when related MCL is connected
		'''
		self.mcl = mcl
		self.process_queue(self.CONNECTION, err)

	def mcl_disconnected(self, mcl):
		'''
		Called back by instance when MCL is disconnected
		'''
		self.process_queue(self.DISCONNECTION)

	def mcl_deleted(self, mcl):
		'''
		Called back by instance when MCL is invalidated
		'''
		self.mcl = None
		self.process_queue(self.DELETION)

	def stop(self):
		'''
		Called back by instance when it is being stopped
		'''
		self.queue = []
		self.queue_state = IDLE

	def process_queue(self, event, err=0):
		'''
		Handles queue in face of events
		'''
		if not self.queue or not event:
			return

		if event == self.CONNECTION:
			if not err:
				self.queue_proceed()
			else:
				self.queue_fail()
		else:
			# disconnection/deletion
			self.queue_fail()

	def queue_proceed(self):
		'''
		Called when a connection is successful
		'''
		if self.queue_status == self.WAITING_MCL:
			self.queue_status = self.IDLE

		self.dispatch_queue()

	def queue_fail(self):
		'''
		Called when MCL connection could not be done and therefore
		the queued command can not be completed
		'''
		# FIXME error feedback
		if self.queue_status != self.IDLE:
			del self.queue[0]
			self.queue_status = self.IDLE

		self.dispatch_queue()

	def dispatch_queue(self):
		if not self.queue:
			return

		if self.queue_status != self.IDLE:
			# waiting for something to happen
			return

		if not self.mcl or not self.mcl.active():
			self.queue_status = self.WAITING_MCL
			self.instance.CreateMCL(addr, dpsm)
			# how feedback comes here?
		else:
			self.queue_execute()

	def execute_queue(self):
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

	def _OpenDataChannel(args, reply_handler, error_handler):
		mdepid, conf, reliable = args
		mdlid = self.instance.CreateMDLID(self.mcl)
		self.instance.CreateMDL(self.mcl, mdlid, mdepid, conf, reliable)
		# FIXME where feedback comes from?
		# FIXME we need to ConnectMDL too

	def DeleteAllDataChannels(self):
		"""
		Deletes all data channels so they will not be available for
		future use.
		"""
		self.queue.append(self._DeleteAllDataChannels, (), None, None)
		self.dispatch_queue()

	def _DeleteAllDataChannels(self, dummy1, dummy2):
		self.instance.DeleteAll(self.mcl)
		# FIXME where feedback comes from?

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
	def __init__(self, instance, mdl):
		self.instance = instance
		self.mdl = mdl
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
		instance.DeleteMDL(self.mdl)
		pass

	def Reconnect(self, reply_handler, error_handler):
		if not self.valid:
			raise HealthError("Data channel deleted")
		self.instance.ReconnectMDL(self.mdl)


class HealthApplicationAgent(object):
	def __init__(self):
		pass

	def Release(self):
		print "HealthApplicationAgent.Release not overridden"
		pass

	def ServiceDiscovered(service):
		print "HealthApplicationAgent.ServiceDiscovered not overridden"
		pass

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
