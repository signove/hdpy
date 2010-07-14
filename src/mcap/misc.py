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
from sys import exit

BDADDR_ANY = "00:00:00:00:00:00"

class BlauZ(object):

	def __init__(self):
		self.bus = dbus.SystemBus()
		obj = self.bus.get_object("org.bluez", "/")
		self.manager = dbus.Interface(obj, "org.bluez.Manager")

	def is_hci(self, s):
		return s.lower()[0:3] == "hci"

	def is_name(self, s):
		s = s.lower()
		return self.is_hci(s) or s in ("any", "default")

	def normalize(self, s):
		if self.is_name(s):
			return s.lower()
		else:
			return s.upper()

	def adapter_from_path(self, path):
		return path.split("/")[-1]

	def adapters(self):
		roll = self.manager.ListAdapters()
		return [self.adapter_from_path(str(path)) for path in roll]

	def adapter_path(self, name_or_addr):
		name_or_addr = self.normalize(name_or_addr)
		path = None
		if name_or_addr and name_or_addr == "default":
			try:
				path = self.manager.DefaultAdapter()
			except:
				path = None
		elif name_or_addr:
			try:
				path = self.manager.FindAdapter(name_or_addr)
			except:
				path = None
		return path

	def is_wildcard(self, name_or_addr):
		return name_or_addr in ("any", BDADDR_ANY, "", None)

	def adapter_iface(self, name_or_addr):
		path = self.adapter_path(name_or_addr)
		if not path or self.adapter_from_path(path) == "any":
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

	def device_addr(self, name):
		if self.is_hci(name):
			return self.adapter_addr(name)
		return name

	def adapter_addr_w(self, name):
		if self.is_wildcard(name):
			return BDADDR_ANY
		return self.adapter_addr(name)

	def adapter_name(self, addr):
		path = self.adapter_path(addr)
		if not path:
			return None
		adapter = self.adapter_from_path(path)
 		if adapter == "any":
			return None
		return adapter

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


_BlueZ = None

def BlueZ():
	global _BlueZ
	if not _BlueZ:
		_BlueZ = BlauZ()
	return _BlueZ


def parse_srv_params(args, wildcard=True):
	try:
		if len(args) < 2 or args[1] not in ("-a", "--adapter"):
			adapter = wildcard and "any" or "default"
		else:
			adapter = args[2]
		
		if wildcard:
			adapter = BlueZ().adapter_addr_w(adapter)
		else:
			adapter = BlueZ().adapter_addr(adapter)

		if adapter is None:
			raise ValueError("")

		return adapter

	except ValueError:
		print "Usage: %s [-a <adapter>]" % args[0]
		exit(1)
		

def parse_params(args, wildcard=True):
	try:
		if len(args) < 2:
			raise ValueError("")

		if args[1] in ("-a", "--adapter"):
			adapter = args[2]
			del args[1]
			del args[1]
		else:
			adapter = wildcard and "any" or "default"
		
		if wildcard:
			adapter = BlueZ().adapter_addr_w(adapter)
		else:
			adapter = BlueZ().adapter_addr(adapter)

		device = BlueZ().device_addr(args[1])

		if adapter is None or device is None:
			raise ValueError("")

		if len(args) > 2:
			cpsm = int(args[2])
		else:
			cpsm = 0x1001

		if len(args) > 3:
			dpsm = int(args[3])
		else:
			dpsm = cpsm + 2

		return adapter, device, cpsm, dpsm, (str(device), cpsm)

	except ValueError:
		print "Usage: %s [ -a <adapter> ] <device> [ cPSM [ dPSM ] ]" \
			% args[0]
		print "(default adapter = auto; default dPSM = cPSM + 2)"
		exit(1)


def test():
	# good ones
	name = "hci0"
	addr = "00:1b:DC:0F:C8:A9"
	# bad ones
	namef = "hci2"
	addrf = "00:1B:DC:0f:C8:A8"
	# wildcards 
	namew = "any"
	addrw = "00:00:00:00:00:00"

	print "Beginning tests"
	b = BlueZ()
	assert(addr.lower() == b.adapter_addr(addr).lower())
	assert(addr.lower() == b.adapter_addr(name).lower())
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
	assert(b.adapter_addr('default') == addr.upper())
	assert(b.adapter_name('default') == name)
	assert(b.adapter_addr_w(namew) == BDADDR_ANY)
	assert(b.adapter_addr_w(addrw) == BDADDR_ANY)
	assert(b.adapter_name_w(namew) == "any")
	assert(b.adapter_name_w(addrw) == "any")
	assert(b.adapters() == ['hci0', 'hci1'])
	print "Tests ok"


if __name__ == '__main__':
	test()
