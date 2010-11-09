# -*- coding: utf-8

#######################################################################
# Copyright 2010 Signove Corporation - All rights reserved.
# Contact: Signove Corporation (contact@signove.com)
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330,
# Boston, MA 02111-1307  USA
#
# If you have questions regarding the use of this file, please contact
# Signove at contact@signove.com.
#######################################################################

from mcap_defs import *
from mcap import *
from mcap_loop import *


class MCAPInstance:
	def __init__(self, adapter, listen):
		self.adapter = adapter
		self.listener = listen
		self.cpsm = 0
		self.dpsm = 0
		self.csp_enabled = True
		self.reconn_enabled = True
		self.ccl = None
		self.dcl = None
		self.mcls = []
		self.peers = {}
		self.watch_mdl = True
		self.start()

	def stop(self):
		while self.mcls:
			self.remove_mcl(self.mcls[0])

		if not self.listener:
			return

		if self.ccl:
			self.ccl.stop()
			self.ccl = None
		if self.dcl:
			self.dcl.stop()
			self.dcl = None

	def start(self):
		if not self.listener:
			return

		self.ccl = ControlChannelListener(self.adapter, self)
		self.cpsm = self.ccl.psm
		self.dcl = DataChannelListener(self.adapter, self)
		self.dpsm = self.dcl.psm

	def mdl_watch(self, enabled):
		self.watch_mdl = enabled

### Housekeeping

	def add_mcl(self, mcl):
		peer = mcl.remote_addr[0]
		if mcl in self.mcls:
			raise Exception("MCL already in instance list")
		if peer in self.peers:
			raise Exception("Peer already in instance peer list")
		if mcl.invalidated:
			raise Exception("MCL had been deleted")
		self.mcls.append(mcl)
		self.peers[peer] = mcl

	def remove_mcl(self, mcl):
		peer = mcl.remote_addr[0]
		mcl.close()
		mcl.invalidated = True
		for i, item in enumerate(self.mcls):
			if item is mcl:
				del self.mcls[i]
				break
		del self.peers[peer]

	def peer_connected(self, remote_addr):
		return remote_addr[0] in self.peers

	def peer_mcl(self, remote_addr):
		return self.peers[remote_addr[0]]

### CSP enabling

	def SyncEnable(self):
		self.csp_enabled = True
		return True;

	def SyncDisable(self):
		self.csp_enabled = False
		return True;

	def ReconnectionEnable(self):
		self.reconn_enabled = True

	def ReconnectionDisable(self):
		self.reconn_enabled = False

