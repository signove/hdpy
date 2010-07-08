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
from hdp.dummy_ieee10404 import parse_message_str
import dbus.mainloop.glib

class MyInstance(MCAPInstance):
	def MCLConnected(self, mcl, err):
		print "MCL has connected", id(mcl)

	def MCLReconnected(self, mcl, err):
		print "MCL has reconnected", id(mcl)

	def MCLDisconnected(self, mcl):
		print "MCL has disconnected", id(mcl)

	def MDLRequested(self, mcl, mdl, mdepid, config):
		print "MDL requested MDEP", mdepid, "config", config

	def MDLConnected(self, mdl, err):
		print "MDL connected", id(mdl)

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

instance = MyInstance("00:00:00:00:00:00", True)
# instance.csp_config(False)

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
					'reconnect_accept')}

xml_record = hdp_record.gen_xml(health_record)

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
manager = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.bluez.Manager')
path = manager.DefaultAdapter()
service = dbus.Interface(bus.get_object('org.bluez', path), 'org.bluez.Service')
hdp_record_handle = service.AddRecord(xml_record)

print 'Service record with handle 0x%04x added' % (hdp_record_handle)

try:
	print "Waiting for connections %d %d" % (instance.cpsm, instance.dpsm)
	loop = glib.MainLoop()
	loop.run()
finally:
	service.RemoveRecord(dbus.UInt32(hdp_record_handle))
	print 'Stopped instance, thanks'
