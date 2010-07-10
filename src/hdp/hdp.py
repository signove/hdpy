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

# FIXME remove this hack someday
sys.path.insert(0, "..")

from mcap.mcap_instance import MCAPInstance


class HealthManager(object):
	def __init__(self):
		self.applications = []
		pass

	def RegisterApplication(self, agent, config): # -> HealthApplication
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
		pass
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
		"""
		FIXME chk
		FIXME null config
		FIXME publish sdp record
		"""

	def CreateMCL(self, addr, dpsm):
		# FIXME
		pass
	def DeleteMCL(self, mcl):
		# FIXME
		pass
	def CloseMCL(self, mcl):
		# FIXME
		pass
	def CreateMDLID(self, mcl):
		# FIXME
		pass
	def CreateMDL(self, mcl, mdlid, mdepid, conf, reliable=True):
		# FIXME
		pass
	def AbortMDL(self, mcl, mdlid):
		# FIXME
		pass
	def ConnectMDL(self, mdl):
		# FIXME
		pass
	def DeleteMDL(self, mdl):
		# FIXME
		pass
	def DeleteAll(self, mcl):
		# FIXME
		pass
	def CloseMDL(self, mdl):
		# FIXME
		pass
	def ReconnectMDL(self, mdl):
		# FIXME
		pass
	def TakeFd(self, mdl):
		# FIXME
		pass
	def Send(self, mdl, data):
		# FIXME
		pass
	def SyncTimestamp(self, mcl):
		# FIXME
		pass
	def SyncBtClock(self, mcl):
		# FIXME
		pass
	def SyncCapabilities(self, mcl, reqaccuracy):
		# FIXME
		pass
	def SyncSet(self, mcl, update, btclock, timestamp):
		# FIXME
		pass
	def Recv(self, mdl, data):
		# FIXME
		pass
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
	def SyncCapabilitiesResponse(self, mcl, err, btclockres, synclead,
				tmstampres, tmstampacc):
		pass
	def SyncSetResponse(self, mcl, err, btclock, tmstamp, tmstampacc):
		# FIXME
		pass
	def SyncInfoIndication(self, mcl, btclock, tmstamp, accuracy):
		# FIXME
		pass


class HealthService(object):
	def __init__(self, addr):
		self.addr = addr

	def Echo(self, data, reply_handler, error_handler):
		pass
		"""
		Sends an echo petition to the remote service. Returns True if
		response matches with the buffer sent. If some error is detected
		False value is returned and the associated MCL is closed.
		"""

	def OpenDataChannel(end_point, conf, reply_handler, error_handler):
		"""
		Creates a new data channel with the indicated config to the
		remote MCAP Data End Point (MDEP).
		The configuration should indicate the channel quality of
		service using one of this values "Reliable", "Streaming", "Any".

		Returns an string that identifies the data channel.
		Possible errors: org.bluez.Error.InvalidArguments
				org.bluez.Error.HealthError
		"""
		pass

	def DeleteAllDataChannels(self):
		"""
		Deletes all data channels so they will not be available for
		future use.
		"""

	def GetProperties(self):
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
	def __init__(self):
		pass

	def GetProperties(self):
		"""
		{"QualityOfService": string}
		{"Connected": boolean}
		"""

	def Acquire(self):
		"""
		Returns the file descriptor for the data channel_ZZ
		"""
		pass

	def Release(self):
		pass

	def Delete(self):
		pass

	def Reconnect(self, reply_handler, error_handler):
		pass


class HealthApplicationAgent(object):
	def __init__(self):
		pass

	def Release(self):
		pass

	def ServiceDiscovered(service):
		print "HealthApplicationAgent.ServiceDiscovered not overridden"

	def DataChannelRemoved(service, data_channel):
		print "HealthApplicationAgent.DataChannelRemoved not overridden"


def HealthEndPointAgent(object):
	def __init__(self):
		pass

	def Release(self):
		pass

	def DataChannelCreated(self, data_channel, reconn):
		pass