### Commands

	def CreateMCL(self, addr, dpsm):
		"""Creates a MCL object and initiate connection.
		@return: MCL object.
		"""
		if self.peer_connected(addr):
			mcl = self.peer_mcl(addr)
			mcl.virgin = False
		else:
			mcl = MCL(self, MCAP_MCL_ROLE_INITIATOR, addr, dpsm)
			self.add_mcl(mcl)
			mcl.virgin = True

		if mcl.state == MCAP_MCL_STATE_IDLE:
			mcl.connect()
		else:
			schedule(self.mclconnected_mcl, mcl, 0)

		return mcl

	def DeleteMCL(self, mcl):
		"""Make MCAP stack 'forget' the given MCL.
		@param mcl: MCL object to forget.
		@type mcl: MCl object.
		"""
		self.remove_mcl(mcl)
		schedule(self.MCLUncached, mcl)

	def CloseMCL(self, mcl):
		"""Closes the connection (but does not forget/delete) the MCL.
		@param mcl: MCL object to be closed.
		@type mcl: MCl object.
		"""
		mcl.close()

	def CreateMDLID(self, mcl):
		"""Generates an unique MDL ID for this MCL. This method does not involve
		any communication.
		@param mcl: MCL object to create mdl id for..
		@type mcl: MCl object.
		"""
		return mcl.create_mdlid()

	def CreateMDL(self, mcl, mdlid, mdepid, conf, reliable=True):
		"""followed by ConnectMDL/AbortMDL, which should be
		invoked when MDLReady callback is triggered. If a previous MDL with the
		same MDL ID exists, it will be overridden by this one.
		@param mcl: MCL object.
		@type mcl: MCl object.
		@param mdlid: Id of mdl.
		@type mdlid: Integer.
		@param mdepid: Id of mdep.
		@type mdepid: Integer.
		@param conf: Configuration.
		@type conf: Dictionary.
		@param reliable: Define if the request is reliable or not.
		@type reliable: Boolean.
		"""
		req = CreateMDLRequest(mdlid, mdepid, conf, reliable)
		mcl.send_request(req)

	def AbortMDL(self, mcl, mdlid):
		"""Initiator-side method to abort MDL creation/reconnection. Used
		in place of ConnectMDL() to take MCAP off PENDING state.
		@param mcl: MCL object.
		@type mcl: MCl object.
		@param mdlid: Id of mdl.
		@type mdlid: Integer.
		"""
		req = AbortMDLRequest(mdlid)
		mcl.send_request(req)

	def ConnectMDL(self, mdl):
		"""Initiator-side second phase of MDL creation. Connects the data
		channel.
		@param mdl: MDL object to connect.
		@type mdl: MDl object.
		"""
		mdl.connect()

	def DeleteMDL(self, mdl):
		"""Effectively removes the MDL from memory, so it cannot be reconnected.
		@param mdl: MDL object to delete.
		@type mdl: MDl object.
		"""
		mcl = mdl.mcl
		req = DeleteMDLRequest(mdl.mdlid)
		mcl.send_request(req)

	def DeleteAll(self, mcl):
		"""Remove all MDLs.
		@param mcl: MCL object used to send the request.
		@type mcl: MCl object.
		"""
		req = DeleteMDLRequest(MCAP_MDL_ID_ALL)
		mcl.send_request(req)

	def CloseMDL(self, mdl):
		"""Closes MDL data channel (but does not forget the MDL, so it can be
		reconnected later).
		@param mdl: MDL object to close.
		@type mdl: MDl object.
		"""
		mcl = mdl.mcl
		mdl.close()

	def ReconnectMDL(self, mdl):
		"""Followed by ConnectMDL/AbortMDL, which should be invoked when
		MDLReady callback is triggered. Initiator-side. First phase of 
		reconnecting a previously known MDL. Note that confirmation callback is
		MDLReady(), the same as CreateMDL(). Should an error happens, MDLReady()
		will notify about.
		@param mdl: MDL object to close.
		@type mdl: MDl object.
		"""
		if not self.reconn_enabled:
			raise InvalidOperation("MDL reconnection feature off")
		mcl = mdl.mcl
		req = ReconnectMDLRequest(mdl.mdlid)
		mcl.send_request(req)

	def TakeFd(self, mdl):
		"""Takes ownership of MDL socket. This means that Recv() callback
		will no longer be triggered, and application is responsible by
		watching the socket for reading and writing.
		@param mdl: MDL object.
		@type mdl: MDl object.
		"""
		if not mdl.active():
			raise InvalidOperation("MDL is not active yet")
		if mdl._instance_watch:
			watch_cancel(mdl._instance_watch)
			mdl._instance_watch = None
		return mdl.sk

	def Send(self, mdl, data):
		"""Sends data through MDL, if we don't want to manipulate the file
		descriptor directly.
		@param mdl: MDL object.
		@type mdl: MDl object.
		@param data: Data to be sent.
		"""
		return mdl.write(data)

	def SendRawRequest(self, mcl, *chars):
		"""Sends a raw request through MCL control channel. No checks are made
		on data. For debugging and testing purposes only.
		"""
		req = RawRequest(*chars)
		mcl.send_request(req)

	def SyncTimestamp(self, mcl):
		"""CSP Slave. Gets the current timestamp, for application usage.
		@param mcl: MCL object used to get timestamp.
		@type mcl: MCl object.
		"""
		if not self.csp_enabled:
			raise InvalidOperation("CSP not enabled for instance")
		return mcl.get_timestamp()

	def SyncBtClock(self, mcl):
		"""Returns (clock, accuracy), or None if failed. CSP Slave. Gets current
		Bluetooth Clock.
		@param mcl: MCL object used to get bluetooth clock.
		@type mcl: MCl object.
		"""
		if not self.csp_enabled:
			raise InvalidOperation("CSP not enabled for instance")
		return mcl.get_btclock()

	def SyncCapabilities(self, mcl, reqaccuracy):
		"""CSP Master. Requests CSP capabilities from slave.
		@param mcl: MCL object used to get bluetooth clock.
		@type mcl: MCl object.
		@param reqaccuracy: accuracy of request.
		"""
		if not self.csp_enabled:
			raise InvalidOperation("CSP not enabled for instance")
		req = CSPCapabilitiesRequest(reqaccuracy)
		mcl.send_request(req)

	def SyncSet(self, mcl, update, btclock, timestamp):
		"""CSP Master. Requests reset of slave timestamp. Passing btclock as none
		means immediate update. Passing timestamp as None means do not reset
		timestamp, only read it. Update as True means that info indication must
		be sent periodically by slave.
		"""
		if not self.csp_enabled:
			raise InvalidOperation("CSP not enabled for instance")
		req = CSPSetRequest(update, btclock, timestamp)
		mcl.send_request(req)

