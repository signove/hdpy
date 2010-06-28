#!/usr/bin/env python

from mcap_instance import MCAPInstance
import glib

class MyInstance(MCAPInstance):
	def MCLConnected(self, mcl):
		print "MCL has connected", id(mcl)

	def MCLReconnected(self, mcl):
		print "MCL has reconnected", id(mcl)

	def MCLDisconnected(self, mcl):
		print "MCL has disconnected", id(mcl)

	def MDLRequested(self, mcl, mdl, mdepid, config):
		print "MDL requested MDEP", mdepid, "config", config

	def MDLConnected(self, mdl):
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

instance = MyInstance("00:00:00:00:00:00", True)

print "Waiting for connections on default dev"
loop = glib.MainLoop()
loop.run()
