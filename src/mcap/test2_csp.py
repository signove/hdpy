#!/usr/bin/env python
# Run something like a test2_server in the other side

from mcap_instance import MCAPInstance
import time
import sys
import glib

loop = glib.MainLoop()

class MyInstance(MCAPInstance):
	def MCLConnected(self, mcl):
		print "MCL has connected"
		self.begin(mcl)

	def MCLDisconnected(self, mcl):
		print "MCL has disconnected"
		self.bye()

	def __init__(self, adapter, listener):
		MCAPInstance.__init__(self, adapter, listener)

	def bye(self):
		glib.MainLoop.quit(loop)

	def RecvDump(self, mcl, message):
		print "Received raw msg", repr(message)
		return True

	def SendDump(self, mcl, message):
		print "Sent", repr(message)
		return True

	### CSP-specifc part

	def begin(self, mcl):
		self.counter = 1
		instance.SyncCapabilities(mcl, 1000)

	def SyncCapabilitiesResponse(self, mcl, err, btclockres, synclead,
					tmstampres, tmstampacc):
		print "CSP Caps resp %s btres=%d lead=%d tsres=%d tsacc=%d" % \
			(err and "Err" or "Ok", btclockres,
				synclead, tmstampres, tmstampacc)
		if err:
			self.bye()
		btclock = instance.SyncBtClock(mcl)
		if btclock is None:
			self.bye()
		btclock = btclock[0] + 3200 * 5
		instance.SyncSet(mcl, True, btclock, 5000000)
	
	def SyncSetResponse(self, mcl, err, btclock, tmstamp, tmstampacc):
		print "CSP Set resp: %s btclk=%d ts=%d tsacc=%d" % \
			(err and "Err" or "Ok", btclock,
				tmstamp / 1000000.0, tmstampacc)
		if err:
			self.bye()

	def SyncInfoIndication(self, mcl, btclock, tmstamp, accuracy):
		print "CSP Indication btclk=%d ts=%d tsacc%d" % \
			(btclock, tmstamp / 1000000.0, accuracy)

try:
	remote_addr = (sys.argv[1], int(sys.argv[2]))
except:
	print "Usage: %s <remote addr> <control PSM>" % sys.argv[0]
	sys.exit(1)

instance = MyInstance("00:00:00:00:00:00", False)
print "Connecting..."
mcl = instance.CreateMCL(remote_addr, 0)
# FIXME test CSP command here
# FIXME send command while not connected? protection

loop.run()

# FIXME assert request in flight
# FIXME test two reqs in sequence
