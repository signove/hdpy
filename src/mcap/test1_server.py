#!/usr/bin/env python

from mcap_defs import *
from mcap import *
from test1 import *
import sys
import time
import glib
import threading

class MCAPSessionServerStub:

	received = [
		"0AFF000ABC", # send an invalid message (Op Code does not exist)
		"01FF000ABC", # send a CREATE_MD_REQ (0x01) with invalid MDLID == 0xFF00 (DO NOT ACCEPT)
        	"0100230ABC", # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0023 CONF = 0xBC (ACCEPT)
		"0100240ABC", # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0024 CONF = 0xBC (ACCEPT)
        	"0100270ABC",  # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0027 CONF = 0xBC (ACCEPT)
        	"050027", # send an invalid ABORT_MD_REQ (0x05) MDLID == 0x0027 (DO NOT ACCEPT - not on PENDING state)
        	"070030", # send a valid DELETE_MD_REQ (0x07) MDLID == 0x0027
        	"07FFFF", # send a valid DELETE_MD_REQ (0x07) MDLID == MDL_ID_ALL (0XFFFF)
		]

	sent = [
		"00010000", # receive a ERROR_RSP (0x00) with RSP Invalid OP (0x01)
		"0205FF00BC", # receive a CREATE_MD_RSP (0x02) with RSP Invalid MDL (0x05)
        	"02000023BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
		"02000024BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
        	"02000027BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
        	"06070027", # receive a ABORT_MD_RSP (0x06) with RSP Invalid Operation (0x07)
        	"08050030", # receive a DELETE_MD_RSP (0x08) with RSP Sucess (0x00)
        	"0800FFFF", # receive a DELETE_MD_RSP (0x08) with RSP Sucess (0x00)
		]

	def __init__(self, _mcl):
		self.bclock = threading.Lock()
		self.mcl = _mcl
		self.mcl_sm = MCLStateMachine(_mcl)

	def stop_session(self):
		self.mcl.close_cc()
		glib.MainLoop.quit(self.inLoop)

	def start_session(self):
		if self.mcl.is_cc_open():
			glib.io_add_watch(self.mcl.cc, glib.IO_IN, self.read_cb)
			glib.io_add_watch(self.mcl.cc, glib.IO_ERR, self.close_cb)
			glib.io_add_watch(self.mcl.cc, glib.IO_HUP, self.close_cb)

	def read_cb(self, socket, *args):
		try:
			message = self.mcl.read()
		except IOError:
			message = ""
		if message:
			self.mcl_sm.receive_message(message)
		else:
			self.stop_session()
		return True

	def close_cb(self, socket, *args):
		self.stop_session()
		return True

	def loop(self):
		self.inLoop = glib.MainLoop()
		self.inLoop.run()


if __name__=='__main__':

	mcl = MCL("00:00:00:00:00:00", MCAP_MCL_ROLE_ACCEPTOR)

	mcap_session = MCAPSessionServerStub(mcl)

	assert(mcl.state == MCAP_MCL_STATE_IDLE)

	# wait until a connection is done
	print "Waiting for connections on default dev"
	mcl.open_cc()

	print "Connected!"
	mcap_session.start_session()
	assert(mcl.state == MCAP_MCL_STATE_CONNECTED)

	print "Start main loop... "

	mcap_session.loop()
	
	print "Main loop finished."

	print 'TESTS OK' 
