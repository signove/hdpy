#!/usr/bin/env python

import sys
import glib
from hdp.dummy_ieee10404 import make_assoc_str, make_sample_str
from hdp.hdp import *
import time

watch_bitmap = glib.IO_IN | glib.IO_ERR | glib.IO_HUP | glib.IO_NVAL

counter = 0

def data_received(sk, evt):
	global counter
	data = None
	if evt & glib.IO_IN:
		try:
			data = sk.recv(1024)
		except IOError:
			data = ""
		if data:
			print "Data received"
			counter += 1
			if counter <= 5:
				# schedule next oximeter sample transmission
				glib.timeout_add(2000, send_sample, sk)
			else:
				app.DestroyChannel(agent.channel)

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


accept_channel = True


class MyAgent(HealthAgent):
	def ChannelConnected(self, channel):
		if accept_channel:
			print "Accepted channel"
			self.ChannelOk(channel)
		else:
			print "We don't like to accept connections, dropping"
			app.DestroyChannel(channel)

	def ChannelDeleted(self, channel):
		print "Channel %d deleted" % id(channel)

	def ServiceDiscovered(self, service):
		print "Service %d discovered %s" % \
			(id(service), service.addr_control)

		self.virgin = True
		if dont_initiate:
			print "Not initiating a connection"
			return

		if test_echo:
			method = self.echo
		else:
			method = self.connect
		glib.timeout_add(2000, method, service)
		if not test_echo and streaming_channel:
			# One more
			glib.timeout_add(4000, method, service, "Streaming")

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

	def connect(self, service, config="Reliable"):
		print "Connecting... (config=%s)" % config
		self.service = service
		app.CreateChannel(service, config,
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
		print "Will retry in 60 seconds"
		glib.timeout_add(60000, self.connect, self.service)

	def FdAcquired(self, fd):
		if echo_after_fd:
			glib.timeout_add(5000, self.echo, self.channel.service)

		if exercise_reconn:
			glib.timeout_add(3000, self.toogle_connection, fd)

		glib.io_add_watch(fd, watch_bitmap, data_received)
		print "FD acquired, sending association"
		time.sleep(2)
		try:
			fd.send(make_assoc_str())
			print "Sent"
		except IOError, e:
			print "Send error", e

	def toogle_connection(self, fd):
		print "Shutting channel down for reconnection test"
		fd.close()
		glib.timeout_add(3000, self.toogle_connection_2)
		if mcl_reconn:
			print "\tShutting MCL down too"
			self.service.CloseMCL()
		return False

	def toogle_connection_2(self):
		print "Reconnecting channel"
		self.channel.Acquire(reply_handler=self.FdAcquired,
				error_handler=self.FdNotAcquired)
		return False

	def FdNotAcquired(self, err):
		print "FD not acquired"

	def ServiceRemoved(self, service):
		print "Service %d removed" % id(service)

	def InquireConfig(self, mdepid, config, is_sink):
		# TODO Ugly trick to please PTS, needs to be improved!
		if streaming_channel:
			if self.virgin:
				config = 0x01 # Reliable 1st time
				self.virgin = False
			else:
				config = 0x02 # Streaming
		else:
			config = 0x01 # Reliable is default

		print "InquireConfig: returning %d" % config
		return config


test_echo = "-e" in sys.argv
dont_initiate = "-d" in sys.argv
echo_after_fd = "-ea" in sys.argv # TC_SRC_DEP_BV_01_I
streaming_channel = "-s" in sys.argv # TC_SRC_CC_BV_07_C
exercise_reconn = "-r" in sys.argv # TC_SRC_HCT_BV_05_I
mcl_reconn = "-R" in sys.argv # TC_SRC_HCT_BV_03_I
if mcl_reconn:
	exercise_reconn = True

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
