#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Signove Tecnologia
# Parts based on another test script written by OpenHealth

import sys
import gobject
import dbus.mainloop.glib
import glib
import string
from test_suite import TestSuite, mcap_suites
import subprocess
import fcntl
import os

mcap_iface = "org.bluez.mcap"
# bdaddr = "00:80:98:E7:36:9f"
bdaddr = "00:80:98:E7:36:85"
cpsm = 0x1001
dpsm = 0x1003
mdepid = 1
conf = 0x00
hci_interface = None

print "Bdaddr", bdaddr
session = None
mcl = None
csp_caps = None
last_mdl = None

mcap_tests = TestSuite(mcap_suites)

def object_signal(*args, **kwargs):
    global mcl
    global last_mdl
    if 'member' not in kwargs:
        return
    sig_name = kwargs['member']
    if sig_name == "Recv":
        mdl, data = args
        print "Received data in mdl", mdl
        print "Data:", data
    elif sig_name == "MCLConnected":
        tmp_mcl, _ = args
        if mcl != None:
            print "Mcl is already connected"
            return
        print "New mcl"
        mcl = tmp_mcl
    elif sig_name == "MDLConnected":
        tmp_mcl, mdl = args
        if mcl != tmp_mcl:
            return
        last_mdl = mdl
        print "New mdl connected", mdl
    elif sig_name == "MDLReconnected":
        mdl = args[0]
        last_mdl = mdl
        print "New mdl reconnected", mdl
    elif sig_name == "MCLDisconnected":
        tmp_mcl = args[0]
        if mcl != tmp_mcl:
            return
        print "mcl disconnected"
    elif sig_name == "MCLReconnected":
        tmp_mcl = args[0]
        if mcl != tmp_mcl:
            return
        print "mcl reconnected"
    elif sig_name == "MDLDeleted":
        mdl = args[0]
        last_mdl = None
        print "mdl deleted", mdl
    elif sig_name == "MDLAborted":
        tmp_mcl, mdl = args
        if mcl != tmp_mcl:
            return
        print "mdl aborted", mdl

def adapter_signal(value, path, interface, member):
    hci = str(value)
    if hci.split("/")[-1] == ad.split("/")[-1]:
        print "Adapter went out, quitting"
        mainloop.quit()

def con_mcl(cmd):
    global mcl
    if session == None:
        print "Session not connected"
        return
    print "connect_mcl"
    try:
        mcl = mcap.CreateMCL(session, bdaddr, cpsm)
    except Exception, e:
        print e

def close_mcl(cmd):
    global mcl
    if mcl == None:
        print "mcl is not connected"
        return
    print "close_mcl"
    try:
        mcap.CloseMCL(mcl)
    except Exception, e:
        print e

def delete_mcl(cmd):
    global mcl
    if mcl == None:
        print "mcl is not connected"
        return
    print "delete_mcl"
    try:
        mcap.DeleteMCL(mcl)
        mcl = None
    except Exception, e:
        print e

def send_data(cmd):
    global last_mdl
    if last_mdl:
        data = "test"
        try:
            mcap.Send(last_mdl, data)
        except Exception, e:
            print "Error", e

def away(cmd):
    print "#################################################"
    print "Go away                                          "
    print "#################################################"

def con_mdl(cmd):
    global last_mdl
    print "Connect mdl"
    try:
        mdl = mcap.CreateMDL(mcl, mdepid, conf)
        mcap.ConnectMDL(mdl, dpsm)
        last_mdl = mdl
        print "connected mdl", mdl
    except Exception, e:
        print e

def close_mdl(cmd):
    global last_mdl
    print "Closing data channel", last_mdl
    if last_mdl:
        try:
            mcap.CloseMDL(last_mdl)
        except Exception, e:
            print "Error", e

def recon_mdl(cmd):
    global last_mdl
    print "Reconnecting mdl", last_mdl
    if last_mdl:
        try:
            mcap.ReconnectMDL(last_mdl)
            mcap.ConnectMDL(last_mdl, dpsm)
            print "reconnected mdl", last_mdl
        except Exception, e:
            print e

