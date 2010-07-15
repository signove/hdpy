#!/usr/bin/env python

import sys
import glib
from hdp.dummy_ieee10404 import make_assoc_str, make_sample_str
from hdp.hdp import *

watch_bitmap = glib.IO_IN | glib.IO_ERR | glib.IO_HUP | glib.IO_NVAL


def data_received(sk, evt):
	data = None
	if evt & glib.IO_IN:
		data = sk.recv(1024)
		if data:
			print "Data received"
			# schedule next oximeter sample transmission
			glib.timeout_add(2000, send_sample, sk)

	more = (evt == glib.IO_IN and data)

	if not more:
		print "EOF"
		try:
			sk.shutdown(2)
		except IOError:
			pass
		sk.close()

	return more


def send_sample(sk):
	try:
		sk.send(make_sample_str())
	except IOError:
		pass
	return False


class MyAgent(HealthAgent):
	def ChannelConnected(self, channel):
		print "We don't like to accept connections, dropping"
		app.DeleteChannel(channel)

	def ChannelDeleted(self, channel):
		print "Channel %d deleted" % id(channel)

	def ServiceDiscovered(self, service):
		print "Service %d discovered %s" % \
			(id(service), service.addr_control)
		app.CreateChannel(service, "Reliable", reply_handler=self.ChannelOk,
				error_handler=self.ChannelNok)

	def ChannelOk(self, channel):
		print "Channel up"
		channel.Acquire(reply_handler=self.FdAcquired,
				error_handler=self.FdNotAcquired)

	def ChannelNok(self, err):
		print "Could not establish channel with service"

	def FdAcquired(self, fd):
		glib.io_add_watch(fd, watch_bitmap, data_received)
		print "FD acquired, sending association"
		try:
			fd.send(make_assoc_str())
		except IOError:
			pass

	def FdNotAcquired(self, err):
		print "FD not acquired"

	def ServiceRemoved(self, service):
		print "Service %d removed" % id(service)


agent = MyAgent()

config = {"Role": "Source", "DataType": 0x1004, "Description": "Oximeter source"}

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
