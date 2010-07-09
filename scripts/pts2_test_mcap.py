#!/usr/bin/env python
# -*- coding: utf-8

################################################################
#
# Copyright (c) 2010 Signove. All rights reserved.
# See the COPYING file for licensing details.
#
# Autors: Elvis Pfützenreuter < epx at signove dot com >
#         Raul Herbster < raul dot herbster at signove dot com >
################################################################


from mcap.mcap_instance import MCAPInstance
import gobject
import dbus.mainloop.glib
import glib

### Class to deal with Bluetooth issues

class BluetoothUtils(object):

	def __init__(self):
        	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        	self.bus = dbus.SystemBus()
		self.InitDBus()

	# initialize DBus things here
	def InitDBus(self):
		self.root_obj = self.bus.get_object("org.bluez", "/")
		self.manager = dbus.Interface(self.root_obj, "org.bluez.Manager")
		self.adapter_obj = self.bus.get_object("org.bluez", self.manager.DefaultAdapter())	
		self.adapter = dbus.Interface(self.adapter_obj, "org.bluez.Adapter")

	# return a list of availble adapters
	def GetAvailableAdapters(self):
		properties = self.adapter.GetProperties()
		return properties['Devices']

	# send connection request to an adapter. It is possible
        # to request an encripted connection
	def SendConnectionRequest(self, adapter, encrypted):
		pass		

### Class to deal with MCAP issues

class MyInstance(MCAPInstance):
	def MCLConnected(self, mcl, err):
		print "MCL has connected", id(mcl)

	def MCLReconnected(self, mcl, err):
		print "MCL has reconnected", id(mcl)

	def MCLDisconnected(self, mcl):
		print "MCL has disconnected", id(mcl)

	def MDLRequested(self, mcl, mdl, mdepid, config):
		print "MDL requested MDEP", mdepid, "config", config

	def MDLConnected(self, mdl, err):
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

def test():
	bt_utils = BluetoothUtils()

	available_adapters = bt_utils.GetAvailableAdapters()
	for adp in available_adapters:
		print "#", adp

test()