def del_mdl(cmd):
    global last_mdl
    print "Deleting mdl", last_mdl
    if last_mdl:
        try:
            mcap.DeleteMDL(last_mdl)
            print "deleted mdl", last_mdl
        except Exception, e:
            print e

def del_all(cmd):
    global mcl
    global last_mdl
    if mcl == None:
        print "Mcl is not connected"
        return
    print "Deleting all mdls"
    try:
        last_mdl = None
        mcap.DeleteAll(mcl)
        pass
    except Exception, e:
        print e

def abort_mdl(cmd):
    global last_mdl
    print "Aborting mdl", last_mdl
    try:
        mcap.AbortMDL(last_mdl)
        print "aborted mdl", last_mdl
    except Exception, e:
        print e

def neg_mdl(cmd):
    global last_mdl
    print "Negotiating mdl"
    try:
        mdl = mcap.CreateMDL(mcl, mdepid, conf)
        last_mdl = mdl
        print "negotitated mdl", mdl
    except Exception, e:
        print e

def csp_cap(cmd):
    global csp_caps
    print "Requesting CSP capabilities"
    try:
        ppm = 50
        csp_caps = mcap.SyncCapabilities(mcl, ppm)
        print "Capabilities:", csp_caps
    except Exception, e:
        print e

def csp_set(cmd):
    print "Setting CSP timestamp"
    try:
        send_indication = 0
        retries = 5
        btclock = 0xffffffff
        while retries > 0 and btclock == 0xffffffff:
            print "Reading BT clock"
            btclock = mcap.SyncBtClock(mcl)
            retries -= 1
        print "\tBT clock is 0x%x" % btclock
        btclock += 3200 * 10 # PTS wants it fairly into the future
        timestamp = 0x1122334455667788
        print "\tScheduled BT clock will be 0x%x" % btclock
        print mcap.SyncSet(mcl, send_indication, btclock, timestamp)
    except Exception, e:
        print e

def csp_seti(cmd):
    print "Setting CSP timestamp immediately"
    try:
        send_indication = 0
        btclock = 0xffffffff
        print "\tBT clock is 0x%x (immediate)" % btclock
        timestamp = 0x1122334455667788
        print mcap.SyncSet(mcl, send_indication, btclock, timestamp)
    except Exception, e:
        print e

def csp_set_ind(cmd):
    print "Setting CSP timestamp"
    try:
        send_indication = 1
        retries = 5
        btclock = 0xffffffff
        while retries > 0 and btclock == 0xffffffff:
            print "Reading BT clock"
            btclock = mcap.SyncBtClock(mcl)
            retries -= 1
        print "\tBT clock is 0x%x" % btclock
        btclock += 3200 * 10 # PTS wants it fairly into the future
        timestamp = 0x1122334455667788
        print mcap.SyncSet(mcl, send_indication, btclock, timestamp)
    except Exception, e:
        print e

def enable_csp(cmd):
    print "Enabling CSP"
    try:
        print mcap.SyncEnable(session) and "Enabled" or "Not enabled"
    except Exception, e:
        print e

def disable_csp(cmd):
    print "Disabling CSP"
    try:
        print mcap.SyncDisable(session) and "Disabled" or "Not disabled"
    except Exception, e:
        print e

def bt_up(cmd):
    global hci_interface
    print "Enabling Bluetooth"
    print "Status: %d" % (subprocess.call(["sudo", "hciconfig", hci_interface, "up"]))

def bt_down(cmd):
    global hci_interface
    print "Disabling Bluetooth"
    print "Status: %d" % (subprocess.call(["sudo", "hciconfig", hci_interface, "down"]))


