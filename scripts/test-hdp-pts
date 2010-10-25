#!/usr/bin/python
# -*- coding: utf-8 -*-

import dbus
import sys
from sys import stdin

end = False
app = None
device = None
channels = []

def setup():
    global bus
    global manager
    global hdp_manager
    bus = dbus.SystemBus()

    manager = dbus.Interface(bus.get_object("org.bluez", "/"),
                            "org.bluez.Manager")
    hdp_manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"),
                        "org.bluez.HealthManager")

def select_adapter():
    global adapter
    select = manager.DefaultAdapter()
    adapters = manager.ListAdapters()

    print "Select an adapter [%s]:" % (select)
    i = 1
    for ad in adapters:
        print "%d. %s" % (i, ad)
        i = i + 1

    set = None
    while set == None:
        try:
            cmd = sys.stdin.readline()
            if cmd == '\n':
                break
            pos = int(cmd) - 1
            if pos < 0:
                raise TypeError
            select = adapters[pos]
            set = True
        except (TypeError, IndexError, ValueError):
            print "Wrong selection, try again: "
        except KeyboardInterrupt:
            sys.exit()
    adapter = dbus.Interface(bus.get_object("org.bluez", select),
                            "org.bluez.Adapter")

def select_device():
    global manager
    global adapter
    global device
    devices = adapter.ListDevices()

    if len(devices) == 0:
        print "No devices available"
        sys.exit()

    print "Select a device [%s]:" % (devices[0])
    i = 1
    for dev in devices:
        print "%d. %s" % (i, dev)
        i = i + 1

    set = None
    select = devices[0]
    while set == None:
        try:
            cmd = sys.stdin.readline()
            if cmd == '\n':
                break
            pos = int(cmd) - 1
            if pos < 0:
                raise TypeError
            select = devices[pos]
            set = True
        except (TypeError, IndexError, ValueError):
            print "Wrong selection, try again: ",
        except KeyboardInterrupt:
            sys.exit()

    print "Connecting to %s" % (select)
    device = dbus.Interface(bus.get_object("org.bluez", select),
                    "org.bluez.HealthDevice")

def help():
    print 'Help'

def exit():
    global end
    end = True

def create_app(role):
    global app
    app = hdp_manager.CreateApplication({"DataType": dbus.types.UInt16(4103),
                    "Role": role})
    print '%s created' % (app)

def create_app_sink():
    create_app('sink')

def create_app_source():
    create_app('source')

def destroy_app():
    global app
    hdp_manager.DestroyApplication(app)
    app = None

def create_channel(type):
    global channels
    global app
    global device
    select_device()
    try:
        channel = device.CreateChannel(app, type)
        channels.append(channel)
    except dbus.exceptions.DBusException, e:
        print e

def destroy_channel(channel):
    global channels
    global device
    chan = device.DestroyChannel(channel)
    channels.remove(channel)

def list_channels():
    '''
    List the channels created in this session.
    '''
    global channels
    for ch in channels:
        print ch

def create_channel_any():
    create_channel("Any")

def create_channel_reliable():
    create_channel('Reliable')

def create_channel_streaming():
    create_channel('Streaming')

commands = {'help':help,
            'exit':exit,
            'create_app_sink':create_app_sink,
            'create_app_source':create_app_source,
            'destroy_app':destroy_app,
            'create_channel_any':create_channel_any,
            'create_channel_reliable':create_channel_reliable,
            'create_channel_streaming':create_channel_streaming,
#            'destroy_channel':destroy_channel,
#            'list_channels':list_channels,
            }


def start_shell():
    global commands
    global end
    print 'Available commands:'
    i = 1
    keys = commands.keys()
    keys.sort()
    for c in keys:
        print c

    while not end:
        print '$',
        cmd = sys.stdin.readline()
        try:
            cmd = cmd.split('\n')[0]
            cmd = cmd.split(' ')
            if len(cmd) > 1:
                commands[cmd[0]](cmd[1:])
            else:
                commands[cmd[0]]()
        except KeyError:
            print 'Unknown command'
        except TypeError:
            print 'Unknown parameters on function %s' % (cmd[0])


setup()
select_adapter()
start_shell()
print 'Bye'
