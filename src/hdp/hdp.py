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


class Adapter(object):
	def __init__(self, addr, devid):
		self.addr = addr
		self.devid = devid

	def CreateInstance(self, config):
		return HDPInstance(self.addr, config)

	def RegisterAgent(self, instance, agent):
		instance.set_observer(agent)

	def CloseInstance(self, instance):
		instance.stop()


DefaultAdapter = Adapter("00:00:00:00:00:00", -1)


def GetAdapterList():
	adapters = [DefaultAdapter]
	# FIXME get the rest


def RegisterAgent(instance, agent):
	instance.set_observer(agent)


def CloseInstance(instance):
	instance.stop()


class HDPInstance(MCAPInstance):

	def __init__(self, adapter, config):
		self.adapter = adapter
		self.listener = not not config
		self.__init__(self.adapter, self.listener)
		self.observer = HealthAgent()

		# FIXME link list, link list housekeeping

		if not config:
			return		

		# FIXME
		"""
                Dict is defined as bellow:
                { "data_spec" : The data_spec is the data exchange specification
                                (see section 5.2.10 of the specification
                                document) possible values:
                                        0x00 = reserved,
                                        0x01 [IEEE 11073-20601],
                                        0x02..0xff reserved,
                                (optional)
                  "end_points" : [{ (optional)
                        "mdepid" : uint8, (optional)
                        "role" : ("source" or "sink"), (mandatory)
                        "specs" :[{ (mandatory)
                                "data_type" : uint16, (mandatory)
                                "description" : string, (optional)
                        }]
                  }]
                }

		FIXME publish sdp record
		"""

	def set_observer(self, observer):
		if not isinstance(observer, HealthAgent):
			raise Exception("Observer needs to be HealthAgent")
		self.observer = observer

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
		# FIXME
				tmstampres, tmstampacc):
		pass
	def SyncSetResponse(self, mcl, err, btclock, tmstamp, tmstampacc):
		# FIXME
		pass
	def SyncInfoIndication(self, mcl, btclock, tmstamp, accuracy):
		# FIXME
		pass


def GetDeviceList():
	# FIXME
	pass


def CheckDevice(addr):
	# FIXME
	pass


def AddDeviceManually(addr, config):
	# FIXME
	pass


class HealthDevice(object):
	def __init__(self, addr):
		self.addr = addr

	def GetHealthInstances(self):
		# FIXME
		pass
		"""
		Gets the information of the remote instances present in this
		device and published on its SDP record. The returned data
		follows this format.

		[{"id": uint32,
		  "data_spec" : data spec,
		  "end_points":
			["mdepid": uint8,
			 "role"  : "source" or "sink" ,
			 "specs" : [{
				"dtype"       : uint16,
				"description" : string, (optional)
			 }]
			]
		}];
		"""

	def Connect(self, local_instance, remote_instance, cb, *args): # -> HealthLink
		# FIXME
		pass
		"""
		FIXME demands 'null' (no-listening) instance, created on demand
		"""

	def Disconnect(self, link):
		# FIXME
		pass


class HealthLink(object):
	def __init__(self, mcl):
		self.mcl = mcl

	def echo(self, string, cb, *args):
		# FIXME
		pass
		"""
		Sends an echo petition to the remote intance. Returns True if
		response matches with the buffer sent. If some error is detected
		False value is returned and the associated MCL is closed.

		Uses MDEP ID 00, connects MDL and disconnects.
		"""

	def OpenDataChannel(self, mdepid, config, cb, *args): # -> mdl id
		# FIXME
		pass
		"""
		Creates a new data channel with the indicated config to the
		remote MCAP Data End Point (MDEP).
		The configuration should indicate the channel quality of
		service. In the current version of HDP, valid values are 0x01
		for reliable channels and 0x02 for streaming data channel.
		"""

	def ReconnectDataChannel(self, mdlid, cb, *args):
		# FIXME
		pass

	def GetDataChannelFileDescriptor(self, mdlid):
		# FIXME
		pass

	def DeleteDataChannel(self, mdlid, cb, *args):
		# FIXME
		pass

	def DeleteAllDataChannels(self):
		# FIXME
		pass

	def GetDataChannelStatus(self):
		# FIXME
		pass
		"""
		{
			"reliable": [mdlid_r1, mdlid_r2, ...],
			"streaming" : [mdlid_s1, mdlid_s2, ...]
		}

		"""


class HealthAgent(object):
	'''
	Abstract class for health agents that observe a given instance.
	'''

	def __init__(self):
		pass

	def LinkConnected(self, link):
		print "HealthAgent.LinkConnected not overridden"

	def LinkPaused(self, link):
		# closed
		print "HealthAgent.LinkPaused not overridden"
	
	def LinkResumed(self, link):
		print "HealthAgent.LinkResumed not overridden"

	def LinkDisconnected(self, link):
		# deleted
		print "HealthAgent.LinkDisconnected not overridden"

	def CreatedDataChannel(self, link, mdlid, conf):
		# conf: (0x01 reliable, 0x02 streaming).
		print "HealthAgent.CreatedDataChannel not overridden"

	def DataChannelReconnected(self, link, mdlid, conf):
		print "HealthAgent.DataChannelReconnected not overridden"

	def DeletedDataChannel(self, link, mdlid):
		print "HealthAgent.DeletedDataChannel not overridden"

	def DeletedAllDataChannels(self, link):
		print "HealthAgent.DeletedAllDataChannels not overridden"
