# -*- coding: utf-8

################################################################
#
# Copyright (c) 2010 Signove. All rights reserved.
# See the COPYING file for licensing details.
#
# Autors: Elvis Pfützenreuter < epx at signove dot com >
#         Raul Herbster < raul dot herbster at signove dot com >
################################################################


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
		self.ccl = self.dcl = None
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
			schedule(self.mclconnected_mcl, mcl)

		return mcl

	def DeleteMCL(self, mcl):
		self.remove_mcl(mcl)
		schedule(self.MCLUncached, mcl)

	def CloseMCL(self, mcl):
		mcl.close()

	def CreateMDLID(self, mcl):
		''' returns a new mdlid unique for the MCL '''
		return mcl.create_mdlid()

	def CreateMDL(self, mcl, mdlid, mdepid, conf, reliable=True):
		''' followed by ConnectMDL/AbortMDL, which should be '''
		''' invoked when MDLReady callback is triggered '''
		req = CreateMDLRequest(mdlid, mdepid, conf, reliable)
		mcl.send_request(req)

	def AbortMDL(self, mcl, mdlid):
		req = AbortMDLRequest(mdlid)
		mcl.send_request(req)

	def ConnectMDL(self, mdl):
		mdl.connect()

	def DeleteMDL(self, mdl):
		mcl = mdl.mcl
		req = DeleteMDLRequest(mdl.mdlid)
		mcl.send_request(req)

	def DeleteAll(self, mcl):
		req = DeleteMDLRequest(MCAP_MDL_ID_ALL)
		mcl.send_request(req)

	def CloseMDL(self, mdl):
		mcl = mdl.mcl
		mdl.close()

	def ReconnectMDL(self, mdl):
		''' followed by ConnectMDL/AbortMDL, which should be '''
		''' invoked when MDLReady callback is triggered '''
		if not self.reconn_enabled:
			raise InvalidOperation("MDL reconnection feature off")
		mcl = mdl.mcl
		req = ReconnectMDLRequest(mdl.mdlid)
		mcl.send_request(req)

	def TakeFd(self, mdl):
		if not mdl.active():
			raise InvalidOperation("MDL is not active yet")
		if mdl._instance_watch:
			watch_cancel(mdl._instance_watch)
			mdl._instance_watch = None
		return mdl.sk

	def Send(self, mdl, data):
		return mdl.write(data)

	def SendRawRequest(self, mcl, *chars):
		req = RawRequest(*chars)
		mcl.send_request(req)

	def SyncTimestamp(self, mcl):
		if not self.csp_enabled:
			raise InvalidOperation("CSP not enabled for instance")
		return mcl.get_timestamp()

	def SyncBtClock(self, mcl):
		'''
		Returns (clock, accuracy), or None if failed
		'''
		if not self.csp_enabled:
			raise InvalidOperation("CSP not enabled for instance")
		return mcl.get_btclock()

	def SyncCapabilities(self, mcl, reqaccuracy):
		if not self.csp_enabled:
			raise InvalidOperation("CSP not enabled for instance")
		req = CSPCapabilitiesRequest(reqaccuracy)
		mcl.send_request(req)

	def SyncSet(self, mcl, update, btclock, timestamp):
		'''
		btclock None means immediate update
		timestamp None means do not update
		'''
		if not self.csp_enabled:
			raise InvalidOperation("CSP not enabled for instance")
		req = CSPSetRequest(update, btclock, timestamp)
		mcl.send_request(req)

### Callback methods that must/may be implemented by subclass

	def Recv(self, mdl, data):
		print "Recv (mdl data) not overridden"

	def MCLConnected(self, mcl, err):
		print "MCLConnected not overridden"

	def MCLDisconnected(self, mcl):
		print "MCLDisconnected not overridden"

	def MCLReconnected(self, mcl, err):
		print "MCLReconnected not overridden"

	def MCLUncached(self, mcl):
		print "MCLUncached not overridden"

	def MDLInquire(self, mdepid, config):
		'''
		Ask if this MDEP ID and config are ok, and if the channel
		is reliable or not
		'''
		print "MDLInquire not overridden"
		if not config:
			config = 0x01
		return True, True, config

	def MDLReady(self, mcl, mdl, err):
		''' Async confirmation of MDLCreate/MDLReconnect method '''
		raise Exception("Not overridden, but it should have been")

	def MDLRequested(self, mcl, mdl, mdep_id, conf):
		''' Followed by MDLAborted or MDLConnected '''
		print "MDLRequested not overridden"

	def MDLAborted(self, mcl, mdl):
		print "MDLAborted not overridden"

	def MDLConnected(self, mdl, err):
		print "MDLConnected not overridden"

	def MDLDeleted(self, mdl):
		print "MDLDeleted not overridden"

	def MDLClosed(self, mdl):
		print "MDLClosed not overridden"

	def MDLReconnected(self, mdl):
		print "MDLReconnected not overridden"

	def RecvDump(self, mcl, message):
		pass

	def SendDump(self, mcl, message):
		pass

	def SyncCapabilitiesResponse(self, mcl, err, btclockres, synclead,
				tmstampres, tmstampacc):
		print "SyncCapabilitiesResponse not overridden"

	def SyncSetResponse(self, mcl, err, btclock, tmstamp, tmstampacc):
		print "SyncSetResponse not overridden"

	def SyncInfoIndication(self, mcl, btclock, tmstamp, accuracy):
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
		self.MDLRequested(mcl, mdl, mdepid, config)

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
