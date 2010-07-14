#!/usr/bin/env python

import sys
import glib
from hdp.dummy_ieee10404 import parse_message_str
from hdp.hdp import *

watch_bitmap = glib.IO_IN | glib.IO_ERR | glib.IO_HUP | glib.IO_NVAL

def data_received(sk, evt):
	data = None
	if evt & glib.IO_IN:
		data = sk.recv(1024)
		if data:
			print "Data received"
			response = parse_message_str(data)
			if response:
				sk.send(response)
				print "Response sent"

	more = (evt == glib.IO_IN and data)

	if not more:
		print "EOF"
		try:
			sk.shutdown(2)
		except IOError:
			pass
		sk.close()

	return more


class MyAgent(HealthAgent):
	def ChannelConnected(self, channel):
		channel.Acquire(self.FdAcquired, self.FdNotAcquired)
		print "Channel %d from %d up" % \
			(id(channel), id(channel.GetProperties()['Service']))

	def FdAcquired(self, fd):
		glib.io_add_watch(fd, watch_bitmap, data_received)
		print "FD acquired"

	def FdNotAcquired(self, err):
		print "FD not acquired"

	def ChannelDeleted(self, channel):
		print "Channel %d deleted" % id(channel)

	def ServiceDiscovered(self, service):
		print "Service %d discovered %s" % \
			(id(service), service.addr_control)

	def ServiceRemoved(self, service):
		print "Service %d removed" % id(service)


agent = MyAgent()

config = {"Role": "Sink", "DataType": 0x1004, "Description": "Oximeter sink"}

manager = HealthManager()
app = manager.CreateApplication(agent, config)

try:
	loop = glib.MainLoop()
	loop.run()
except KeyboardInterrupt:
	pass
finally:
	manager.DestroyApplication(app)
	print
	print "Application stopped"
	print
