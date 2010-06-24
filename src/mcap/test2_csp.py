#!/usr/bin/env python
# Run something like a test2_server in the other side

from mcap_instance import MCAPInstance
import mcap
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
		mcl.test_step = 0
		self.test(mcl, None, None)

	def test(self, mcl, response, err):
		if response is not None and response != mcl.test_response:
			print "Test %d expected %d came %d" % \
				(mcl.test_step, mcl.test_response, response)
			sys.exit(1)

		if err is not None and err != mcl.test_err:
			print "Test %d expected err %s came %s" % \
				(mcl.test_step, mcl.test_err, err)
			sys.exit(1)

		mcl.test_step += 1
		print "Round %d" % mcl.test_step

		if mcl.test_step == 1:
			self.test_preposterous(mcl)

		elif mcl.test_step == 2:
			# requests invalid 0ppm precision
			self.test_req_cap(mcl, 0, True)
		
		elif mcl.test_step == 3:
			# requests too accurate 2ppm precision
			self.test_req_cap(mcl, 2, True)

		elif mcl.test_step == 4:
			# requests 20ppm precision
			self.test_req_cap(mcl, 20, False)

		elif mcl.test_step == 5:
			self.test_set_future_indication(mcl)

		elif mcl.test_step == 6:
			mcl.test_response = 3 # Indications
			pass

		elif mcl.test_step == 7:
			self.test_stop_indications(mcl)

		elif mcl.test_step in range(8, 28):
			self.test_invalid_set(mcl, mcl.test_step - 8)

		elif mcl.test_step == 28:
			self.test_stop_indications(mcl)

		else:
			print "All tests ok"
			glib.timeout_add(5000, self.bye)


	def test_invalid_set(self, mcl, seq):
		mcl.test_response = 2 # Set
		mcl.test_err = True

		btclock = instance.SyncBtClock(mcl)
		if btclock is None:
			self.bye()
			return

		# resets timestamp in 1s
		btclock = btclock[0] + 1600
		# begins with a timestamp of 5 full seconds
		initial_tmstamp = 5000000

		mcl.test_indications = -100000
		mcl.test_initial_ts = initial_tmstamp
		mcl.test_initial_btclk = btclock
		mcl.test_err_ma = None

		if seq % 2:
			update = True
		else:
			update = False

		# Until here we have perfectly valid parameters
		# Now we inject errors

		seq //= 2

		if seq % 2:
			# "don't set" (DS) timestamp
			initial_tmstamp = 0xffffffffffffffff

		seq //= 2

		if seq == 0:
			# btclock in past tense
			btclock -= 3200
		elif seq == 1:
			# btclock too into future
			btclock += 3200 * 63
		elif seq == 2:
			# invalid btclock
			btclock = 0xfffffff + 5
		elif seq == 3:
			# immediate btclock (makes req VALID)
			btclock = 0xffffffff
			mcl.test_err = False
		elif seq == 4:
			# leave btclock as it is (makes req VALID)
			mcl.test_err = False
			pass

		instance.SyncSet(mcl, update, btclock, initial_tmstamp)
		


	def test_req_cap(self, mcl, ppm, err):
		print "Requesting capabilities, ppm %d" % ppm

		mcl.test_response = 1 # Req
		mcl.test_err = err
		instance.SyncCapabilities(mcl, ppm)

		try:
			instance.SyncCapabilities(mcl, 20)
			print "Error: should not have accepted two requests"
			sys.exit(1)
		except mcap.InvalidOperation:
			pass


	def test_set_future_indication(self, mcl):
		mcl.test_response = 2 # Set
		mcl.test_err = False

		btclock = instance.SyncBtClock(mcl)
		if btclock is None:
			self.bye()
			return

		# resets timestamp in 1s
		btclock = btclock[0] + 3200
		# begins with a timestamp of 5 full seconds
		initial_tmstamp = 5000000

		mcl.test_indications = 0
		mcl.test_initial_ts = initial_tmstamp
		mcl.test_initial_btclk = btclock
		mcl.test_err_ma = None

		instance.SyncSet(mcl, True, btclock, initial_tmstamp)
	

	def test_stop_indications(self, mcl):
		mcl.test_response = 2 # Set
		mcl.test_err = False

		instance.SyncSet(mcl, False, None, None)


	def test_preposterous(self, mcl):
		mcl.test_err = True
		mcl.test_response = 2 # Set
		try:
			instance.SyncSet(mcl, True, None, 0x123)
			print "Preposterous CSP sync set must fail locally"
			sys.exit(1)
		except mcap.InvalidOperation:
			pass

		# cheat to make it go to server (and fail there)
		mcl.sm.csp.local_got_caps = True
		instance.SyncSet(mcl, True, None, 0x123)


	def SyncCapabilitiesResponse(self, mcl, err, btclockres, synclead,
					tmstampres, tmstampacc):
		print "CSP Caps resp %s btres %d lead %d tsres %d tsacc %d" % \
			(err and "Err" or "Ok", btclockres,
				synclead, tmstampres, tmstampacc)

		self.test(mcl, 1, err)
	
		
	def SyncSetResponse(self, mcl, err, btclock, tmstamp, tmstampacc):
		print "CSP Set resp: %s btclk %d ts %d tsacc %d" % \
			(err and "Err" or "Ok", btclock,
				tmstamp, tmstampacc)
		if not err:
			self.calc_drift(mcl, btclock, tmstamp)

		self.test(mcl, 2, err)


	def SyncInfoIndication(self, mcl, btclock, tmstamp, accuracy):
		print "CSP Indication btclk %d ts %d tsacc %d" % \
			(btclock, tmstamp, accuracy)
		self.calc_drift(mcl, btclock, tmstamp)

		mcl.test_indications += 1
		if mcl.test_indications > 5:
			self.test(mcl, 3, False)


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

try:
	remote_addr = (sys.argv[1], int(sys.argv[2]))
except:
	print "Usage: %s <remote addr> <control PSM>" % sys.argv[0]
	sys.exit(1)

instance = MyInstance("00:00:00:00:00:00", False)
print "Connecting..."
mcl = instance.CreateMCL(remote_addr, 0)

try:
	instance.SyncCapabilities(mcl, 100)
	print "Error: accepted command before connected"
	sys.exit(1)
except mcap.InvalidOperation:
	pass

loop.run()
