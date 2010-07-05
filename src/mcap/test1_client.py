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


from mcap_defs import *
from mcap import *
import time
import sys
import glib

class MCAPSessionClientStub:

	sent = [ 
		"0BFF", # send an invalid message (Op Code does not exist)
		"01FF000ABC", # send a CREATE_MD_REQ (0x01) with invalid MDLID == 0xFF00 (DO NOT ACCEPT)
        	"0100230ABC", # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0023 CONF = 0xBC (ACCEPT)
		"0100240ABC", # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0024 CONF = 0xBC (ACCEPT)
        	"0100270ABC",  # send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0027 CONF = 0xBC (ACCEPT)
        	"050027", # send valid ABORT_MD_REQ (0x05) MDLID == 0x0027
        	"070030", # send an invalid DELETE_MD_REQ (0x07) MDLID == 0x0030
        	"07FFFF", # send a valid DELETE_MD_REQ (0x07) MDLID == MDL_ID_ALL (0XFFFF)
		]

	received = [
		"00010000", # receive a ERROR_RSP (0x00) with RSP Invalid OP (0x01)
		"0205FF00", # receive a CREATE_MD_RSP (0x02) with RSP Invalid MDL (0x05)
        	"02000023BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
		"02000024BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
        	"02000027BC", # receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
        	"06000027", # receive a ABORT_MD_RSP (0x06) with RSP Sucess
        	"08050030", # receive an invalid DELETE_MD_RSP (0x08) 
        	"0800FFFF", # receive a DELETE_MD_RSP (0x08) with RSP Sucess (0x00)
		]

	def __init__(self):
 		self.counter = 0

	def stop_session(self, mcl):
		glib.MainLoop.quit(self.inLoop)

	def closed_mcl(self, mcl, *args):
		print "Closed MCL!"
		self.stop_session(mcl)

	def activity_mcl(self, mcl, recv, message, *args):
		if recv:
			print "Received raw msg", repr(message)
			expected_msg = testmsg(self.received[self.counter])
			assert(message == expected_msg)
			self.check_asserts(mcl)
			self.counter += 1
			if message[0:2] != "\x02\x00":
				self.take_initiative(mcl)
		else:
			print "Sent raw msg", repr(message)
		return True

	def take_initiative(self, mcl):
		to = 1000
		if self.counter >= 4:
			to = 2000 
		glib.timeout_add(to, self.take_initiative_cb, mcl)

	def take_initiative_cb(self, mcl, *args):
		if self.counter >= len(self.sent):
			self.stop_session(mcl)
		else:
			msg = testmsg(self.sent[self.counter])
			print "Sending ", repr(msg)
			mcl.sm.send_raw_message(msg)
		# It is important to return False.
		return False

	def loop(self):
		self.inLoop = glib.MainLoop()
		self.inLoop.run()

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
			assert(mcl.count_mdls() == 3)
			assert(mcl.state == MCAP_MCL_STATE_ACTIVE)
			assert(mcl.sm.request_in_flight == 0)
		elif (self.counter == 7):
			assert(mcl.count_mdls() == 0)
			assert(mcl.state == MCAP_MCL_STATE_CONNECTED)
			assert(mcl.sm.request_in_flight == 0)

	def mdlgranted_mcl(self, mcl, mdl, err):
		# An MDL we requested has been granted. Now it is expected
		# that we connect.
		if err:
			print "MDL not granted!", err
			return

		print "MDL granted:", id(mdl)

		if mdl.mdlid == 0x27:
			# this one we will abort
			self.take_initiative(mcl)
		else:
			# Postpone connection so asserts see PENDING state
			glib.timeout_add(1000, self.mdl_do_connect, mdl)

	def mdl_do_connect(self, mdl):
		mdl.connect()
		return False

	def mclconnected_mcl(self, mcl, err):
		if err:
			print "Not connected!", err
			return
		print "Connected!"
		session.take_initiative(mcl)
		assert(mcl.state == MCAP_MCL_STATE_CONNECTED)

	def mdlconnected_mcl(self, mdl, reconnection, err):
		if err:
			print "MDL not connected!"
			return

		print "MDL connected"
		assert(mdl.mcl.state == MCAP_MCL_STATE_ACTIVE)
		glib.io_add_watch(mdl.sk, glib.IO_IN | glib.IO_ERR | glib.IO_HUP,
						self.recvdata, mdl)
		glib.timeout_add(1500, self.ping, mdl)
		self.take_initiative(mdl.mcl)
		
	def mdlaborted_mcl(self, mcl, mdl):
		pass

	def mdldeleted_mcl(self, mdl):
		pass

	def ping(self, mdl):
		if not mdl.active():
			return False
		mdl.write("hdpy ping ")
		return True

	def recvdata(self, sk, evt, mdl):
		if evt != glib.IO_IN:
			return False
		print "MDL", id(mdl),
		data = mdl.read()
		print "data", data
		return True
		
	def mdlclosed_mcl(self, mdl):
		print "MDL closed"

try:
	remote_addr = (sys.argv[1], int(sys.argv[2]))
	dpsm = int(sys.argv[3])
except:
	print "Usage: %s <remote addr> <control PSM> <data PSM>" % sys.argv[0]
	sys.exit(1)

session = MCAPSessionClientStub()
mcl = MCL(session, "00:00:00:00:00:00", MCAP_MCL_ROLE_INITIATOR, remote_addr, dpsm)

assert(mcl.state == MCAP_MCL_STATE_IDLE)

print "Requesting connection..."
mcl.connect()

session.loop()

print 'TESTS OK' 
