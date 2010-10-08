#!/usr/bin/env python

import sys
import glib
from hdp.dummy_ieee10404 import parse_message_str
import dbus
import dbus.service
import gobject
from dbus.mainloop.glib import DBusGMainLoop

DBusGMainLoop(set_as_default=True)
loop = gobject.MainLoop()
bus = dbus.SystemBus()


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
	def __init__(self):
		bus.add_signal_receiver(self.ChannelConnected,
			signal_name="ChannelConnected",
			bus_name="org.bluez",
			path_keyword="device",
			interface_keyword="interface",
			dbus_interface="org.bluez.HealthDevice")

		bus.add_signal_receiver(self.ChannelDeleted,
			signal_name="ChannelDeleted",
			bus_name="org.bluez",
			path_keyword="device",
			interface_keyword="interface",
			dbus_interface="org.bluez.HealthDevice")

	def ChannelConnected(self, channel, interface, device):
		print "Device %s channel %s up" % (device, channel)
		# channel.Acquire(reply_handler=self.fd_acquired,
		#		error_handler=self.fd_not_acquired)

	def ChannelDeleted(self, channel, interface, device):
		print "Device %s hannel %s deleted" % (device, channel)

	def fd_acquired(self, fd):
		print "FD acquired"
		glib.io_add_watch(fd, watch_bitmap, data_received)

	def fd_not_acquired(self, err):
		print "FD not acquired"


signal_handler = SignalHandler()

config = {"Role": "Sink", "DataType": dbus.types.UInt16(0x1004),
		"Description": "Oximeter sink"}

manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"),
					"org.bluez.HealthManager")
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
