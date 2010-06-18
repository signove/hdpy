#!/usr/bin/env python

from mcap_instance import MCAPInstance
import glib

class MyInstance(MCAPInstance):
	def Watch(self, fd, activity_cb, error_cb, arg):
		if activity_cb:
			glib.io_add_watch(fd, glib.IO_IN, activity_cb, arg)
		if error_cb:
			glib.io_add_watch(fd, glib.IO_ERR, error_cb, arg)
			glib.io_add_watch(fd, glib.IO_HUP, error_cb, arg)

	def MCLConnected(self, mcl):
		print "MCL has connected"

	def MCLDisconnected(self, mcl):
		print "MCL has disconnected"
		self.bye()

	def bye(self):
		glib.MainLoop.quit(loop)

	def RecvDump(self, mcl, message):
		print "Received", repr(message)
		return True

	def SendDump(self, mcl, message):
		print "Sent", repr(message)
		return True

instance = MyInstance("00:00:00:00:00:00", True)

print "Waiting for connections on default dev"
loop = glib.MainLoop()
loop.run()

print "Main loop finished."
print 'TESTS OK' 
