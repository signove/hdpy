#!/usr/bin/env python

import sys
import glib
from hdp.dummy_ieee10404 import make_assoc_str, make_sample_str
from hdp.hdp import *
import time

watch_bitmap = glib.IO_IN | glib.IO_ERR | glib.IO_HUP | glib.IO_NVAL

counter = 0

def data_received(sk, evt, device, channel):
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
				device.DestroyChannel(channel)

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


class SignalHandler(object):
	def ChannelConnected(self, device, interface, channel):
		if accept_channel:
			print "Accepted channel"
			self.channel_ok(channel)
		else:
			print "We don't like to accept connections, dropping"
			device.DestroyChannel(channel)

	def ChannelDeleted(self, device, interface, channel):
		print "Channel %d deleted" % id(channel)

	def DeviceFound(self, app, interface, device):
		print "Device %d discovered %s" % \
			(id(device), device.addr_control)

		self.virgin = True
		if dont_initiate:
			print "Not initiating a connection"
			return

		if test_echo:
			method = self.echo
		else:
			method = self.connect
		glib.timeout_add(2000, method, device)
		if not test_echo and streaming_channel:
			# One more
			glib.timeout_add(4000, method, device, "Streaming")

	def DeviceRemoved(self, app, interface, device):
		print "Device %d removed" % id(device)

	# TODO Ugly trick to please PTS, needs to be improved!
	def InquireConfig(self, app, interface, data):
		mdepid, config, is_sink = data
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

	def echo(self, device):
		print "Initiating echo"
		self.device = device
		device.Echo(reply_handler=self.echo_ok,
			    error_handler=self.echo_nok)
		return False

	def echo_nok(self, *args):
		# print "Echo failed, retrying in 2 seconds"
		# glib.timeout_add(2000, self.echo, self.device)
		print "Echo failed"
	
	def echo_ok(self):
		# print "Echo Ok, connecting in 1 second..."
		# glib.timeout_add(1000, self.connect, self.device)
		print "Echo Ok"

	def connect(self, device, config="Reliable"):
		print "Connecting... (config=%s)" % config
		self.device = device
		device.CreateChannel(None, config,
				reply_handler=self.channel_ok,
				error_handler=self.channel_nok)
		return False

	def channel_ok(self, channel):
		global counter
		counter = 0
		self.channel = channel
		print "Channel up"
		channel.Acquire(reply_handler=self.fd_acquired,
				error_handler=self.fd_not_acquired)

	def channel_nok(self, err):
		print "Could not establish channel with device (%d)" % err
		print "Will retry in 60 seconds"
		glib.timeout_add(60000, self.connect, self.device)

	def fd_acquired(self, fd):
		if echo_after_fd:
			glib.timeout_add(5000, self.echo, self.channel.device)

		if exercise_reconn:
			glib.timeout_add(3000, self.toogle_connection, fd)

		glib.io_add_watch(fd, watch_bitmap, data_received,
					self.channel.device, self.channel)
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
			self.device.CloseMCL()
		return False

	def toogle_connection_2(self):
		print "Reconnecting channel"
		self.channel.Acquire(reply_handler=self.fd_acquired,
				error_handler=self.fd_not_acquired)
		return False

	def fd_not_acquired(self, err):
		print "FD not acquired"


test_echo = "-e" in sys.argv
dont_initiate = "-d" in sys.argv
echo_after_fd = "-ea" in sys.argv # TC_SRC_DEP_BV_01_I
streaming_channel = "-s" in sys.argv # TC_SRC_CC_BV_07_C
exercise_reconn = "-r" in sys.argv # TC_SRC_HCT_BV_05_I
mcl_reconn = "-R" in sys.argv # TC_SRC_HCT_BV_03_I
if mcl_reconn:
	exercise_reconn = True

signal_handler = SignalHandler()

config = {"Role": "Source", "DataType": 0x1004, "Description": "Oximeter source"}

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
