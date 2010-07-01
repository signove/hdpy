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

'''
Test server to be used with hdpy_bluez_test*.py scripts.
Uses the mcap test plugin dbus API.
'''

import sys
import dbus
import time
import gobject
import dbus.mainloop.glib

mcap_iface = "org.bluez.mcap"

stored_data = ''

def acumulate(data):
    global stored_data
    stored_data += data

def object_signal(*args, **kwargs):
    global stored_data
    print "Value", args
    print kwargs
    print '############################################'
#    try:
    print ">> %s" % str(kwargs['member'])
    print '>> Interface: %s' % str(kwargs['interface'])
    print '>> Path: %s' % str(kwargs['path'])
    if kwargs['member'] == 'Recv':
        print 'Recieved data: %s' % args[1]
        acumulate(args[1])
        if (stored_data == 'Hello mcap server'):
            stored_data = ''
            print 'Hello mcap client'
            obj = bus.get_object("org.bluez", kwargs['path'])
            adapter = dbus.Interface(obj, mcap_iface)
            adapter.Send(args[0], 'Hello mcap client')
#    except:
#        print 'Some error in signal handling'
#        print "Details was:"
#        print kwargs


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()

manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.bluez.Manager")

adapter = dbus.Interface(bus.get_object("org.bluez", manager.DefaultAdapter()),
                            mcap_iface)

bus.add_signal_receiver(object_signal, bus_name="org.bluez",
                member_keyword="member",
                path_keyword="path",
                interface_keyword="interface",
                dbus_interface=mcap_iface,
                byte_arrays=True)

handle = adapter.StartSession(0x1011, 0x1013)

try:
    mainloop = gobject.MainLoop()
    mainloop.run()
finally:
    adapter.StopSession(handle)
    print
    print "Stopped instance, thanks"
    print
