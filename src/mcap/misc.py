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

import dbus

class BlueZ(object):
	BDADDR_ANY = "00:00:00:00:00:00"

	def __init__(self):
		self.bus = dbus.SystemBus()
		obj = self.bus.get_object("org.bluez", "/")
		self.manager = dbus.Interface(obj, "org.bluez.Manager")

	def adapter_path(self, name_or_addr):
		if name_or_addr:
			try:
				path = self.manager.FindAdapter(name_or_addr)
			except:
				path = None
		else:
			path = self.manager.DefaultAdapter()
		return path

	def is_wildcard(self, name_or_addr):
		return name_or_addr is None or \
			name_or_addr in ("any", self.BDADDR_ANY, "")

	def adapter_iface(self, name_or_addr):
		path = self.adapter_path(name_or_addr)
		if not path or path[-3:] == "any":
			return None
		obj = self.bus.get_object("org.bluez", path)
		return dbus.Interface(obj, "org.bluez.Adapter")

	def adapter_properties(self, name_or_addr):
		iface = self.adapter_iface(name_or_addr)
		if not iface:
			return None
		return iface.GetProperties()

	def adapter_addr(self, name):
		props = self.adapter_properties(name)
		if not props:
			return None
		return props['Address']

	def adapter_addr_w(self, name):
		if self.is_wildcard(name):
			return self.BDADDR_ANY
		return self.adapter_addr(name)

	def adapter_name(self, addr):
		path = self.adapter_path(addr)
		if not path or path[-3:] == "any":
			return None
		return path.split("/")[-1]

	def adapter_name_w(self, addr):
		if self.is_wildcard(addr):
			return "any"
		return self.adapter_name(addr)

	def adapter_service(self, adapter):
		path = self.adapter_path(adapter)
		if not path:
			return None
		obj = self.bus.get_object("org.bluez", path)
		return dbus.Interface(obj, "org.bluez.Service")

	def add_record(self, adapter, xml):
		service = self.adapter_service(adapter)
		if not service:
			return None
		return service.AddRecord(xml)

	def remove_record(self, adapter, handle):
		service = self.adapter_service(adapter)
		if not service:
			return None
		service.RemoveRecord(dbus.UInt32(handle))


def test():
	# good ones
	name = "hci0"
	addr = "00:1B:DC:0F:C8:A9"
	# bad ones
	namef = "hci2"
	addrf = "00:1B:DC:0F:C8:A8"
	# wildcards 
	namew = "any"
	addrw = "00:00:00:00:00:00"

	print "Beginning tests"
	b = BlueZ()
	assert(addr == b.adapter_addr(addr))
	assert(addr == b.adapter_addr(name))
	assert(name == b.adapter_name(name))
	assert(name == b.adapter_name(addr))
	assert(b.adapter_addr(addrf) is None)
	assert(b.adapter_addr(namef) is None)
	assert(b.adapter_name(namef) is None)
	assert(b.adapter_name(addrf) is None)
	assert(b.adapter_addr(namew) is None)
	assert(b.adapter_name(namew) is None)
	assert(b.adapter_addr(addrw) is None)
	assert(b.adapter_name(addrw) is None)
	assert(b.adapter_addr_w(namew) == BlueZ.BDADDR_ANY)
	assert(b.adapter_addr_w(addrw) == BlueZ.BDADDR_ANY)
	assert(b.adapter_name_w(namew) == "any")
	assert(b.adapter_name_w(addrw) == "any")
	print "Tests ok"


if __name__ == '__main__':
	test()
