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

from hdp import hdp_record
from mcap.mcap_instance import MCAPInstance
import glib
import sys
from hdp.dummy_ieee10404 import parse_message_str
from mcap.misc import parse_srv_params
import dbus.mainloop.glib

TEST_CSP = True

class MyInstance(MCAPInstance):
	def MCLConnected(self, mcl, err):
		print "MCL has connected", id(mcl)

	def MCLReconnected(self, mcl, err):
		print "MCL has reconnected", id(mcl)

	def MCLDisconnected(self, mcl):
		print "MCL has disconnected", id(mcl)

	def MDLRequested(self, mcl, mdl, mdepid, config):
		print "MDL requested MDEP", mdepid, "config", config
		return True # reliable

	def MDLConnected(self, mdl, err):
		print "MDL connected", id(mdl)
		if TEST_CSP:
			# Nonin oximeter only answers to CSP after MDL is up
			glib.timeout_add(0, self.get_caps, mdl.mcl)

	def MDLAborted(self, mcl, mdl):
		print "MDL aborted", id(mdl)

	def MDLClosed(self, mdl):
		print "MDL closed", id(mdl)

	def MDLDeleted(self, mdl):
		print "MDL deleted", id(mdl)

	def MDLInquire(self, mdepid, config):
		if not config:
			print "MDLInquire: resetting configuration"
			config = 0x01
		reliable = not (config == 0x02 and mdepid == 0x02)
		ok = True
		print "MDLInquire: answering", ok, reliable, config
		return ok, reliable, config

	def get_caps(self, mcl):
		print "\tAsking CSP capabilities"
		self.SyncCapabilities(mcl, 100) # request 100ppm, nonin 55ppm
		return False

	def SyncCapabilitiesResponse(self, mcl, err, btclockres, synclead,
					tmstampres, tmstampacc):
		print "CSP Caps resp %s btres %d lead %d tsres %d tsacc %d" % \
			(err and "Err" or "Ok", btclockres,
				synclead, tmstampres, tmstampacc)
		if not err:
			# Schedule set late otherwise nonin does not respond
			glib.timeout_add(7500, self.test_set_future_indication, mcl)
		
	def test_set_future_indication(self, mcl):
		mcl.test_response = 2 # Set
		mcl.test_err = False

		retries = 5
		btclock = None

		while not btclock and retries > 0:
			retries -= 1
			btclock = instance.SyncBtClock(mcl)

		if btclock is None:
			print "Could not read bt clock, not testing CSP"
			return False

		# resets timestamp in 1s
		print "My BT Clock is", btclock
		btclock = btclock[0] + 3200
		initial_tmstamp = 1000000

		mcl.test_indications = 0
		mcl.test_initial_ts = initial_tmstamp
		mcl.test_initial_btclk = btclock
		mcl.test_err_ma = None

		print "\tRequesting CSP Set"
		instance.SyncSet(mcl, True, btclock, initial_tmstamp)

		return False

	def SyncSetResponse(self, mcl, err, btclock, tmstamp, tmstampacc):
		print "CSP Set resp: %s btclk %d ts %d tsacc %d" % \
			(err and "Err" or "Ok", btclock,
				tmstamp, tmstampacc)
		if not err:
			self.calc_drift(mcl, btclock, tmstamp)

	def SyncInfoIndication(self, mcl, btclock, tmstamp, accuracy):
		print "CSP Indication btclk %d ts %d tsacc %d" % \
			(btclock, tmstamp, accuracy)
		self.calc_drift(mcl, btclock, tmstamp)

	def calc_drift(self, mcl, btclock, tmstamp):
		btdiff = mcl.sm.csp.btdiff(mcl.test_initial_btclk, btclock)
		btdiff *= 312.5
		tmdiff = tmstamp - mcl.test_initial_ts
		err = tmdiff - btdiff

		if mcl.test_err_ma is None:
			errma = mcl.test_err_ma = err
		else:
			last_ma = mcl.test_err_ma
			errma = mcl.test_err_ma = 0.05 * err + \
				0.95 * last_ma

		print "\terror %dus moving avg %dus " % (err, errma),

		if tmdiff > 10000000:
			drift = float(errma) / (float(tmdiff) / 1000000)
			print "drift %dus/h" % (drift * 3600)
		else:
			print

	def RecvDump(self, mcl, message):
		# print "Received command ", repr(message)
		return True

	def SendDump(self, mcl, message):
		# print "Sent command ", repr(message)
		return True

	def Recv(self, mdl, data):
		response = parse_message_str(data)
		instance.Send(mdl, response)
		return True

adapter = parse_srv_params(sys.argv)

instance = MyInstance(adapter, True)
# instance.SyncDisable()

health_record = {'features': [{	'mdep_id': 0x01,
				'role': 'sink',
                     		'data_type': 0x1004,
				'description': 'HDP sink'}],

       		'mcap_control_psm': instance.cpsm,
		'mcap_data_psm': instance.dpsm,
  		'name': 'HDPy Sink',
		'provider': 'HDPy',
      		'description': 'A Health Device Protocol Sink',

		'mcap_procedures': (	'reconnect_init',
					'reconnect_accept',
					'csp',
					'csp_master')}

xml_record = hdp_record.gen_xml(health_record)

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
manager = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.bluez.Manager')
if not adapter:
	path = manager.DefaultAdapter()
else:
	path = manager.FindAdapter(adapter)
service = dbus.Interface(bus.get_object('org.bluez', path), 'org.bluez.Service')
hdp_record_handle = service.AddRecord(xml_record)

print 'Service record with handle 0x%04x added' % (hdp_record_handle)

try:
	print "Waiting for connections on %s %d" % (adapter, instance.cpsm)
	loop = glib.MainLoop()
	loop.run()
finally:
	service.RemoveRecord(dbus.UInt32(hdp_record_handle))
	print 'Stopped instance, thanks'
