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

# Run test3_server in the other side

from mcap_instance import MCAPInstance
import mcap
import time
import sys
import glib
import random

loop = glib.MainLoop()

class MI(MCAPInstance):
	def __init__(self, adapter, listener):
		MCAPInstance.__init__(self, adapter, listener)
		self.test_step = 0
		self.response = self.MCLConnected

	def bye(self):
		glib.MainLoop.quit(loop)

	def RecvDump(self, mcl, message):
		# print "Received raw msg", repr(message)
		return True

	def SendDump(self, mcl, message):
		# print "Sent", repr(message)
		return True

	def test(self, mcl, mdl, response, *args):
		if response is not None and response != self.response:
			print "Test %d expected %s came %s" % \
				(self.test_step, self.response.__name__,
					response.__name__)
			sys.exit(1)

		test_item = MI.tests[self.test_step]
		self.test_step += 1
		print "Round %d %s" % (self.test_step, test_item[0].__name__)
		test_item[0](self, mcl, mdl, *test_item[1:])

		return False

	def finish(self, *dummy):
		print "All tests ok"
		glib.timeout_add(500, self.bye)

	################################3############## Tests

	def test_disconnect(self, mcl, dummy):
		self.response = self.MCLDisconnected
		instance.CloseMCL(mcl)

	def test_reconnect(self, mcl, dummy):
		self.response = self.MCLReconnected
		new_mcl = instance.CreateMCL(remote_addr, dpsm)
		assert(mcl is new_mcl)

	def test_delete(self, mcl, dummy):
		self.response = self.MCLUncached
		instance.DeleteMCL(mcl)

	def test_connect(self, mcl, dummy):
		self.response = self.MCLConnected
		instance.CreateMCL(remote_addr, dpsm)

	def test_mdl_create(self, mcl, dummy):
		self.response = self.MDLReady
		mdlid = instance.CreateMDLID(mcl)
		print "\tmdl id is", mdlid
		instance.CreateMDL(mcl, mdlid, 0x01, 0x12)

	def test_mdl_create_pending(self, mcl, dummy):
		self.test_mdl_create(mcl, dummy)
		# and now tries to create again
		mdlid = instance.CreateMDLID(mcl)
		try:
			instance.CreateMDL(mcl, mdlid, 0x01, 0x12)
			print "CreateMDL in PENDING state should have failed"
			sys.exit(1)
		except mcap.InvalidOperation:
			pass

	def test_mdl_connect(self, dummy, mdl):
		self.response = self.MDLConnected
		instance.ConnectMDL(mdl)

	def test_mdl_connect_connected(self, dummy, mdl):
		self.response = self.test_mdl_connect_connected
		try:
			instance.ConnectMDL(mdl)
			print "CreateMDL in CONNECTED state should have failed"
		except mcap.InvalidOperation:
			pass
			glib.timeout_add(0, self.test, dummy, mdl,
					self.test_mdl_connect_connected)

	def test_mdl_reconnect(self, dummy, mdl):
		self.response = self.MDLReady
		instance.ReconnectMDL(mdl)

	def test_mdl_reconnect_pending(self, mcl, mdl):
		self.test_mdl_reconnect(mcl, mdl)
		# and now tries to create again
		try:
			instance.ReconnectMDL(mdl)
			print "ReconnectMDL in PENDING state should have failed"
			sys.exit(1)
		except mcap.InvalidOperation:
			pass
		try:
			instance.CreateMDL(mcl, 33, 0x02, 0x13)
			print "CreateMDL in PENDING state should have failed (2)"
			sys.exit(1)
		except mcap.InvalidOperation:
			pass

	def test_mdl_connect2(self, dummy, mdl):
		self.response = self.MDLConnected
		instance.ConnectMDL(mdl)

	def test_mdl_abort(self, mcl, mdl):
		self.response = self.MDLAborted
		instance.AbortMDL(mcl, mdl.mdlid)

	def test_mdl_send(self, dummy, mdl):
		self.response = self.Recv
		mdl._a = a = int(random.random() * 1000)
		mdl._b = b = int(random.random() * 1000)
		instance.Send(mdl, "%d + %d" % (a, b))

	def test_mdl_close(self, dummy, mdl):
		self.response = self.MDLClosed
		instance.CloseMDL(mdl)

	def test_mdl_delete(self, dummy, mdl):
		self.response = self.MDLDeleted
		instance.DeleteMDL(mdl)

	def test_mdl_delete_all(self, mcl, dummy):
		self.response = self.MDLDeleted
		instance.DeleteAll(mcl)

	################################### MCAP callbacks

	def MCLConnected(self, mcl):
		print "\tMCL has connected"
		self.test(mcl, None, self.MCLConnected)

	def MCLReconnected(self, mcl):
		print "\tMCL has reconnected"
		self.test(mcl, None, self.MCLReconnected)

	def MCLDisconnected(self, mcl):
		print "\tMCL has disconnected"
		self.test(mcl, None, self.MCLDisconnected)

	def MCLUncached(self, mcl):
		print "\tMCL has disconnected"
		self.test(mcl, None, self.MCLUncached)

	def MDLReady(self, mcl, mdl):
		print "\tinitiated MDL ready"
		self.test(mcl, mdl, self.MDLReady)

	def MDLConnected(self, mdl):
		print "\tMDL connected"
		self.test(mdl.mcl, mdl, self.MDLConnected)

	def MDLReconnected(self, mdl):
		print "\tMDL reconnected"
		print "ERROR: this callback is acceptor-only"
		sys.exit(1)

	def MDLAborted(self, mcl, mdl):
		print "\tMDL abort"
		self.test(mcl, mdl, self.MDLAborted)

	def MDLClosed(self, mdl):
		print "\tMDL closed"
		self.test(mdl.mcl, mdl, self.MDLClosed)

	def MDLDeleted(self, mdl):
		print "\tMDL deleted"
		self.test(mdl.mcl, mdl, self.MDLDeleted)

	def Recv(self, mdl, data):
		print "\tMDL received data"
		assert(data == ("%d" % (mdl._a + mdl._b + mdl.mdlid)))
		self.test(mdl.mcl, mdl, self.Recv)


