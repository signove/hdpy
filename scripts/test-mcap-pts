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

#
# This script is supposed to be used for PTS testing. However, you can use it
# whenever you need to interact with other MCAP actor.
#

from mcap.mcap_defs import *
from mcap.mcap import *
from threading import RLock
import sys
import time
import glib

class MCAPSessionServerStub:

	def __init__(self):
		self.csp_enabled = True
		self.mutex = RLock()
		glib.io_add_watch(sys.stdin, glib.IO_IN, self.send_data)

	def new_cc(self, listener, sk, remote_addr):
		self.mcl = MCL(self, MCAP_MCL_ROLE_ACCEPTOR, remote_addr, 0)
		assert(self.mcl.state == MCAP_MCL_STATE_IDLE)
		self.mcl.accept(sk)
		assert(self.mcl.state == MCAP_MCL_STATE_CONNECTED)
		
		print "Connected!"

	def send_data(self, sk, evt):
		self.mutex.acquire()
		if (self.mcl == None):
			self.mutex.release()
			return False
		
		key_pressed = raw_input("")
		data = raw_input("#: ")
		message = testmsg(data)
		self.mcl.write(message)
		self.mutex.release()
		return True

	def error_cc(self, listener):
		print "MCL error"

	def closed_mcl(self, socket, *args):
		print "MCL created"

	def activity_mcl(self, mcl, recv, message, *args):
		if recv:
			print "Received", repr(message)
		else:
			print "Sent", repr(message)
		return True

	def mdlrequested_mcl(self, mcl, mdl, mdepid, config):
		self.mcl = mcl
		print "MDL requested"

	def mdlinquire_mcl(self, mdepid, config):
		if not config:
			config = 0x01
		return True, True, config

	def new_dc(self, listener, sk, addr):
		self.mcl.incoming_mdl_socket(sk)
		print "MDL created"

	def mdlconnected_mcl(self, mdl, reconn, err):
		glib.io_add_watch(mdl.sk, glib.IO_IN, self.recvdata, mdl)
		print "MDL connected"

	def mdlaborted_mcl(self, mcl, mdl):
		print "MDL", id(mdl), "aborted"

	def mdldeleted_mcl(self, mdl):
		print "MDL", id(mdl), "deleted"

	def mdlclosed_mcl(self, mdl):
		print "MDL", id(mdl), "closed"

	def recvdata(self, sk, evt, mdl):
		self.mutex.acquire()
		data = mdl.read()
		if not data:
			mdl.close()
			self.mutex.release()
			return False

		print "MDL", id(mdl), "data", data
		self.mutex.release()
		return True

	def loop(self):
		self.inLoop = glib.MainLoop()
		self.inLoop.run()


if __name__=='__main__':
	session = MCAPSessionServerStub()
	mcl_listener = ControlChannelListener("00:00:00:00:00:00", session)
	mdl_listener = DataChannelListener("00:00:00:00:00:00", session)

	print "Waiting for connections on default dev"
	session.loop()
