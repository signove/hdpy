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


from mcap.mcap_defs import *
from mcap.mcap import *
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

	def new_cc(self, listener, sk, remote_addr):
		self.mcl = MCL(self, "00:00:00:00:00:00", MCAP_MCL_ROLE_ACCEPTOR, remote_addr, 0)
		assert(self.mcl.state == MCAP_MCL_STATE_IDLE)
		self.mcl.accept(sk)
		assert(self.mcl.state == MCAP_MCL_STATE_CONNECTED)

		print "Connected!"

	def error_cc(eslf, listener):
		pass

	def closed_mcl(self, socket, *args):
		pass

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

	def mdlconnected_mcl(self, mdl, reconn, err):
		glib.io_add_watch(mdl.sk, glib.IO_IN, self.recvdata, mdl)

	def mdlaborted_mcl(self, mcl, mdl):
		print "MDL aborted"

	def mdldeleted_mcl(self, mdl):
		print "MDL deleted"

	def mdlclosed_mcl(self, mdl):
		pass

	def recvdata(self, sk, evt, mdl):
		data = mdl.read()
		if not data:
			mdl.close()
			return False

		print "MDL", id(mdl), "data", data
		mdl.write(data + " PONG1 " + data)
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
