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
import glib
import sys
from mcap.misc import parse_srv_params

class MyInstance(MCAPInstance):
	def MCLConnected(self, mcl, err):
		print "MCL has connected", id(mcl)

	def MCLReconnected(self, mcl, err):
		print "MCL has reconnected", id(mcl)

	def MCLDisconnected(self, mcl):
		print "MCL has disconnected", id(mcl)

	def MDLRequested(self, mcl, mdl, mdepid, config):
		print "MDL requested MDEP", mdepid, "config", config

	def MDLConnected(self, mdl, err):
		print "MDL connected", id(mdl)

	def MDLAborted(self, mcl, mdl):
		print "MDL aborted", id(mdl)

	def MDLClosed(self, mdl):
		print "MDL closed", id(mdl)

	def MDLDeleted(self, mdl):
		print "MDL deleted", id(mdl)

	def MDLInquire(self, mdepid, config):
		if not config:
			print "MDLInquire: resetting configuration"
			config = 0x01
		reliable = not (config == 0x02 and mdepid == 0x02)
		ok = True
		print "MDLInquire: answering", ok, reliable, config
		return ok, reliable, config

	def RecvDump(self, mcl, message):
		# print "Received command ", repr(message)
		return True

	def SendDump(self, mcl, message):
		# print "Sent command ", repr(message)
		return True

	def Recv(self, mdl, data):
		print "MDL", id(mdl), "data", data
		try:
			response = str(eval(data + (" + %d" % mdl.mdlid)))
		except:
			response = "ERROR IN EVAL"
		print "\tresponse is", response
		instance.Send(mdl, response)
		return True

adapter = parse_srv_params(sys.argv)
instance = MyInstance(adapter, True)
if "-r" in sys.argv:
	instance.ReconnectionDisable()
	print "Reconnections disabled"
if "-c" in sys.argv:
	instance.SyncDisable()
	print "CSP support disabled"

print "Waiting for connections on", adapter
loop = glib.MainLoop()
loop.run()
