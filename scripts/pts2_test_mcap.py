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
		return True


class TestStub(object):

	GeneralCommands = ['bt_commads',
			   'mcap_commands'
			   'exit_menu']

	MCAPCommands = ['open_mcl',
			'close_mcl',
			'echo_mcl',
			'open_mdl',
			'close_mdl',
			'echo_mdl',
			'back_menu']

	def __init__(self):
		self.current_adapter = None
		self.bluetoothUtils = BluetoothUtils()

	def SelectAdapter(self):
		while True:
			selectedAdapter = self.PrintAdaptersPrompt()
			adapters = self.bluetoothUtils.GetAvailableAdapters()
			totalAdapters = len(adapters)
			if (selectedAdapter < 1 or selectedAdapter > totalAdapters):
				print "\t> > Invalid adapter. Please, insert a valid number"
			else:
				return adapters[selectedAdapter - 1]

	def SelectGeneralCommand(self):
		selectedCommand = self.SelectCommands(self.GeneralCommands)
		return selectedCommand

	def SelectMCAPCommand(self):
		selectedCommand = self.SelectCommands(self.MCAPCommands)
		return selectedCommand
	
	def PrintAdaptersPrompt(self):
		adapters = self.bluetoothUtils.GetAvailableAdapters()
		print "Select an adapter: "
		for index, adapter in enumerate(adapters, 1):
			print index, "-", adapter
		selectedAdapter = raw_input("#: ")
		return int(selectedAdapter)

        def SelectCommands(self, command_list):
                while True:
                        selectedCommand = self.PrintCommandsPrompt(command_list)
                        numberOfCommands = len(command_list)
                        if (selectedCommand < 1 or selectedCommand > numberOfCommands):
                                print "\t> > Invalid command. Please, insert a valid number"
                        else:
                                return command_list[selectedCommand - 1]


	def PrintCommandsPrompt(self, command_list):
		print "Select a command:"
		for index, command in enumerate(command_list,1):
			print index, "-", command
		selectedCommand = raw_input("#: ")
		return int(selectedCommand)


test = TestStub()
result = test.SelectMCAPCommand()
print ">>>", result
