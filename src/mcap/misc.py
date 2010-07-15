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
from mcap_loop import timeout_call, timeout_cancel
import dbus.mainloop.glib

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

BDADDR_ANY = "00:00:00:00:00:00"

# FIXME detect bluez out/in again (survives restarts)
# FIXME convert prints to DBG

exc = dbus.exceptions.DBusException


class ObserverProxy():
	def __init__(self, obj, uuid):
		self.obj = obj
		self.uuid = uuid128(uuid)
		self.devmap = {}

		# we don't force the observer to have all methods
		self.Created = getattr(obj, "device_created", self.noop)
		self.Removed = getattr(obj, "device_removed", self.noop)
		self.Found = getattr(obj, "device_found", self.noop)
		self.Disappeared = getattr(obj, "device_disappeared", self.noop)
		self.Dead = getattr(obj, "bluetooth_dead", self.noop)
		self.Alive = getattr(obj, "bluetooth_alive", self.noop)
		self.AdapterAdded = getattr(obj, "adapter_added", self.noop)
		self.AdapterRemoved = getattr(obj, "adapter_removed", self.noop)
		
	def noop(self, *args):
		print "noop", args
		pass

	def interesting(self, uuids):
		for candidate in uuids:
			candidate = uuid128(str(candidate))
			if candidate == self.uuid:
				return True
		return False

	def device_created(self, path, adapter, addr, uuids, forced):
		if self.interesting(uuids):
			self.devmap[path] = (adapter, addr)
			self.Created(addr)

	def device_removed(self, path):
		if path in self.devmap:
			adapter, addr = self.devmap[path]
			del self.devmap[path]
			self.Removed(addr)

	def adapter_added(self, name):
		self.AdapterAdded(name)

	def adapter_removed(self, path):
		self.AdapterRemoved(name)

	def dead(self):
		self.devmap = {}
		self.Dead()

	def alive(self):
		self.Alive()

	def device_addr(self, path):
		if path in self.devmap:
			return self.devmap[path][1]
		return None

	def device_found(self, path):
		addr = self.device_addr(path)
		if addr:
			# Reports only if it has been paired
			self.Found(addr)

	def device_disappeared(self, path):
		addr = self.device_addr(path)
		if addr:
			self.Disappeared(addr)


BASE_BT_UUID = "00000000-0000-1000-8000-00805F9B34FB"

def uuid128(uuid_any):
	uuid_any = uuid_any.strip()
	if len(uuid_any) == 4:
		uuid = BASE_BT_UUID[0:4] + uuid_any + BASE_BT_UUID[8:]
	else:
		uuid = uuid_any
	return uuid.upper()