### Callback methods that must/may be implemented by subclass

	def Recv(self, mdl, data):
		"""Called back when data came via MDL.
		"""
		print "Recv (mdl data) not overridden"

	def MCLConnected(self, mcl, err):
		"""Called back when CreateMCL() was processed (with err != 0 in case of
		failure), as well as when a MCL connection was accepted.
		"""
		print "MCLConnected not overridden"

	def MCLDisconnected(self, mcl):
		"""MCL has disconnected, for any reason (including having called
		CloseMCL()).
		"""
		print "MCLDisconnected not overridden"

	def MCLReconnected(self, mcl, err):
		"""The same as MCLConnected, but MCL was already 'known'.
		"""
		print "MCLReconnected not overridden"

	def MCLUncached(self, mcl):
		"""MCAP stack has forgotten the given MCL. All references to it should
		be removed, otherwise the object can not be garbage-collected.
		"""
		print "MCLUncached not overridden"

	def MDLInquire(self, mdepid, config):
		"""Ask if this MDEP ID and config are ok, and if the channel
		is reliable or not.
		"""
		print "MDLInquire not overridden"
		if not config:
			config = 0x01
		return True, True, config

	def MDLReady(self, mcl, mdl, err):
		""" Async confirmation of MDLCreate/MDLReconnect method.
		"""
		raise Exception("Not overridden, but it should have been")

	def MDLRequested(self, mcl, mdl, mdep_id, conf):
		"""Followed by MDLAborted or MDLConnected. Remote side initiated MDL
		creation with the given characteristics. his event only handles MDLs
		that remote side has initiated.
		"""
		print "MDLRequested not overridden, must return reliability"
		return True

	def MDLAborted(self, mcl, mdl):
		"""Informs that MDL connection has been aborted, and we should not wait
		for MDLConnected().
		"""
		print "MDLAborted not overridden"

	def MDLConnected(self, mdl, err):
		"""Informs that MDL has a connected data channel. This event is received
		for both initiated and accepted MDLs.
		"""
		print "MDLConnected not overridden"

	def MDLDeleted(self, mdl):
		"""The MDL has been removed from remote side, either by our initiative
		or remote's.
		"""
		print "MDLDeleted not overridden"

	def MDLClosed(self, mdl):
		"""Notifies that the given MDL has been closed.
		@param mdl: MDL object closed.
		@type mdl: MDl object.
		"""
		print "MDLClosed not overridden"

	def MDLReconnected(self, mdl):
		"""Acceptor-only. Reconnection request was granted. It is not needed to
		do nothing, only wait for MDLConnected(), if we intend to accept the
		MDL.
		"""
		print "MDLReconnected not overridden"

	def RecvDump(self, mcl, message):
		"""MCL control channel incoming data event. For debugging and testing
		purposes only.
		"""
		pass

	def SendDump(self, mcl, message):
		"""MCL control channel outgoing data event. For debugging and testing
		purposes only.
		"""
		pass

	def SyncCapabilitiesResponse(self, mcl, err, btclockres, synclead,
				tmstampres, tmstampacc):
		"""CSP Master. Slave returned capabilities request. The "err" argument
		contains the MCAP error response. If it is zero, means success. If not
		zero, the numeric arguments are invalid.
		"""
		print "SyncCapabilitiesResponse not overridden"

	def SyncSetResponse(self, mcl, err, btclock, tmstamp, tmstampacc):
		"""CSP Master. Response to reset request.The "err" argument contains
		the MCAP error response. If it is not zero (success), the other values
		are unusable
		"""
		print "SyncSetResponse not overridden"

	def SyncInfoIndication(self, mcl, btclock, tmstamp, accuracy):
		"""CSP Master. Info indication received.
		"""
		print "SyncIndication not overridden"

