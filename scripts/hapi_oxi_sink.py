#!/usr/bin/env python

import sys
import glib
from hdp.dummy_ieee10404 import parse_message_str
from hdp.hdp import *

watch_bitmap = glib.IO_IN | glib.IO_ERR | glib.IO_HUP | glib.IO_NVAL

def data_received(sk, evt):
	data = None
	if evt & glib.IO_IN:
		data = sk.recv(1024)
		if data:
			response = parse_message_str(data)
			sk.send(response)

	return evt == glib.IO_IN and data


class MyAgent(HealthApplicationAgent, HealthEndPointAgent):
	def DataChannelCreated(self, channel, reconn):
		print "Channel %d MDLID %d up" % \
			(id(channel), channel.mdl.mdlid)
		fd = channel.Acquire()
		glib.io_add_watch(fd, watch_bitmap, data_received)

	def DataChannelRemoved(self, service, channel):
		print "Service %d channel %d removed" % \
			(id(service), id(channel))

	def ServiceDiscovered(self, service):
		print "Service %d discovered %s" % \
			(id(service), service.addr_control)

	def ServiceRemoved(self, service):
		print "Service %d removed" % id(service)


agent = MyAgent()

config = {"end_points":
		[
		{"agent": agent,
		 "role" : "sink",
		 "specs":
			[
			{"data_type": 0x1004,
			 "description": "Oximeter sink"}, 
			]
		},
		]
	}


manager = HealthManager()
app = manager.RegisterApplication(agent, config)

try:
	loop = glib.MainLoop()
	loop.run()
except KeyboardInterrupt:
	pass
finally:
	manager.UnregisterApplication(app)
	print
	print "Application stopped"
	print
