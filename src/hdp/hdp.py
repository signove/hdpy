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

# TODO remove this someday
sys.path.insert(0, "..")

from mcap.mcap_instance import MCAPInstance

# CreateInstance
# CloseInstance

class HDPInstance(MCAPInstance):
	def __init__(self, config):
		pass
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

		FIXME null config
		FIXME publish sdp record
		FIXME agent
		FIXME default observer
		"""

	def set_observer_agent(self, observer):
		if not isinstance(observer, HealthAgent):
			raise Exception("Observers need be HealthAgent's")
		self.observer = observer

	def CreateMCL(self, addr, dpsm):
		pass
	def DeleteMCL(self, mcl):
		pass
	def CloseMCL(self, mcl):
		pass
	def CreateMDLID(self, mcl):
		pass
	def CreateMDL(self, mcl, mdlid, mdepid, conf, reliable=True):
		pass
	def AbortMDL(self, mcl, mdlid):
		pass
	def ConnectMDL(self, mdl):
		pass
	def DeleteMDL(self, mdl):
		pass
	def DeleteAll(self, mcl):
		pass
	def CloseMDL(self, mdl):
		pass
	def ReconnectMDL(self, mdl):
		pass
	def TakeFd(self, mdl):
		pass
	def Send(self, mdl, data):
		pass
	def SyncTimestamp(self, mcl):
		pass
	def SyncBtClock(self, mcl):
		pass
	def SyncCapabilities(self, mcl, reqaccuracy):
		pass
	def SyncSet(self, mcl, update, btclock, timestamp):
		pass
	def Recv(self, mdl, data):
		pass
	def MCLConnected(self, mcl, err):
		pass
	def MCLDisconnected(self, mcl):
		pass
	def MCLReconnected(self, mcl, err):
		pass
	def MCLUncached(self, mcl):
		pass
	def MDLInquire(self, mdepid, config):
		pass
	def MDLReady(self, mcl, mdl, err):
		pass
	def MDLRequested(self, mcl, mdl, mdep_id, conf):
		pass
	def MDLAborted(self, mcl, mdl):
		pass
	def MDLConnected(self, mdl, err):
		pass
	def MDLDeleted(self, mdl):
		pass
	def MDLClosed(self, mdl):
		pass
	def MDLReconnected(self, mdl):
		pass
	def SyncCapabilitiesResponse(self, mcl, err, btclockres, synclead,
				tmstampres, tmstampacc):
		pass
	def SyncSetResponse(self, mcl, err, btclock, tmstamp, tmstampacc):
		pass
	def SyncInfoIndication(self, mcl, btclock, tmstamp, accuracy):
		pass


# FIXME get list of devices


class HealthDevice(object):
	def __init__(self, adapter, addr):
		self.adapter = adapter
		self.addr = addr

	def GetHealthInstances(self):
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

	def Connect(self, local_instance, remote_instance): # -> HealthLink
		pass
		"""
		Connects the local instance with the remote instance and returns
		the path of the HealthLink object. You should get the remote
		instance id running GetHealthInstances.

		Only the bus client that created the local session will be able
		to create connections using it.

		Possible errors: org.bluez.Error.InvalidArguments
				org.bluez.Error.HealthError

		FIXME demands 'null' (no-listening) instance, created on demand
		"""

	def Disconnect(self, link):
		pass
		"""
		Disconnect from the link the state will also be deleted. And
		no future reconnections will be possible. For keeping the state
		the method Pause of the health link should be used.

		Possible errors: org.bluez.Error.InvalidArguments
				org.bluez.Error.NotFound
				org.bluez.Error.HealthError
		"""


class HealthLink(object):
	def __init__(self, mcl):
		self.mcl = mcl

	def echo(self, string, cb, *args):
		pass
		"""
		Sends an echo petition to the remote intance. Returns True if
		response matches with the buffer sent. If some error is detected
		False value is returned and the associated MCL is closed.

		Uses MDEP ID 00, connects MDL and disconnects.
		"""

	def OpenDataChannel(self, mdepid, config, cb, *args):
		pass
		"""
		Creates a new data channel with the indicated config to the
		remote MCAP Data End Point (MDEP).
		The configuration should indicate the channel quality of
		service. In the current version of HDP, valid values are 0x01
		for reliable channels and 0x02 for streaming data channel.

		Returns the data channel id.

		Possible errors: org.bluez.Error.InvalidArguments
				org.bluez.Error.HealthError
		"""

	def ReconnectDataChannel(self, mdlid, cb, *args):
		pass
		"""
		Reconnects a previously created data channel indicated by its
		mdlid.

		Possible errors: org.bluez.Error.InvalidArguments
				org.bluez.Error.HealthError
				org.bluez.Error.NotFound
		"""

	def GetDataChannelFileDescriptor(self, mdlid):
		pass

	def DeleteDataChannel(self, mdlid, cb, *args):
		pass

	def DeleteAllDataChannels(self):
		pass

	def GetDataChannelStatus(self):
		pass
		"""
		Return a dictionary with all the data channels that
		can be used to send data right now. The dictionary
		is formed like follows:
		{
			"reliable": [mdlid_r1, mdlid_r2, ...],
			"streaming" : [mdlid_s1, mdlid_s2, ...]
		}

		The fist reliable data channel will always be the first
		data channel in reliable array.
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
