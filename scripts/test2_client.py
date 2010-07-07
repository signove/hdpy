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


from mcap.mcap_instance import MCAPInstance
from mcap.mcap_defs import *
import time
import sys
import glib

loop = glib.MainLoop()

class MyInstance(MCAPInstance):
	def MCLConnected(self, mcl, err):
		if err:
			print "MCL Connection error", err
			self.bye()
			return

		print "MCL has connected"
		self.take_initiative(mcl)

	def MCLDisconnected(self, mcl):
		print "MCL has disconnected"
		self.bye()

	def __init__(self, adapter, listener):
		MCAPInstance.__init__(self, adapter, listener)
 		self.counter = 0
		self.ping_counter = 50

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
			to = 1000
			print "############ counter", self.counter
			if self.counter == 4:
				to = 2000
			glib.timeout_add(to, self.take_initiative_cb, mcl)

	def take_initiative_cb(self, mcl, *args):
		action = send_script[self.counter]
		method = action[0]
		if method in [MyInstance.DeleteMDL, MyInstance.ConnectMDL,
				MyInstance.ReconnectMDL]:
			method(self, mdl)
		else:
			method(self, mcl, *action[1:])

		# It is important to return False.
		return False

	def RecvDump(self, mcl, message):
		print "Received raw msg", repr(message)
		expected_msg = testmsg(received[self.counter])
		if message != expected_msg:
			print
			print "Received control msg different from expected!"
			print "Expected", repr(expected_msg)
			print "Received", repr(message)
			print
			return
		self.check_asserts(mcl)
		self.counter += 1
		if message[0:2] != "\x02\x00":
			self.take_initiative(mcl)
		else:
			# delay until we open MDL
			pass
		return True

	def SendDump(self, mcl, message):
		print "Sent", repr(message)
		expected_msg = testmsg(sent[self.counter])
		if message != expected_msg:
			print
			print "Sent control msg different from expected!"
			print "Expected", repr(expected_msg)
			print "Received", repr(message)
			print
			return
		return True

	def check_asserts(self, mcl):
		if (self.counter == 2):
			assert(mcl.count_mdls() == 1)
			assert(mcl.sm.request_in_flight == 0)
			assert(mcl.state == MCAP_MCL_STATE_PENDING)
		elif (self.counter == 3):
			assert(mcl.count_mdls() == 2)
			assert(mcl.sm.request_in_flight == 0)
			assert(mcl.state == MCAP_MCL_STATE_PENDING)
		elif (self.counter == 4):
			assert(mcl.count_mdls() == 3)
			assert(mcl.sm.request_in_flight == 0)
			assert(mcl.state == MCAP_MCL_STATE_PENDING)
		elif (self.counter == 5):
			assert(mcl.count_mdls() == 3)
			assert(mcl.state == MCAP_MCL_STATE_ACTIVE)
			assert(mcl.sm.request_in_flight == 0)
		elif (self.counter == 6):
			assert(mcl.count_mdls() == 0)
			assert(mcl.state == MCAP_MCL_STATE_CONNECTED)
			assert(mcl.sm.request_in_flight == 0)
	
	def MDLReady(self, mcl, mdl, err):
		if err:
			print "MDL creation/reconnection failed!"
		elif mdl.mdlid == 0x27:
			print "MDL ready but not connecting"
			self.take_initiative(mdl.mcl)
		else:
			print "MDL ready, connecting"
			glib.timeout_add(0, self.MDLReady_post, mdl)

	def MDLReady_post(self, mdl):
		instance.ConnectMDL(mdl)
		return False

	def MDLConnected(self, mdl, err):
		if err:
			print "MDL connection error!"
			return

		print "MDL connected"
		glib.timeout_add(1500, self.ping, mdl)
		self.take_initiative(mdl.mcl)

	def MDLClosed(self, mdl):
		print "MDL closed"

	def ping(self, mdl):
		self.ping_counter -= 1
		if self.ping_counter < 0:
			instance.CloseMDL(mdl)
			return False

		if not mdl.active():
			return False
		mdl.write("hdpy ping ")
		return True

	def Recv(self, mdl, data):
		print "MDL", id(mdl), "data", data
		return True
		
	
sent = [ 
	"0BFF000ABC", # send an invalid message (Op Code does not exist)
	"01FF000ABC", # send a CREATE_MD_REQ (0x01) with invalid MDLID == 0xFF00 (DO NOT ACCEPT)
       	"0100230ABC", # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0023 CONF = 0xBC (ACCEPT)
	"0100240ABC", # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0024 CONF = 0xBC (ACCEPT)
       	"0100270ABC",  # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0027 CONF = 0xBC (ACCEPT)
       	"050027", # send valid ABORT_MD_REQ (0x05) MDLID == 0x0027 (DO NOT ACCEPT - not on PENDING state)
       	"07FFFF", # send a valid DELETE_MD_REQ (0x07) MDLID == MDL_ID_ALL (0XFFFF)
	]

send_script = [
	(MyInstance.SendRawRequest, 0x0b, 0xff, 0x00, 0x0a, 0xbc),
	(MyInstance.CreateMDL, 0xff00, 0x0a, 0xbc),
	(MyInstance.CreateMDL, 0x0023, 0x0a, 0xbc),
	(MyInstance.CreateMDL, 0x0024, 0x0a, 0xbc),
	(MyInstance.CreateMDL, 0x0027, 0x0a, 0xbc),
	(MyInstance.AbortMDL, 0x0027),
	(MyInstance.DeleteAll, ),
	]

received = [
	"00010000", # receive a ERROR_RSP (0x00) with RSP Invalid OP (0x01)
	"0205FF00", # receive a CREATE_MD_RSP (0x02) with RSP Invalid MDL (0x05)
       	"02000023BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
	"02000024BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
       	"02000027BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
       	"06000027", # receive a ABORT_MD_RSP (0x06) with RSP Sucess
       	"0800FFFF", # receive a DELETE_MD_RSP (0x08) with RSP Sucess (0x00)
	]

try:
	remote_addr = (sys.argv[1], int(sys.argv[2]))
	dpsm = int(sys.argv[3])
except:
	print "Usage: %s <remote addr> <control PSM> <data PSM>" % sys.argv[0]
	sys.exit(1)

instance = MyInstance("00:00:00:00:00:00", False)
print "Connecting..."
mcl = instance.CreateMCL(remote_addr, dpsm)

loop.run()
