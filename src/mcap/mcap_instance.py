from mcap_defs import *
from mcap import *
from mcap_loop import *

# The API of MCAPInstance mimics closely the mcap_test_plugin implemented
# for BlueZ / OpenHealth HDP and MCAP. D-BUS methods are normal methods,
# and D-BUS signals are callback methods implemented by a subclass of
# MCAPInstance.
#
# Differences from D-BUS API:
# 
# The major difference is that methods don't have async responses. If there
# is any async feedback, it comes via callbacks/signals. (In D-BUS API, only
# "passive", unprovoked events come via signals.)
#
# So, the application must take into account that it will receive callbacks
# about locally generated events, in order to avoid infinite loops.
#
# CreateMDL is an special case that can not work without an async response,
# so this API has a "MDLReady" signal just to supply this need.
# The same for ReconnectMDL.
#
# MDLRequested yields (mcl, mdl, mdep_id, config) because MDL object is already
# known, while D-BUS does not reurn MDL handle at this signal.


class MCAPInstance:
	def __init__(self, adapter, listen):
		self.adapter = adapter
		self.listener = listen
		self.cpsm = 0
		self.dpsm = 0
		self.ccl = self.dcl = None
		self.mcls = []
		self.peers = {}
		if listen:
			self.do_listen()

	def do_listen(self):
		self.ccl = ControlChannelListener(self.adapter, self)
		self.cpsm = self.ccl.psm
		self.dcl = DataChannelListener(self.adapter, self)
		self.dpsm = self.ccl.psm

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
		mcl.close()
		mcl.invalidated = True
		for i, item in enumerate(self.mcls):
			if item is mcl:
				del self.mcls[i]
				break
		del self.peers[mcl.peer]

	def peer_connected(self, remote_addr):
		return remote_addr[0] in self.peers

	def peer_mcl(self, remote_addr):
		return self.peers[remote_addr[0]]

### Commands

	def CreateMCL(self, addr, dpsm):
		if self.peer_connected(addr):
			mcl = self.peer_mcl(addr)
			mcl.virgin = False
		else:
			mcl = MCL(self, self.adapter, MCAP_MCL_ROLE_INITIATOR,
				addr, dpsm)
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

	def CreateMDL(self, mcl, mdlid, mdepid, conf):
		''' followed by ConnectMDL/AbortMDL, which should be '''
		''' invoked when MDLReady callback is triggered '''
		req = CreateMDLRequest(mdlid, mdepid, conf)
		mcl.send_request(req)

	def AbortMDL(self, mcl, mdlid):
		req = AbortMDLRequest(mdlid)
		mcl.send_request(req)

	def ConnectMDL(self, mdl):
		if mdl.state == MCAP_MDL_STATE_CLOSED:
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

	def ReconnectMDL(mdl):
		''' followed by ConnectMDL/AbortMDL, which should be '''
		''' invoked when MDLReady callback is triggered '''
		mcl = mdl.mcl
		req = ReconnectMDLRequest(mdl.mdlid)
		mcl.send_request(req)

	def Send(self, mdl, data):
		return mdl.write(data)

	def SendRawRequest(self, mcl, *chars):
		req = RawRequest(*chars)
		mcl.send_request(req)

	def SyncTimestamp(self, mcl):
		return mcl.get_timestamp()

	def SyncBtClock(self, mcl):
		'''
		Returns (clock, accuracy), or None if failed
		'''
		return mcl.get_btclock()

	def SyncCapabilities(self, mcl, reqaccuracy):
		req = CSPCapabilitiesRequest(reqaccuracy)
		mcl.send_request(req)

	def SyncSet(self, update, btclock, timestamp):
		'''
		btclock None means immediate update
		timestamp None means do not update
		'''
		req = CSPSetRequest(update, btclock, timestamp)
		mcl.send_request(req)

### Callback methods that must/may be implemented by subclass

	def Recv(self, mdl, data):
		print "Recv (mdl data) not overridden"

	def MCLConnected(self, mcl):
		print "MCLConnected not overridden"

	def MCLDisconnected(self, mcl):
		print "MCLDisconnected not overridden"

	def MCLReconnected(self, mcl):
		print "MCLReconnected not overridden"

	def MCLUncached(self, mcl):
		print "MCLUncached not overridden"
	
	def MDLReady(self, mcl, mdl):
		''' Async confirmation of MDLCreate/MDLReconnect method '''
		raise Exception("Not overridden, but it should have been")

	def MDLRequested(self, mcl, mdl, mdep_id, conf):
		''' Followed by MDLAborted or MDLConnected '''
		print "MDLRequested not overridden"

	def MDLAborted(self, mcl, mdl):
		print "MDLAborted not overridden"

	def MDLConnected(self, mcl, mdl):
		print "MDLConnected not overridden"

	def MDLDeleted(self, mdl):
		print "MDLDeleted not overridden"

	def MDLClosed(self, mdl):
		print "MDLReconnected not overridden"

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
			mcl = MCL(self, self.adapter, MCAP_MCL_ROLE_ACCEPTOR,
				addr, 0)
			self.add_mcl(mcl)

		if mcl.state == MCAP_MCL_STATE_IDLE:
			mcl.accept(sk)
			event(mcl)
		else:
			# crossed or duplicated connection, reject
			# TODO refuse using BT_DEFER_SETUP		
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

	def mdlconnected_mcl(self, mdl, reconn):
		watch_fd(mdl.sk, self.mdl_activity, mdl)
		if reconn:
			self.MDLReconnected(mdl)
		else:
			self.MDLConnected(mdl)

	def mdl_activity(self, sk, event, mdl):
		if io_err(event):
			return False

		data = mdl.read()
		if not data:
			mdl.close()
			return False

		self.Recv(mdl, data)
		return True

	def mdlgranted_mcl(self, mcl, mdl):
		'''
		Only called as async response to active CreateMDL or
		ReconnectMDL
		'''
		self.MDLReady(mcl, mdl)

	def mdlrequested_mcl(self, mcl, mdl, mdepid, config):
		self.MDLRequested(mcl, mdl, mdepid, config)

	def mdlreconn_mcl(self, mcl, mdl):
		self.MDLReconnected(mcl, mdl)

	def mdlaborted_mcl(self, mcl, mdl):
		self.MDLAborted(mcl, mdl)

	def mdldeleted_mcl(self, mdl):
		self.MDLDeleted(mdl)

	def mdlclosed_mcl(self, mdl):
		self.MDLClosed(mdl)

	def new_dc(self, listener, sk, addr):
		if not self.peer_connected(addr):
			# unknown peer
			sk.close()
			return
		mcl = self.peer_mcl(addr)
		mcl.incoming_mdl_socket(sk)

	def error_dc(self, listener):
		raise Exception("Error in data PSM listener, bailing out")

	def mclconnected_mcl(self, mcl):
		if mcl.virgin:
			event = self.MCLConnected
		else:
			event = self.MCLReconnected
		event(mcl)

	def csp_capabilities(self, mcl, err, btclockres, synclead,
				tmstampres, tmstampacc):
		self.SyncCapabilitiesResponse(err, mcl, btclockres, synclead,
						tmstampres, tmstampacc)

	def csp_set(self, mcl, err, btclock, timestamp, tmacc):
		self.SyncSetResponse(err, mcl, btclock, timestamp, tmacc)

	def csp_indication(self, mcl, btclock, timestamp, accuracy):
		self.SyncInfoIndication(mcl, btclock, timestamp, accuracy)

# TODO Uncache timeout for idle MCLs