MI.tests = ( \
	(MI.test_disconnect, ),
	(MI.test_reconnect, ),
	(MI.test_disconnect, ),
	(MI.test_delete, ),
	(MI.test_connect, ),
	(MI.test_mdl_create, ),
	(MI.test_mdl_connect, ),
	(MI.test_mdl_send, ),
	(MI.test_mdl_close, ),
	(MI.test_mdl_create, ),
	(MI.test_mdl_abort, ),
	(MI.test_mdl_reconnect, ),
	(MI.test_mdl_connect2, ),
	(MI.test_mdl_close, ),
	(MI.test_mdl_reconnect_pending, ),
	(MI.test_mdl_connect2, ),
	(MI.test_mdl_send, ),
	(MI.test_mdl_send, ),
	(MI.test_mdl_connect_connected, ),
	(MI.test_mdl_send, ),
	(MI.test_mdl_send, ),
	(MI.test_mdl_close, ),
	(MI.test_mdl_delete, ),
	(MI.test_mdl_delete_all, ),
	(MI.test_mdl_create_pending, ),
	(MI.test_mdl_abort, ),
	(MI.test_disconnect, ),
	(MI.finish, ),
	)

try:
	remote_addr = (sys.argv[1], int(sys.argv[2]))
	dpsm = int(sys.argv[3])
except:
	print "Usage: %s <remote addr> <cPSM> <dPSM>" % sys.argv[0]
	sys.exit(1)

instance = MI("00:00:00:00:00:00", False)
print "Connecting..."
mcl = instance.CreateMCL(remote_addr, dpsm)

loop.run()
