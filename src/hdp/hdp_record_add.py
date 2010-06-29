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

import hdp_record
import sys
import time
import dbus

feature1 = {'mdep_id': 0x01, 'role': 'sink',
		'data_type': 0x1004, 'description': "Oximeter sink"}
# feature2 = {'mdep_id': 0x01, 'role': 'source', 'data_type': 0x4005}
# feature3 = {'mdep_id': 0x02, 'role': 'sink', 'data_type': 0x4006}
# feature4 = {'mdep_id': 0x04, 'role': 'sink', 'data_type': 0x4007}
# features = [feature1, feature2, feature3, feature4]
features = [feature1]
hdp = {'features': features}
hdp['mcap_control_psm'] = 0x1001
hdp['mcap_data_psm'] = 0x1003
hdp['name'] = "Fake oximeter"
hdp['description'] = "A fake HDP record"
hdp['provider'] = "Epx Inc."
hdp['mcap_procedures'] = ('csp', 'csp_master', 'reconnect_init', \
				'reconnect_accept')
xml = hdp_record.gen_xml(hdp)

bus = dbus.SystemBus()
manager = dbus.Interface(bus.get_object("org.bluez", "/"),
						"org.bluez.Manager")

if len(sys.argv) > 1:
	path = manager.FindAdapter(sys.argv[1])
else:
	path = manager.DefaultAdapter()

service = dbus.Interface(bus.get_object("org.bluez", path),
						"org.bluez.Service")

handle = service.AddRecord(xml)
# handle2 = service.AddRecord(open("pnpinfo.xml").read())
handle2 = None

print "Service record with handle 0x%04x added" % (handle)
if handle2:
	print "Service record with handle 0x%04x added" % (handle2)

print "Press CTRL-C to remove service record"

try:
	time.sleep(1000)
	print "Terminating session"
except:
	pass

service.RemoveRecord(dbus.UInt32(handle))
if handle2:
	service.RemoveRecord(dbus.UInt32(handle2))

# Hints for testing w/ Nonin 9650 oximeter:

# Listen CSM channel with l2test -P 4097 -X ertm -O 48 -r

# Nonin only searches PC SDP records right after cells disconnected (!),
# if it can't connect to CSM at first time, it seems not to try again,
# and cells must be removed for it to happen. (Thanks to Libresoft guys
# about this issue.)

# The Device Identification (PNPINFO) record is mandatory accordingly
# to HDP spec, but seems not to make a difference.
