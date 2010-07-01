#!/usr/bin/python
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
import gobject
import dbus.mainloop.glib
from dummy_ieee10415 import parse_message

mcap_iface = 'org.bluez.mcap'
mcap_control_psm = 0x1001
mcap_data_psm = 0x1003

def object_signal(*args, **kwargs):
	print 'Value', args
	print 'Details', kwargs
	if 'member' in kwargs and kwargs['member'] == 'Recv':
		mdl, data = args
		response = parse_message(data)
		adapter.Send(mdl, response)

health_record = {'features': [{'mdep_id': 0x01, 'role': 'sink',
                     'data_type': 0x100f, 'description': 'HDP sink'}],
       'mcap_control_psm': mcap_control_psm, 'mcap_data_psm': mcap_data_psm,
       'name': 'Bluez HDP Sink', 'provider': 'Bluez',
       'description': 'A Health Device Protocol Sink',
       'mcap_procedures':('reconnect_init', 'reconnect_accept')}

xml_record = hdp_record.gen_xml(health_record)

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()

manager = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.bluez.Manager')

adapter = dbus.Interface(bus.get_object('org.bluez', manager.DefaultAdapter()),
							mcap_iface)

path = manager.DefaultAdapter()

service = dbus.Interface(bus.get_object('org.bluez', path), 'org.bluez.Service')

hdp_record_handle = service.AddRecord(xml_record)

print 'Service record with handle 0x%04x added' % (hdp_record_handle)

bus.add_signal_receiver(object_signal, bus_name='org.bluez',
				member_keyword='member',
				path_keyword='path',
				interface_keyword='interface',
				dbus_interface=mcap_iface)

mcap_handle = adapter.StartSession(mcap_control_psm, mcap_data_psm)
print 'Mcap handle: ', mcap_handle

try:
	print 'Press CTRL-C to stop'
	mainloop = gobject.MainLoop()
	mainloop.run()
finally:
	service.RemoveRecord(dbus.UInt32(hdp_record_handle))
	adapter.StopSession(mcap_handle)
	print 'Stopped instance, thanks'

