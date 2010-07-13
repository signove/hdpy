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
import sys
from mcap.misc import parse_srv_params
import glib

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

	def MDLClosed(self, mdl):
		print "MDL closed", id(mdl)

	def MDLDeleted(self, mdl):
		print "MDL deleted", id(mdl)

	def RecvDump(self, mcl, message):
		print "Received command ", repr(message)
		return True

	def SendDump(self, mcl, message):
		print "Sent command ", repr(message)
		return True

	def Recv(self, mdl, data):
		print "MDL", id(mdl), "data", data
		instance.Send(mdl, data + " PONG " + data)
		return True

adapter = parse_srv_params(sys.argv)

instance = MyInstance(adapter, True)

print "Waiting for connections on", adapter
loop = glib.MainLoop()
loop.run()