commands = {"con_mcl": {"help":"con_mcl", "npar": 0, "fun": con_mcl},
    "close_mcl": {"help":"close_mcl", "npar": 0, "fun": close_mcl},
    "delete_mcl": {"help":"delete_mcl", "npar": 0, "fun": delete_mcl},
    "send_data": {"help":"send_data mdl", "npar": 0, "fun": send_data},
    "con_dc": {"help":"con_dc", "npar": 0, "fun": con_mdl},
    "close_dc": {"help":"close_dc mdl", "npar": 0, "fun": close_mdl},
    "recon_dc": {"help":"recon_dc mdl", "npar": 0, "fun": recon_mdl},
    "del_dc": {"help":"del_dc mdl", "npar": 0, "fun": del_mdl},
    "away": {"help":"away", "npar": 0, "fun": away},
    "del_all": {"help":"del_all", "npar": 0, "fun": del_all},
    "abort_dc": {"help":"abort_dc mdl", "npar": 0, "fun": abort_mdl},
    "neg_dc": {"help":"neg_dc", "npar": 0, "fun": neg_mdl},
    "enable_csp": {"help":"enable_csp", "npar": 0, "fun": enable_csp},
    "disable_csp": {"help":"disable_csp", "npar": 0, "fun": disable_csp},
    "csp_cap": {"help":"csp_cap", "npar": 0, "fun": csp_cap},
    "csp_set": {"help":"csp_set", "npar": 0, "fun": csp_set},
    "csp_seti": {"help":"csp_seti", "npar": 0, "fun": csp_seti},
    "csp_set_ind": {"help":"csp_set_ind", "npar": 0, "fun": csp_set_ind},
    "bt_down": {"help":"bt_down", "npar": 0, "fun": bt_down},
    "bt_up": {"help":"bt_up", "npar": 0, "fun": bt_up},
    "exit": {"help":"exit", "npar": 0, "fun": exit},
    }

def check_cmd(cmd):
    try:
        if cmd[0].lower() not in commands.keys():
            return False
        c = commands[cmd[0].lower()]
        if (c["npar"] + 1) == len(cmd):
            return True
        print "help: %s" % c["help"]
    except:
        pass
    return False

def flush(fd):
    try:
        while fd.read(512):
            pass
    except IOError:
        pass

def stdin_cb(fd, condition):
    global mcap_tests

    keys = fd.readline().strip() # Read input line

    cmd = mcap_tests.get_current_command()

    if keys:
        if keys[0] == '\x1b':
            print
            print "Skipping..."
	    print
            if not mcap_tests.next_command():
                print "####### END ########"
        else:
            if keys[0] == '/':
                # This vi habit....
                keys = keys[1:]
            mcap_tests.seek_command(keys)
    else:
        commands[cmd[0].lower()]["fun"](cmd)
        if not mcap_tests.next_command():
            print "####### END ########"

    mcap_tests.command_info()
    flush(fd);
    return True


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()

manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.bluez.Manager")

ad = manager.DefaultAdapter()
print "Binding to adapter", ad
hci_interface = ad.split("/")[-1]

mcap = dbus.Interface(bus.get_object("org.bluez", ad), mcap_iface)

bus.add_signal_receiver(object_signal, bus_name="org.bluez",
                member_keyword="member",
                path_keyword="path",
                interface_keyword="interface",
                dbus_interface=mcap_iface,
                byte_arrays=True)

bus.add_signal_receiver(adapter_signal, bus_name="org.bluez",
                signal_name="AdapterAdded",
                path_keyword="path",
                member_keyword="member",
                interface_keyword="interface")

bus.add_signal_receiver(adapter_signal, bus_name="org.bluez",
                signal_name="AdapterRemoved",
                path_keyword="path",
                member_keyword="member",
                interface_keyword="interface")

session = mcap.StartSession(cpsm, dpsm)

fd = sys.stdin.fileno()
fl = fcntl.fcntl(fd, fcntl.F_GETFL)
fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

try:
    print "Starting tests Session: ", session
    print 'Press Enter to send commands'
    mcap_tests.command_info()

    glib.io_add_watch(sys.stdin, glib.IO_IN, stdin_cb)

    mainloop = gobject.MainLoop()
    mainloop.run()
finally:
    try:
        mcap.StopSession(session)
        print
        print "Stopped instance, thanks"
        print
    except:
        pass

