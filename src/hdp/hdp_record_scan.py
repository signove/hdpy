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

import hdp_record
import dbus

bus = dbus.SystemBus()

manager = dbus.Interface(bus.get_object("org.bluez", "/"),
						"org.bluez.Manager")

adapter_list = manager.ListAdapters()

for i in adapter_list:
	adapter = dbus.Interface(bus.get_object("org.bluez", i),
							"org.bluez.Adapter")
	properties  = adapter.GetProperties()
	try:
		device_list = properties["Devices"]
	except:
		device_list = []

	for n in device_list:
		device = dbus.Interface(bus.get_object("org.bluez", n),
							"org.bluez.Device")
		p = device.GetProperties()
		print "Discovering device", p['Address'], p['Name']
		try:
			services = device.DiscoverServices("")
		except:
			services = {}

		for handle in services.keys():
			hdp = hdp_record.parse_xml(services[handle])
			if hdp:
				print "Handle %08x:" % handle
				print hdp_record.parse_xml(services[handle])
