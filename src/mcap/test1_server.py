#!/usr/bin/env python

from mcap_defs import *
from mcap import *
import sys
import time
import glib

class MCAPSessionServerStub:

	received = [
		"0BFF000ABC", # send an invalid message (Op Code does not exist)
		"01FF000ABC", # send a CREATE_MD_REQ (0x01) with invalid MDLID == 0xFF00 (DO NOT ACCEPT)
        	"0100230ABC", # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0023 CONF = 0xBC (ACCEPT)
		"0100240ABC", # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0024 CONF = 0xBC (ACCEPT)
        	"0100270ABC",  # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0027 CONF = 0xBC (ACCEPT)
        	"050027", # send valid ABORT_MD_REQ (0x05) MDLID == 0x0027 (DO NOT ACCEPT - not on PENDING state)
        	"070030", # send an invalid DELETE_MD_REQ (0x07) MDLID == 0x0030
        	"07FFFF", # send a valid DELETE_MD_REQ (0x07) MDLID == MDL_ID_ALL (0XFFFF)
		]

	sent = [
		"00010000", # receive a ERROR_RSP (0x00) with RSP Invalid OP (0x01)
		"0205FF00", # receive a CREATE_MD_RSP (0x02) with RSP Invalid MDL (0x05)
        	"02000023BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
		"02000024BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
        	"02000027BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
        	"06000027", # receive a ABORT_MD_RSP (0x06) with RSP Success
        	"08050030", # receive an invalid DELETE_MD_RSP (0x08) 
        	"0800FFFF", # receive a DELETE_MD_RSP (0x08) with RSP Sucess (0x00)
		]

	def __init__(self):
		pass

	def watch_cc(self, listener, fd, activity_cb, error_cb):
		glib.io_add_watch(fd, glib.IO_IN, activity_cb)
		glib.io_add_watch(fd, glib.IO_ERR, error_cb)
		glib.io_add_watch(fd, glib.IO_HUP, error_cb)

	def new_cc(self, listener, sk, remote_addr):
		self.mcl = MCL(self, "00:00:00:00:00:00", MCAP_MCL_ROLE_ACCEPTOR, remote_addr, 0)
		assert(self.mcl.state == MCAP_MCL_STATE_IDLE)
		self.mcl.accept(sk)
		assert(self.mcl.state == MCAP_MCL_STATE_CONNECTED)

		print "Connected!"

	def error_cc(eslf, listener):
		self.stop_session()

	def watch_mcl(self, mcl, fd, activity_cb, error_cb):
		glib.io_add_watch(fd, glib.IO_IN, activity_cb)
		glib.io_add_watch(fd, glib.IO_ERR, error_cb)
		glib.io_add_watch(fd, glib.IO_HUP, error_cb)

	def closed_mcl(self, socket, *args):
		self.stop_session()

	def stop_session(self):
		glib.MainLoop.quit(self.inLoop)

	def activity_mcl(self, mcl, recv, message, *args):
		if recv:
			print "Received", repr(message)
		else:
			print "Sent", repr(message)
		return True

	def loop(self):
		self.inLoop = glib.MainLoop()
		self.inLoop.run()


if __name__=='__main__':
	session = MCAPSessionServerStub()
	mcl_listener = ControlChannelListener("00:00:00:00:00:00", session)

	print "Waiting for connections on default dev"
	session.loop()

	print "Main loop finished."
	print 'TESTS OK' 
