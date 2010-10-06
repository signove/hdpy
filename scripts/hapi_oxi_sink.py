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

	def DeviceFound(self, app, interface, device):
		print "Device %d discovered %s" % \
			(id(device), device.addr_control)
		if test_echo:
			glib.timeout_add(2000, self.echo, device)
		elif force_conn:
			method = self.connect
			glib.timeout_add(2000, method, device)
			if streaming_channel:
				# One more
				glib.timeout_add(4000, method, device)

	def DeviceRemoved(self, app, interface, device):
		print "Service %d removed" % id(device)

	# TODO Ugly trick to please PTS, needs to be improved!
	def InquireConfig(self, app, interface, data):
		return 0x00

	def echo(self, device):
		print "Initiating echo"
		self.device = device
		app.Echo(device,
			reply_handler=self.echo_ok,
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

	def connect(self, device):
		print "Connecting..."
		self.device = device
		# Sinks must not specify channel configuration, use 'Any'!
		app.CreateChannel(device, "Any",
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
		# print "Will retry in 60 seconds"
		# glib.timeout_add(60000, self.connect, self.device)

	def fd_acquired(self, fd):
		print "FD acquired"
		glib.io_add_watch(fd, watch_bitmap, data_received)

		if exercise_reconn:
			glib.timeout_add(3000, self.toogle_connection, fd)

	def fd_not_acquired(self, err):
		print "FD not acquired"

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


signal_handler = SignalHandler()

config = {"Role": "Sink", "DataType": 0x1004, "Description": "Oximeter sink"}

manager = HealthManager()
manager.RegisterSignalHandler(signal_handler)
app = manager.CreateApplication(config)

test_echo = "-e" in sys.argv
force_conn = "-f" in sys.argv
streaming_channel = "-s" in sys.argv # TC_SNK_CC_BV_08_C
exercise_reconn = "-r" in sys.argv # TC_SNK_HCT_BV_03_I
mcl_reconn = "-R" in sys.argv # TC_SNK_HCT_BV_05_C / 03_I
if mcl_reconn:
	exercise_reconn = True

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
