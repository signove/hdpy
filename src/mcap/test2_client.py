#!/usr/bin/env python

from mcap_instance import MCAPInstance
from mcap_defs import *
import time
import sys
import glib

loop = glib.MainLoop()

class MyInstance(MCAPInstance):
	def Watch(self, fd, activity_cb, error_cb):
		glib.io_add_watch(fd, glib.IO_IN, activity_cb)
		glib.io_add_watch(fd, glib.IO_ERR, error_cb)
		glib.io_add_watch(fd, glib.IO_HUP, error_cb)

	def MCLConnected(self, mcl):
		print "MCL has connected"
		self.take_initiative(mcl)

	def MCLDisconnected(self, mcl):
		print "MCL has disconnected"
		self.bye()

	def __init__(self, adapter, listener):
		MCAPInstance.__init__(self, adapter, listener)
 		self.counter = 0

	def bye(self):
		if self.counter >= len(sent):
			print 'TESTS OK' 
		else:
			print 'DID NOT COMPLETE ALL TESTS'
		glib.MainLoop.quit(loop)

	def take_initiative(self, mcl):
		if self.counter >= len(sent):
			self.bye()
		else:
			glib.idle_add(self.take_initiative_cb, mcl)

	def take_initiative_cb(self, mcl, *args):
		if self.counter >= len(sent):
			print 'TESTS OK' 
			self.bye()
		else:
			action = send_script[self.counter]
			action[0](self, mcl, *action[1:])

		# It is important to return False.
		return False

	def RecvDump(self, mcl, message):
		print "Received raw msg", repr(message)
		expected_msg = testmsg(received[self.counter])
		assert(message == expected_msg)
		self.check_asserts(mcl)
		self.counter += 1
		self.take_initiative(mcl)
		return True

	def SendDump(self, mcl, message):
		print "Sent", repr(message)
		expected_msg = testmsg(sent[self.counter])
		assert(message == expected_msg)
		return True

	def check_asserts(self, mcl):
		if (self.counter == 2):
			assert(mcl.count_mdls() == 1)
			assert(mcl.sm.state == MCAP_STATE_READY)
			assert(mcl.state == MCAP_MCL_STATE_ACTIVE)
		elif (self.counter == 3):
			assert(mcl.count_mdls() == 2)
			assert(mcl.sm.state == MCAP_STATE_READY)
			assert(mcl.state == MCAP_MCL_STATE_ACTIVE)		
		elif (self.counter == 4):
			assert(mcl.count_mdls() == 3)
			assert(mcl.sm.state == MCAP_STATE_READY)
			assert(mcl.state == MCAP_MCL_STATE_ACTIVE)
		elif (self.counter == 5):
			assert(mcl.count_mdls() == 3)
			assert(mcl.state == MCAP_MCL_STATE_ACTIVE)
			assert(mcl.sm.state == MCAP_STATE_READY)
		elif (self.counter == 6):			
			assert(mcl.count_mdls() == 2)
			assert(mcl.state == MCAP_MCL_STATE_ACTIVE)
			assert(mcl.sm.state == MCAP_STATE_READY)
		elif (self.counter == 7):
			assert(mcl.count_mdls() == 0)
			assert(mcl.state == MCAP_MCL_STATE_CONNECTED)
			assert(mcl.sm.state == MCAP_STATE_READY)
	
	
sent = [ 
	"0AFF000ABC", # send an invalid message (Op Code does not exist)
	"01FF000ABC", # send a CREATE_MD_REQ (0x01) with invalid MDLID == 0xFF00 (DO NOT ACCEPT)
       	"0100230ABC", # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0023 CONF = 0xBC (ACCEPT)
	"0100240ABC", # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0024 CONF = 0xBC (ACCEPT)
       	"0100270ABC", # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0027 CONF = 0xBC (ACCEPT)
       	"050027", # send an invalid ABORT_MD_REQ (0x05) MDLID == 0x0027 (DO NOT ACCEPT - not on PENDING state)
       	"070030", # send a valid DELETE_MD_REQ (0x07) MDLID == 0x0027
       	"07FFFF", # send a valid DELETE_MD_REQ (0x07) MDLID == MDL_ID_ALL (0XFFFF)
	]

send_script = [
	(MyInstance.SendRawRequest, 0x0a, 0xff, 0x00, 0x0a, 0xbc),
	(MyInstance.CreateMDL, 0xff00, 0x0a, 0xbc),
	(MyInstance.CreateMDL, 0x0023, 0x0a, 0xbc),
	(MyInstance.CreateMDL, 0x0024, 0x0a, 0xbc),
	(MyInstance.CreateMDL, 0x0027, 0x0a, 0xbc),
	(MyInstance.AbortMDL, 0x0027),
	(MyInstance.DeleteMDL, 0x0027),
	(MyInstance.DeleteAll),
	]

received = [
	"00010000", # receive a ERROR_RSP (0x00) with RSP Invalid OP (0x01)
	"0205FF00BC", # receive a CREATE_MD_RSP (0x02) with RSP Invalid MDL (0x05)
       	"02000023BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
	"02000024BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
       	"02000027BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
       	"06070027", # receive a ABORT_MD_RSP (0x06) with RSP Invalid Operation (0x07)
       	"08000030", # receive a DELETE_MD_RSP (0x08) with RSP Sucess (0x00)
       	"0800FFFF", # receive a DELETE_MD_RSP (0x08) with RSP Sucess (0x00)
	]


try:
	remote_addr = (sys.argv[1], int(sys.argv[2]))
except:
	print "Usage: %s <remote addr> <remote control PSM>" % sys.argv[0]
	sys.exit(1)

instance = MyInstance("00:00:00:00:00:00", False)
print "Connecting..."
mcl = instance.CreateMCL(remote_addr)

loop.run()
