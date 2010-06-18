from mcap_defs import *
from mcap import *

# The API of MCAPInstance mimics closely the mcap_test_plugin implemented
# for BlueZ / OpenHealth HDP and MCAP. D-BUS methods are normal methods,
# and D-BUS signals are callback methods implemented by a subclass of
# MCAPInstance.
#
# The major difference is that methods don't have async responses. If there
# is any async feedback, it comes via callbacks/signals. (In D-BUS API, only
# "passive", unprovoked events come via signals.)
#
# So, the application must take into account that it will receive callbacks
# about locally generated events, in order to avoid infinite loops.
#
# CreateMDL is an special case that can not work without an async response,
# so this API has a "MDLCreated" signal just to supply this need.


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

	def CreateMCL(self, addr):
		event = self.MCLConnected

		if self.peer_connected(addr):
			mcl = self.peer_mcl(addr)
			event = self.MCLReconnected
		else:
			mcl = MCL(self, self.adapter, MCAP_MCL_ROLE_INITIATOR,
				addr)
			self.add_mcl(mcl)

		if mcl.state == MCAP_MCL_STATE_IDLE:
			mcl.connect()
			event(mcl)

		return mcl
	
	def DeleteMCL(self, mcl):
		self.remove_mcl(mcl)
		self.MCLUncached(mcl)

	def CloseMCL(self, mcl):
		mcl.close()

	def CreateMDL(self, mcl, mdlid, mdepid, conf):
		''' followed by ConnectMDL/AbortMDL, which should be '''
		''' invoked when MDLCreated callback is triggered '''
		req = CreateMDLRequest(mdlid, mdepid, conf)
		mcl.sm.send_request(req)

	def AbortMDL(self, mcl, mdlid):
		req = AbortMDLRequest(mdlid)
		mcl.sm.send_request(req)

	def ConnectMDL(self, mdl):
		# FIXME connection feedback?
		pass

	# feedback via callback
	def DeleteMDL(self, mdl):
		mcl = mdl.mcl
		req = DeleteMDLRequest(mdl.mdlid)
		mcl.sm.send_request(req)

	# feedback via callback
	def DeleteAll(self, mcl):
		req = DeleteMDLRequest(MCAP_MDL_ID_ALL)
		mcl.sm.send_request(req)

	def CloseMDL(self, mdl):
		mcl = mdl.mcl
		mdl.close()
		pass # FIXME mdl deletion feebacok?

	# feedback via callback
	def ReconnectMDL(mdl):
		mcl = mdl.mcl
		pass # FIXME

	def Send(self, mdl, data):
		return mdl.send(data)

	def SendRawRequest(self, mcl, *chars):
		req = RawRequest(*chars)
		mcl.sm.send_request(req)

### Callback methods that must be implemented by subclass

	def Recv(self, mdl, data):
		raise Exception("Not implemented")

	def MCLConnected(self, mcl):
		raise Exception("Not implemented")

	def MCLDisconnected(self, mcl):
		raise Exception("Not implemented")

	def MCLReconnected(self, mcl):
		raise Exception("Not implemented")

	def MCLUncached(self, mcl):
		raise Exception("Not implemented")
	
	def MDLCreated(self, mdl):
		''' Async confirmation of MDLCreate method '''
		raise Exception("Not implemented")

	def MDLRequested(self, mcl, mdep_id, conf):
		''' Followed by MDLAborted or MDLConnected '''
		raise Exception("Not implemented")

	def MDLAborted(self, mcl, mdl):
		raise Exception("Not implemented")

	def MDLConnected(self, mcl, mdl):
		raise Exception("Not implemented")

	def MDLDeleted(self, mdl):
		raise Exception("Not implemented")

	def MDLClosed(self, mdl):
		raise Exception("Not implemented")

	def MDLReconnected(self, mdl):
		raise Exception("Not implemented")

	def Watch(self, fd, activity_cb, error_cb):
		raise Exception("Not implemented")

	def Timeout(self, to, cb, *args):
		raise Exception("Not implemented")

	def Idle(self, cb, *args):
		raise Exception("Not implemented")

### Callback methods that may be reimplemented if subclass is interested

	def RecvDump(self, mcl, message):
		pass

	def SendDump(self, mcl, message):
		pass
	
### Internal callbacks

	def watch_cc(self, listener, fd, activity_cb, error_cb):
		self.Watch(fd, activity_cb, error_cb)

	def new_cc(self, listener, sk, addr):
		event = self.MCLConnected

		if self.peer_connected(addr):
			mcl = self.peer_mcl(addr)
			event = self.MCLReconnected
		else:
			mcl = MCL(self, self.adapter, MCAP_MCL_ROLE_ACCEPTOR,
				addr)
			self.add_mcl(mcl)

		if mcl.state == MCAP_MCL_STATE_IDLE:
			mcl.accept(sk)
			event(mcl)
		else:
			# crossed or duplicated connection, reject
			sk.close()

	def error_cc(self, listener):
		raise Exception("Error in control PSM listener, bailing out")

	def watch_mcl(self, mcl, fd, activity_cb, error_cb):
		self.Watch(fd, activity_cb, error_cb)

	def closed_mcl(self, mcl):
		self.MCLDisconnected(mcl)

	def activity_mcl(self, mcl, is_recv, message):
		if is_recv:
			self.RecvDump(mcl, message)
		else:
			self.SendDump(mcl, message)

	def watch_dc(self, listener, fd, activity_cb, error_cb):
		self.Watch(fd, activity_cb, error_cb)

	def new_dc(self, listener, sk, addr):
		if not self.peer_connected(addr):
			# unknown peer
			sk.close()
		mcl = self.peer_mcl(addr)
		mcl.sm.incoming_mdl_socket(sk)

	def error_dc(self, listener):
		raise Exception("Error in data PSM listener, bailing out")

# FIXME call the callbacks
# FIXME mcl.create_mdl() method
# FIXME Crossed connections protection (MDL)
# FIXME MDL observer read / error separate
# FIXME notify close MDL sk
# FIXME test existing MDL ID
# FIXME CreateMCL() x connect() blockage x feedback
# FIXME remove direct refs to state machine
# FIXME Recv for MDLs - connect watcher
# FIXME Uncache timeout
