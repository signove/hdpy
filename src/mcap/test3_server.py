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


from mcap_instance import MCAPInstance
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

	def MDLAborted(self, mcl, mdl):
		print "MDL aborted", id(mdl)

	def MDLClosed(self, mdl):
		print "MDL closed", id(mdl)

	def MDLDeleted(self, mdl):
		print "MDL deleted", id(mdl)

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

instance = MyInstance("00:00:00:00:00:00", True)

print "Waiting for connections on default dev"
loop = glib.MainLoop()
loop.run()
