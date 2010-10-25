#!/usr/bin/env python

import sys
import glib
from hdp.dummy_ieee10404 import parse_message_str
from hdp.hdp import *

watch_bitmap = glib.IO_IN | glib.IO_ERR | glib.IO_HUP | glib.IO_NVAL

def data_received(sk, evt):
	data = None
	if evt & glib.IO_IN:
		try:
			data = sk.recv(1024)
		except IOError:
			data = ""
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


class SignalHandler(object):
	def ChannelConnected(self, device, interface, channel):
		channel.Acquire(reply_handler=self.fd_acquired,
				error_handler=self.fd_not_acquired)
		print "Channel %d from %d up" % \
			(id(channel), id(channel.GetProperties()['Device']))

	def ChannelDeleted(self, device, interface, channel):
		print "Channel %d deleted" % id(channel)

	def fd_acquired(self, fd):
		print "FD acquired"
		glib.io_add_watch(fd, watch_bitmap, data_received)

	def fd_not_acquired(self, err):
		print "FD not acquired"


signal_handler = SignalHandler()

config = {"Role": "Sink", "DataType": 0x1004, "Description": "Oximeter sink"}

manager = HealthManager()
manager.RegisterSignalHandler(signal_handler)
app = manager.CreateApplication(config)

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
