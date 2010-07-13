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
import sys

### Class to deal with Bluetooth issues

class BluetoothUtils(object):

	def __init__(self, adapter_name):
        	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        	self.bus = dbus.SystemBus()
		self.InitDBus(adapter_name)

	# initialize DBus things here
	def InitDBus(self, adapter_name):
		self.root_obj = self.bus.get_object("org.bluez", "/")
		self.manager = dbus.Interface(self.root_obj, "org.bluez.Manager")
		self.adapter_path = self.manager.FindAdapter(adapter_name)
		
		self.adapter_obj = self.bus.get_object("org.bluez", self.adapter_path)	
		self.adapter = dbus.Interface(self.adapter_obj, "org.bluez.Adapter")

	# return a list of availble adapters
	def GetAvailableAdapters(self):
		properties = self.adapter.GetProperties()
		return properties['Devices']

	def GetAdapterAddress(self, adapter):
		device = dbus.Interface(self.bus.get_object("org.bluez",adapter),"org.bluez.Device")
		properties = device.GetProperties()
		return properties['Address']
		

### Class to deal with MCAP issues

class MyTestInstance(MCAPInstance):

	def __init__(self, adapter, listener):
                MCAPInstance.__init__(self, adapter, listener)
	
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

	def __init__(self, adapter_name):
		self.current_adapter = None
		self.bluetoothUtils = BluetoothUtils(adapter_name)
		self.instance = MyTestInstance("00:00:00:00:00:00", False)

	def Start(self):
		while True:
			self.SelectGeneralCommand()

	def Exit(self):
		sys.exit(0)
		print "Finished"

	def EchoMCL(self):
		print 'ECHO MCL'

	def GetParam(self, message, number_of_params):
		user_input = raw_input("\t" + message + " ")
		params = user_input.split()
		return tuple(params)

	def ShowAdapter(self):
		if (self.current_adapter == None):
			print 'No adapter is defined'
		else:
			print self.current_adapter

	def SelectAdapter(self):
		while True:
			selectedAdapter = self.PrintAdaptersPrompt()
			adapters = self.bluetoothUtils.GetAvailableAdapters()
			totalAdapters = len(adapters)
			if (selectedAdapter < 1 or selectedAdapter > totalAdapters):
				print "\t> > Invalid adapter. Please, insert a valid number"
			else:
				self.current_adapter = adapters[selectedAdapter - 1]
				break

	def SelectGeneralCommand(self):
		selectedCommand = self.SelectCommands(GeneralCommands)
		selectedCommand[1](self)
		return selectedCommand

	def SelectMCAPCommand(self):
		selectedCommand = self.SelectCommands(MCAPCommands)
		method = selectedCommand[1]

		# parameters: MDLID, MDEPID, CONF
		if ( method in [MyTestInstance.CreateMDL] ):
			if (self.current_mcl == None):
				print "\t > > Create a MCL before"
			else:
				mdepid, conf = self.GetParam("Insert MDEPID, CONF:",2)	
				mdlid = self.instance.CreateMDLID(self.current_mcl)
				print '**', self.current_mcl.state
				if (mdlid != 0):
					method(self.instance, self.current_mcl, mdlid, int(mdepid), int(conf))
					print "MDL created with ID", mdlid
				else:	
					print "Could not create MDL" 
				

		# parameters: MCL
		elif ( method in [MyTestInstance.CloseMCL, MyTestInstance.DeleteMCL, MyTestInstance.DeleteAll] ):
			print '**', self.current_mcl.remote_addr
			method(self.instance, self.current_mcl)

		#parameters: MDL
		elif ( method in [MyTestInstance.CloseMDL, MyTestInstance.DeleteMDL] ):
			if (self.current_mcl == None):
				print "\t > > Create a MCL before"
			else:
				mdlid = self.GetParam("Insert MDL ID:",1)
				mdl = self.current_mcl.get_mdl(mdlid)
				if (mdl == None):
					print "\t > > Invalid MDL ID"
				else:
					method(self.instance, mdl)

		#parameters: ADDR, CPSM, DPSM
		elif ( method in [MyTestInstance.CreateMCL] ):
			if (self.current_adapter == None):
				print "\t > > Select an adapter before"
			else:
				cpsm, dpsm = self.GetParam("Insert cPSM dPSM:", 2)
				addr = self.bluetoothUtils.GetAdapterAddress(self.current_adapter)
				print '--', addr
				self.current_mcl = method(self.instance, (addr, int(cpsm)), int(dpsm))		
				print '++', self.current_mcl.remote_addr
		
		return selectedCommand
	
	def SelectBTCommand(self):
		selectedCommand = self.SelectCommands(BTCommands)
		selectedCommand[1](self)
		return selectedCommand

	def PrintAdaptersPrompt(self):
		adapters = self.bluetoothUtils.GetAvailableAdapters()
		print "\nSelect an adapter: "
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
		print "\nSelect a command:"
		for index, command in enumerate(command_list,1):
			print index, "-", command[0]
		selectedCommand = raw_input("#: ")
		return int(selectedCommand)


GeneralCommands = [('bt_commads',    TestStub.SelectBTCommand),
                   ('mcap_commands', TestStub.SelectMCAPCommand),
                   ('exit_menu',     TestStub.Exit)]

BTCommands = [('select_adp',     TestStub.SelectAdapter),
	      ('current_adp',    TestStub.ShowAdapter),
              ('back_menu',      TestStub.SelectGeneralCommand)]

MCAPCommands = [('create_mcl',   MyTestInstance.CreateMCL),
                ('close_mcl',    MyTestInstance.CloseMCL),
                ('delete_mcl',   MyTestInstance.DeleteMCL),
                ('echo_mcl',     TestStub.EchoMCL),
                ('create_mdl',   MyTestInstance.CreateMDL),
                ('connect_mdl',  MyTestInstance.ConnectMDL),
                ('delete_mdl',   MyTestInstance.DeleteMDL),
                ('delete_all',   MyTestInstance.DeleteAll),
                ('echo_mdl',     MyTestInstance.Send),
                ('back_menu',    TestStub.SelectGeneralCommand)]

try:
        adapter_name = sys.argv[1]
except:
        print "Usage: %s <adapter name>" % sys.argv[0]
        sys.exit(1)

test = TestStub(adapter_name)
result = test.Start()