### Internal callbacks

	def new_cc(self, listener, sk, addr):
		event = self.MCLConnected

		if self.peer_connected(addr):
			mcl = self.peer_mcl(addr)
			event = self.MCLReconnected
		else:
			mcl = MCL(self, MCAP_MCL_ROLE_ACCEPTOR, addr, 0)
			self.add_mcl(mcl)

		if mcl.state == MCAP_MCL_STATE_IDLE:
			mcl.accept(sk)
			event(mcl, 0)
		else:
			try:
				sk.shutdown(2)
			except IOError:
				pass
			sk.close()

	def error_cc(self, listener):
		raise Exception("Error in control PSM listener, bailing out")

	def closed_mcl(self, mcl):
		self.MCLDisconnected(mcl)

	def activity_mcl(self, mcl, is_recv, message):
		if is_recv:
			self.RecvDump(mcl, message)
		else:
			self.SendDump(mcl, message)

	def mdlconnected_mcl(self, mdl, reconn, err):
		if not err:
			if self.watch_mdl:
				mdl._instance_watch = \
					watch_fd(mdl.sk, self.mdl_activity, mdl)
			else:
				mdl._instance_watch = None
		self.MDLConnected(mdl, err)

	def mdl_activity(self, sk, event, mdl):
		if io_err(event):
			return False

		data = mdl.read()
		if not data:
			# redundant but harmless
			mdl.close()
			return False

		self.Recv(mdl, data)
		return True

	def mdlinquire_mcl(self, mdepid, config):
		return self.MDLInquire(mdepid, config)

	def mdlgranted_mcl(self, mcl, mdl, err):
		'''
		Only called as async response to active CreateMDL or
		ReconnectMDL
		'''
		self.MDLReady(mcl, mdl, err)

	def mdlrequested_mcl(self, mcl, mdl, mdepid, config):
		reliable = self.MDLRequested(mcl, mdl, mdepid, config)
		self.dcl.set_reliable(reliable)

	def mdlreconn_mcl(self, mcl, mdl):
		self.MDLReconnected(mdl)

	def mdlaborted_mcl(self, mcl, mdl):
		self.MDLAborted(mcl, mdl)

	def mdldeleted_mcl(self, mdl):
		self.MDLDeleted(mdl)

	def mdlclosed_mcl(self, mdl):
		mdl._instance_watch = None
		self.MDLClosed(mdl)

	def new_dc(self, listener, sk, addr):
		# TODO this is not a perfect sieve in case two MCLs request data
		# channels of different modes at the same time. The right thing to
		# to is delay response on all MCLs until the first has completed
		# the MDL connection. Also, we need to test whether the expected
		# mode (ERTM or Streaming) was actually honored!
		if not self.peer_connected(addr):
			# unknown peer
			try:
				sk.shutdown(2)
			except IOError:
				pass
			sk.close()
			return
		mcl = self.peer_mcl(addr)
		mcl.incoming_mdl_socket(sk)

	def error_dc(self, listener):
		raise Exception("Error in data PSM listener, bailing out")

	def mclconnected_mcl(self, mcl, err):
		if mcl.virgin:
			event = self.MCLConnected
		else:
			event = self.MCLReconnected
		event(mcl, err)

	def csp_capabilities(self, mcl, err, btclockres, synclead,
				tmstampres, tmstampacc):
		self.SyncCapabilitiesResponse(mcl, err, btclockres, synclead,
						tmstampres, tmstampacc)

	def csp_set(self, mcl, err, btclock, timestamp, tmacc):
		self.SyncSetResponse(mcl, err, btclock, timestamp, tmacc)

	def csp_indication(self, mcl, btclock, timestamp, accuracy):
		self.SyncInfoIndication(mcl, btclock, timestamp, accuracy)

# TODO Uncache timeout for idle MCLs
