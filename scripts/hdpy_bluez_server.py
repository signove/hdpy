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

import gobject
import dbus.mainloop.glib

class TestServer(object):
    '''
    Test server to be used with hdpy_bluez_test*.py scripts.
    '''

    def __init__(self):
        self.mcap_iface = "org.bluez.mcap"
        self.stored_data = ''
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()

    def __acumulate(self, data):
        '''
        Accumulate received data.
        '''
        self.stored_data += data

    def __object_signal(self, *args, **kwargs):
        '''
        Handler of dbus signals.
        '''
        print "Value", args
        print kwargs
        print '############################################'
        print ">> %s" % str(kwargs['member'])
        print '>> Interface: %s' % str(kwargs['interface'])
        print '>> Path: %s' % str(kwargs['path'])
        if kwargs['member'] == 'Recv':
            print 'Recieved data: %s' % args[1]
            self.__acumulate(args[1])
            if (self.stored_data == 'Hello mcap server'):
                self.stored_data = ''
                print 'Hello mcap client'
                obj = self.bus.get_object("org.bluez", kwargs['path'])
                adapter = dbus.Interface(obj, self.mcap_iface)
                adapter.Send(args[0], 'Hello mcap client')

    def start(self):
        '''
        Starts the server.
        '''
        root_obj = self.bus.get_object("org.bluez", "/")
        man = dbus.Interface(root_obj, "org.bluez.Manager")
        adapter_obj = self.bus.get_object("org.bluez", man.DefaultAdapter())
        adapter = dbus.Interface(adapter_obj, self.mcap_iface)
        self.bus.add_signal_receiver(self.__object_signal,
                                     bus_name="org.bluez",
                                     member_keyword="member",
                                     path_keyword="path",
                                     interface_keyword="interface",
                                     dbus_interface=self.mcap_iface,
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

if __name__ == '__main__':
    TestServer().start()
