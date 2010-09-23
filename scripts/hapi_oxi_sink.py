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


class MyAgent(HealthAgent):
	def ChannelConnected(self, channel):
		channel.Acquire(reply_handler=self.FdAcquired,
				error_handler=self.FdNotAcquired)
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
		if test_echo:
			glib.timeout_add(2000, self.echo, service)
		elif force_conn:
			method = self.connect
			glib.timeout_add(2000, method, service)

	def echo(self, service):
		print "Initiating echo"
		self.service = service
		app.Echo(service,
			reply_handler=self.EchoOk,
			error_handler=self.EchoNok)
		return False

	def EchoNok(self, *args):
		# print "Echo failed, retrying in 2 seconds"
		# glib.timeout_add(2000, self.echo, self.service)
		print "Echo failed"
	
	def EchoOk(self):
		# print "Echo Ok, connecting in 1 second..."
		# glib.timeout_add(1000, self.connect, self.service)
		print "Echo Ok"

	def ServiceRemoved(self, service):
		print "Service %d removed" % id(service)

	def connect(self, service):
		print "Connecting..."
		self.service = service
		# Sinks must not specify channel configuration, use 'Any'!
		app.CreateChannel(service, "Any",
				reply_handler=self.ChannelOk,
				error_handler=self.ChannelNok)
		return False

	def ChannelOk(self, channel):
		global counter
		counter = 0
		self.channel = channel
		print "Channel up"
		channel.Acquire(reply_handler=self.FdAcquired,
				error_handler=self.FdNotAcquired)

	def ChannelNok(self, err):
		print "Could not establish channel with service (%d)" % err
		# print "Will retry in 60 seconds"
		# glib.timeout_add(60000, self.connect, self.service)


agent = MyAgent()

config = {"Role": "Sink", "DataType": 0x1004, "Description": "Oximeter sink"}

manager = HealthManager()
app = manager.CreateApplication(agent, config)

test_echo = "-e" in sys.argv
force_conn = "-f" in sys.argv

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