class BlauZ(object):

	def __init__(self):
		self.observers = {}
		self.devmap = {}
		self.search_timeout = None
		self.bus = dbus.SystemBus()
		self.start_dbus()

	def handle_err(self, exception):
		name = exception.get_dbus_name()

		if name == "org.freedesktop.DBus.Error.ServiceUnknown":
			# BlueZ is out
			self.dead()
		else:
			print
			print exception.get_dbus_name()
			print exception.get_dbus_message()
			print

	def start_dbus(self):
		try:
			obj = self.bus.get_object("org.bluez", "/")
			self.manager = dbus.Interface(obj, "org.bluez.Manager")

       			self.manager.connect_to_signal("AdapterAdded",
				self.signal_adapter_added)
       			self.manager.connect_to_signal("AdapterRemoved",
				self.signal_adapter_removed)
       			self.manager.connect_to_signal("DefaultAdapterChanged",
				self.signal_default_adapter_changed)
		except exc, e:
			self.handle_err(e)
			self.manager = None
			return

		for handle, observer in self.observers.items():
			observer.alive()

		for path in self._adapters():
			self.signal_adapter_added(path, True)

	def signal_adapter_added(self, path, forced=False):
		print "Added", path
		name = self.adapter_from_path(path)
		adapter_iface = self._adapter_iface(path)
		if not adapter_iface:
			return

		try:
        		# device.connect_to_signal("PropertyChanged", device_changed)
			adapter_iface.connect_to_signal("DeviceCreated",
				self.signal_device_created)
			adapter_iface.connect_to_signal("DeviceRemoved",
				self.signal_device_removed)
			adapter_iface.connect_to_signal("DeviceFound",
				self.signal_device_found)
			adapter_iface.connect_to_signal("DeviceDisappeared",
				self.signal_device_disappeared)
			devs = adapter_iface.GetProperties()["Devices"]

			for handle, observer in self.observers.items():
				observer.adapter_added(name)

			self.adapter_known_devices(path, devs)

		except exc, e:
			self.handle_err(e)

	def signal_adapter_removed(self, path):
		print "Removed", path

		name = self.adapter_from_path(path)

		for devpath in self.devmap.keys():
			addr, adapter, uuids = self.devmap[devpath]
			if adapter == path:
				self.signal_device_removed(devpath, True)

		for handle, observer in self.observers.items():
			observer.adapter_removed(name)

	def signal_default_adapter_changed(self, path):
		print "Default", path

	def _device_iface(self, path):
		obj = self.bus.get_object("org.bluez", path)
		devif = dbus.Interface(obj, "org.bluez.Device")
		return devif

	def device_props(self, path):
		devif = self._device_iface(path)
		props = devif.GetProperties()
		return props

	def adapter_known_devices(self, path, devices):
		for dev_path in devices:
			self.signal_device_created(dev_path, True)

	def signal_device_created(self, path, forced=False):
		if path in self.devmap:
			return

		print "Device created:", path
		props = self.device_props(path)
		addr = str(props["Address"]).upper()
		adapter = str(props["Adapter"])
		uuids = props["UUIDs"]

		for handle, observer in self.observers.items():
			observer.device_created(path, adapter, addr, uuids,
				forced)

		self.devmap[path] = (adapter, addr, uuids)

	def signal_device_removed(self, path, forced=False):
		if path not in self.devmap:
			return

		print "Device removed:", path
		for handle, observer in self.observers.items():
			observer.device_removed(path)

		del self.devmap[path]

	def signal_device_found(self, found_addr, found_props):
		found_addr = found_addr.upper()
		for path in self.devmap.keys():
			adapter, addr, uuids = self.devmap[path]
			if found_addr == addr:
				break
		else:
			return

		print "Device found:", path
		for handle, observer in self.observers.items():
			props = self.device_props(path)
			observer.device_found(path)

	def signal_device_disappeared(self, path):
		print "Device disappeared:", path
		for handle, observer in self.observers.items():
			observer.device_disappeared(path)

	def dead(self):
		print "D-Bus BlueZ shot down"
		self.manager = None
		self.devmap = {}
		for handle, observer in self.observers.items():
			observer.dead()

	def alive(self):
		return self.manager is not None

	def register_observer(self, observer, uuid):
		obj = ObserverProxy(observer, uuid)
		self.observers[id(observer)] = obj

		if not self.alive():
			obj.dead()
			return
		obj.alive()

		adapters = {}
		for path in self.devmap.keys():
			adapter, addr, uuids = self.devmap[path]
			if adapter not in adapters:
				adapters[adapter] = 1
				obj.adapter_added(self.adapter_from_path(adapter))
			obj.device_created(path, adapter, addr, uuids, True)

	def unregister_observer(self, observer):
		try:
			del self.observers[id(observer)]
		except KeyError:
			pass

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

	def _adapters(self):
		if not self.manager:
			return []

		try:
			roll = self.manager.ListAdapters()
		except exc, e:
			self.handle_err(e)
			roll = []

		return roll

	def adapters(self):
		roll = self._adapters()
		return [self.adapter_from_path(str(path)) for path in roll]

	def adapter_path(self, name_or_addr):
		if not self.manager:
			return None

		path = None
		name_or_addr = self.normalize(name_or_addr)

		if name_or_addr and name_or_addr == "default":
			try:
				path = self.manager.DefaultAdapter()
			except exc, e:
				self.handle_err(e)
				path = None

		elif name_or_addr:
			try:
				path = self.manager.FindAdapter(name_or_addr)
			except exc, e:
				self.handle_err(e)
				path = None

		return path

	def is_wildcard(self, name_or_addr):
		return name_or_addr in ("any", BDADDR_ANY, "", None)

	def adapter_iface(self, name_or_addr):
		path = self.adapter_path(name_or_addr)
		if not path or self.adapter_from_path(path) == "any":
			return None
		return self._adapter_iface(path)

	def _adapter_iface(self, path):
		try:
			obj = self.bus.get_object("org.bluez", path)
			iface = dbus.Interface(obj, "org.bluez.Adapter")
		except exc, e:
			self.handle_err(e)
			iface = None

		return iface

	def adapter_properties(self, name_or_addr):
		iface = self.adapter_iface(name_or_addr)
		if not iface:
			return None
		return iface.GetProperties()

	def adapter_addr(self, name):
		props = self.adapter_properties(name)
		if not props:
			return None
		return props['Address'].upper()

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
		try:
			obj = self.bus.get_object("org.bluez", path)
			iface = dbus.Interface(obj, "org.bluez.Service")
		except exc, e:
			self.handle_err(e)
			iface = None
		return iface

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

	def get_records(self, device, uuid, cb_ok, cb_nok):
		def closure_ok(services):
			cb_ok(device, services)

		def closure_nok(*args):
			cb_ok(device, [])

		device = device.upper()
		for path, adapter, addr in self.devmap.items():
			if addr.upper() == device():
				break
		else:
			return False

		uuid = uuid128(uuid)
		try:
			devif = self._device_iface(path)
			
			devif.DiscoverServices(uuid,
				reply_handler=closure_ok,
				error_handler=closure_nok)
		except exc, e:
			self.handle_err(e)
			return False

		return True

	def search(self, to=60000):
		try:
			for path in self._adapters():
				adapter_iface = self._adapter_iface(path)
				adapter_iface.StartDiscovery()
			self.search_timeout = timeout_call(to, self.stop_search)
			print "Search begun"
		except exc, e:
			self.handle_err(e)

	def stop_search(self):
		if not self.alive():
			return False

		if self.search_timeout:
			timeout_cancel(self.search_timeout)
			self.search_timeout = None

		try:
			for path in self._adapters():
				adapter_iface = self._adapter_iface(path)
				adapter_iface.StopDiscovery()
		except exc, e:
			self.handle_err(e)

		print "Search stopped"
		return False

_BlueZ = None

def BlueZ():
	global _BlueZ
	if not _BlueZ:
		_BlueZ = BlauZ()
	return _BlueZ


def parse_srv_params(args, wildcard=True):
	if not BlueZ().alive():
		print "D-Bus connection with BlueZ could not be made"
		exit(1)

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
	if not BlueZ().alive():
		print "D-Bus connection with BlueZ could not be made"
		exit(1)

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
	assert(addr.upper() == b.adapter_addr(addr).upper())
	assert(addr.upper() == b.adapter_addr(name).upper())
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
	print "Default adapter:", b.adapter_addr('default')
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