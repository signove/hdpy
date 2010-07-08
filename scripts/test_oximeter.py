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

from hdp import hdp_record
import gobject
import dbus.mainloop.glib
from hdp.dummy_ieee10404 import parse_message
import glib

mcap_iface = 'org.bluez.mcap'
mcap_control_psm = 0x1001
mcap_data_psm = 0x1003

TEST_CSP = False
mcl = 0


def object_signal(*args, **kwargs):
	if 'member' not in kwargs:
		return
	print kwargs['member']
	# print 'Value', args
	# print 'Details', kwargs

	if kwargs['member'] == 'Recv':
		mdl, data = args
		response = parse_message(data)
		adapter.Send(mdl, response)

	if kwargs['member'] == 'SyncInfoIndication':
		SyncInfoIndication(*args)

	if kwargs['member'] == 'MDLConnected':
		if TEST_CSP:
			# Nonin oximeter only answers to CSP after MDL is up
			global mcl
			mcl, mdl = args
			print "\tAsking CSP capabilities"
			# request 100ppm, nonin 55ppm
			print adapter.SyncCapabilities(mcl, 100,
				reply_handler=SyncCapabilitiesResponse,
				error_handler=ErrorResponse)


def ErrorResponse(*args):
	print "CSP response was error"


def SyncCapabilitiesResponse(err, btclockres, synclead, tmstampres, tmstampacc):
	print "CSP Caps resp %s btres %d lead %d tsres %d tsacc %d" % \
			(err and "Err" or "Ok", btclockres,
			synclead, tmstampres, tmstampacc)
	if not err:
		# Schedule set late otherwise nonin does not respond
		glib.timeout_add(7500, test_set_future_indication)
	

def test_set_future_indication():
	global test_initial_ts, test_initial_btclk, test_err_ma

	retries = 5
	btclock = None

	while not btclock and retries > 0:
		retries -= 1
		btclock = adapter.SyncBtClock(mcl)

	if btclock is None:
		print "Could not read bt clock, not testing CSP"
		return False

	# resets timestamp in 1s
	print "My BT Clock is", btclock
	btclock = btclock + 3200
	initial_tmstamp = 1000000

	test_initial_ts = initial_tmstamp
	test_initial_btclk = btclock
	test_err_ma = None

	print "\tRequesting CSP Set"
	adapter.SyncSet(mcl, 1, btclock, initial_tmstamp,
		reply_handler=SyncSetResponse,
		error_handler=ErrorResponse)

	return False


def SyncSetResponse(err, btclock, tmstamp, tmstampacc):
	print "CSP Set resp: %s btclk %d ts %d tsacc %d" % \
		(err and "Err" or "Ok", btclock,
			tmstamp, tmstampacc)
	if not err:
		calc_drift(btclock, tmstamp)


def SyncInfoIndication(mcl, btclock, tmstamp, accuracy):
	print "CSP Indication btclk %d ts %d tsacc %d" % \
		(btclock, tmstamp, accuracy)
	calc_drift(btclock, tmstamp)


def calc_drift(btclock, tmstamp):
	global test_err_ma
	btdiff = btclock - test_initial_btclk
	btdiff *= 312.5
	tmdiff = tmstamp - test_initial_ts
	err = tmdiff - btdiff

	if test_err_ma is None:
		errma = test_err_ma = err
	else:
		last_ma = test_err_ma
		errma = test_err_ma = 0.05 * err + \
			0.95 * last_ma

	print "\terror %dus moving avg %dus " % (err, errma),

	if tmdiff > 10000000:
		drift = float(errma) / (float(tmdiff) / 1000000)
		print "drift %dus/h" % (drift * 3600)
	else:
		print


health_record = {'features': [{'mdep_id': 0x01, 'role': 'sink',
                     'data_type': 0x1004, 'description': 'HDP sink'}],
       'mcap_control_psm': mcap_control_psm, 'mcap_data_psm': mcap_data_psm,
       'name': 'Bluez HDP Sink', 'provider': 'Bluez',
       'description': 'A Health Device Protocol Sink',
       'mcap_procedures':('reconnect_init', 'reconnect_accept', 'csp_master', 'csp')}

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

