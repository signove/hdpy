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
		# print "Received raw msg", repr(message)
		return True

	def SendDump(self, mcl, message):
		# print "Sent", repr(message)
		return True

	### CSP-specifc part

	def begin(self, mcl):
		mcl._tc = 1
		# requests 10ppm precision
		instance.SyncCapabilities(mcl, 10)

	def SyncCapabilitiesResponse(self, mcl, err, btclockres, synclead,
					tmstampres, tmstampacc):
		print "CSP Caps resp %s btres %d lead %d tsres %d tsacc %d" % \
			(err and "Err" or "Ok", btclockres,
				synclead, tmstampres, tmstampacc)
		if err:
			self.bye()

		btclock = instance.SyncBtClock(mcl)
		if btclock is None:
			self.bye()

		# resets timestamp in 1s
		btclock = btclock[0] + 3200
		# begins with a timestamp of 5 full seconds
		initial_tmstamp = 5000000

		mcl._it = initial_tmstamp
		mcl._ib = btclock
		mcl._iema = None

		instance.SyncSet(mcl, True, btclock, initial_tmstamp)
	
	def SyncSetResponse(self, mcl, err, btclock, tmstamp, tmstampacc):
		print "CSP Set resp: %s btclk %d ts %d tsacc %d" % \
			(err and "Err" or "Ok", btclock,
				tmstamp, tmstampacc)
		if err:
			self.bye()

	def SyncInfoIndication(self, mcl, btclock, tmstamp, accuracy):
		print "CSP Indication btclk %d ts %d tsacc %d" % \
			(btclock, tmstamp, accuracy)
		self.calc_drift(mcl, btclock, tmstamp)

	def calc_drift(self, mcl, btclock, tmstamp):
		btdiff = mcl.sm.csp.btdiff(mcl._ib, btclock)
		btdiff *= 312.5
		tmdiff = tmstamp - mcl._it
		err = tmdiff - btdiff

		if mcl._iema is None:
			errma = mcl._iema = err
		else:
			last_ma = mcl._iema
			errma = mcl._iema = 0.05 * err + 0.95 * mcl._iema

		drift = float(errma) / (float(tmdiff) / 1000000)
		
		print "\terror %dus moving avg %dus drift %dus/h" % \
			(err, errma, drift * 3600)

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
# FIXME stop indication test
