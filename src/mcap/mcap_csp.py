#!/usr/bin/env ptyhon

import mcap_sock
from mcap_defs import *
import string
import time

class BluetoothClock:
	"""
	This class is intended to be used as a singleton by all
	MCAP instances, as a Bluetooth Clock source.
	"""

	def __init__(self, device_id):
		self.raw_socket = mcap_sock.hci_open_dev(device_id)
		self.clock_latency = self._determine_clock_latency()

	def _determine_clock_latency(self):
		"""
		Determine how much time it takes to read HCI clock
		"""
		# Exercise modules first
		mcap_sock.hci_read_clock(self.raw_socket, None)
		t = time.time()
		mcap_sock.hci_read_clock(self.raw_socket, None)
		t = time.time()
		mcap_sock.hci_read_clock(self.raw_socket, None)
		t = time.time()
		# then measure
		t1 = time.time()
		# FIXME detect preemption here
		mcap_sock.hci_read_clock(self.raw_socket, None)
		# FIXME detect preemption here
		t2 = time.time()
		return int((t2 - t1) * 1000000)

	def latency(self):
		return self.clock_latency
	
	def read(self, remote_addr=None):
		"""
		Reads Bluetooth clock.

		If remote addr is specified, reads piconet clock (the addr
		is a remote participant of the piconet). If not specified,
		reads native clock (which is the same as piconet clock if
		local BT is piconet master).

		Returns a tuple with BT clock and accuracy, or None if
		not successful.

		Accuracy may be zero (means theoretical infinit precision).
		Unit is Bluetooth "ticks" (312.5 us each), wraps 32 bits
		"""
		if remote_addr:
			remote_addr = remote_addr[0]
		return mcap_sock.hci_read_clock(self.raw_socket, remote_addr)


btclock_field     = btclock_max + 1
btclock_wrap      = btclock_max / 4
clocks = {}


def get_singleton_clock(addr):
	# TODO get the right device id accordingly to interface.
	# For now we get interface 0.
	device_id = 0
	try:
		clock = clocks[device_id]
	except KeyError:
		clock = clocks[device_id] = BluetoothClock(device_id)
	return clock


class CSPStateMachine(object):
	def __init__(self, mainsm, mcl):
		self.mainsm = mainsm
		self.parser = mainsm.parser
		self.mcl = mcl
		self.observer = mcl.observer
		self.reset_timestamp(0)
		self.request_in_flight = 0
		self.enabled = True
		self.indication_expected = False
		self.indication_alarm = None
		self.remote_got_caps = False
		self.local_got_caps = False
		self.clock = get_singleton_clock(self.mcl.remote_addr)

		# TODO allow setting timestamp accuracy from higher layer
		self.tmstampacc = 10 # ppm

		# gettimeofday() returns time in us
		self.tmstampres = 1 # us

		# TODO determine btclockres experimentally
		# (preliminary tests returned 1)
		self.btclockres = 1 # clock cycle

		self.latency = self.clock.latency() # us

	def reset_timestamp(self, new_timestamp):
		self.base_time = time.time()
		self.base_timestamp = new_timestamp

	def get_timestamp(self):
		'''
		Get current relative timestamp
		'''
		return int(1000000 * (time.time() - self.base_time)) \
			+ self.base_timestamp

	def get_btclock(self):
		return self.clock.read(self.mcl.remote_addr)

	@staticmethod 
	def bt2us(btclock):
		return int(312.5 * btclock)

	@staticmethod 
	def btdiff(btclock1, btclock2):
		diff = btclock2 - btclock1
		# test for probable wrap of either clock
		if diff > btclock_wrap:
			# btclock1 wrapped
			diff -= btclock_field
		elif diff < -btclock_wrap:
			# btclock2 wrapped
			diff += btclock_field
		return diff

	@staticmethod 
	def us2bt(tmstamp):
		return int(tmstamp / 312.5)

	def is_mine(self, opcode):
		return opcode >= MCAP_MD_SYNC_MIN and \
			opcode <= MCAP_MD_SYNC_MAX

	def send_response(self, message):
		self.mainsm.send_response(message)

	def send_request(self, message):
		if message.opcode != MCAP_MD_SYNC_INFO_IND \
			and self.request_in_flight:
			raise InvalidOperation('CSP: Still waiting for response')

		if message.opcode == MCAP_MD_SYNC_SET_REQ \
			and not self.local_got_caps:
			raise InvalidOperation('CSP: Cannot set before get caps')
			
		if message.opcode != MCAP_MD_SYNC_INFO_IND:
			self.request_in_flight = message.opcode
			self.last_request = request

		return self.mainsm.send_mcap_command(request)

	def receive_message(self, opcode, message):
		if opcode % 2:
			# request
			return self.process_request(opcode, message)

		# response
		expected = self.request_in_flight + 1
		if not expected or opcode != expected:
			# unexpected response: ignore
			return
		self.request_in_flight = 0
		self.process_response(opcode, message)

	def process_request(self, opcode, message):
		try:
			message = self.parser.parse(message)
		except InvalidMessage:
			return self.process_invalid_request(opcode, message)

		return self.handlers[opcode](self, message)

	def process_invalid_request(self, opcode, message):
		if opcode != MCAP_MD_SYNC_INFO_IND:
			print "Invalid CSP request (but valid opcode), rejecting"
			res = self.send_response(invalid_responses[opcode])
		else:
			print "Invalid CSP indication"
			res = None
		return res

	def process_response(self, opcode, message):
		try:
			message = self.parser.parse(message)

		except InvalidMessage:
			# TODO notify higher level about error (how?)
			print "Invalid CSP response, ignoring"
			return

		self.handlers[opcode](self, message)

	def capabilities_request(self, message):
		btclockres = 0
		synclead = 0
		tmstampres = 0
		tmstampacc = 0
		rspcode = MCAP_RSP_SUCCESS

		if not self.enabled:
			rspcode = MCAP_RSP_REQUEST_NOT_SUPPORTED
		elif message.reqaccuracy < self.tmstampacc:
			rspcode = MCAP_RSP_REQUEST_NOT_SUPPORTED
		else:
			self.remote_got_caps = True
			self.remote_reqaccuracy = self.tmstampacc

			btclockres = self.btclockres
			synclead = self.latency / 1000
			tmstampres = self.tmstampres
			tmstampacc = self.tmstampacc
		
		rsp = CSPCapabilitiesResponse(rspcode,
				btclockres, synclead,
				tmstampres, tmstampac)

		return self.send_response(rsp)

	def capabilities_response(self, message):
		if message.rspcode == MCAP_RSP_SUCCESS:
			self.local_got_caps = True

		schedule(self.observer.csp_capabilities(
				message.rspcode != MCAP_RSP_SUCCESS,
				message.btclockres, message.synclead,
				message.tmstampres, message.tmstampacc))

	def set_request(self, message):
		rspcode = MCAP_RSP_SUCCESS

		if message.btclock != btclock_immediate and \
			not self.valid_btclock(message.btclock):
			rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE

		elif message.update not in (0, 1):
			rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE

		elif message.update and not self.remote_got_caps:
			rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE

		# FIXME role switch after cap_req? invalid operation 

		bt_now = self.get_btclock()
		if not bt_now:
			rspcode = MCAP_RSP_UNSPECIFIED_ERROR
			bt_now = message.btclock - 1
		else:
			bt_now = tp[0]
		
		if message.btclock == btclock_immediate:
			to = 0
		else:
			if not self.remote_got_caps:
				rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE

			to = self.tdiff(bt_now, message.btclock)

			if to < 0:
				# can not update timestamp in the past :)
				rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE
			
			# convert to us
			to = self.bt2us(to)

			if to > (60*1000*1000 + 1):
				# more than 60 seconds in the future
				rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE
			elif to < self.latency:
				# would never make it in time
				rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE
			
			# convert to ms to satisfy scheduler
 			to = to / 1000 + 1

			ito = self.remote_reqaccuracy / self.tmstampacc # sec
			ito = int(ito * 1000000) # us

			if ito < (self.latency * 2) or ito < 100000:
				# unreasonable indication rhythm due to
				# low local precision or too high remote
				# precision requirement
				rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE

		if rspcode == MCAP_RSP_SUCCESS:
			if self.indication_alarm:
				timeout_cancel(self.indication_alarm)
				self.indication_alarm = None

			if message.timestamp == tmstamp_dontset:
				# fast-track response
				self.set_request_phase2(message.update,
							message.btclock,
							message.timestamp,
							ito)
			else:
				# send response only when tmstamp is set
				timeout_call(to, self.set_request_phase2,
					message.update, message.btclock,
					message.timestamp, ito)
			return True
		else:
			rsp = CSPSetResponse(rspcode, 0, 0, 0)

		return self.send_response(rsp)

	def set_request_phase2(self, update, sched_btclock, new_tmstamp, ito):
		reset = new_tmstamp != tmstamp_dontset
		btclock = self.get_btclock()

		if not btclock:
			# damn!
			rspcode = MCAP_RSP_UNSPECIFIED_ERROR
			rsp = CSPSetResponse(rspcode, 0, 0, 0)
			self.send_response(rsp)
			return False

		btclock = btclock[0]

		# compensate timestamp for lateness of this callback
		delay = self.bt2us(self.btdiff(sched_btclock, btclock))
		new_tmstamp += delay
	
		if reset:
			self.reset_timestamp(new_tmstamp)

		timestamp = self.get_timestamp()

		# this is different from timestamp accuracy;
		# it needs to take latency into account
		tmstampacc = self.latency + self.tmstampacc

		if update:
			self.indication_alarm = \
				timeout_call(ito, self.send_indication_cb)

		rspcode = MCAP_RSP_SUCCESS
		rsp = CSPSetResponse(rspcode, btclock, timestamp, tmstampacc)
		self.send_response(rsp)
		return False

	def set_response(self, message):
		if not self.valid_btclock(message.btclock):
			return

		self.indication_expected = self.last_request.update

		schedule(self.observer.csp_set(
				message.rspcode != MCAP_RSP_SUCCESS,
				message.btclock, message.timestamp,
				message.tmstampacc))
	
	def info_indication(self, message):
		if not self.indication_expected:
			return
		elif not self.valid_btclock(message.btclock):
			return

		schedule(self.observer.csp_indication(
					message.btclock,
					message.timestamp,
					message.accuracy))

	def send_indication_cb(self):
		btclock = self.get_btclock()
		# FIXME detect preemption here
		timestamp = self.get_timestamp()

		if not btclock:
			return False

		btclock = btclock[0]
		tmstampacc = self.latency
		rsp = CSPInfoIndication(btclock, timestamp, tmstampacc)
		self.send_request(rsp)
		return True

	handlers = {
		MCAP_MD_SYNC_CAP_REQ: capabilities_request,
		MCAP_MD_SYNC_CAP_RSP: capabilities_response,
		MCAP_MD_SYNC_SET_REQ: set_request,
		MCAP_MD_SYNC_SET_RSP: set_response,
		MCAP_MD_SYNC_INFO_IND: info_indication,
		}

	# When a CSP request is corrupted (e.g. invalid length)
	# but opcode is valid, response must be with the same
	# format as an "ok" response

	invalid_responses = {
		MCAP_MD_SYNC_CAP_REQ: CSPCapabilitiesResponse(
				MCAP_RSP_INVALID_PARAMETER_VALUE,
				0, 0, 0, 0),
		MCAP_MD_SYNC_SET_REQ: CSPSetResponse(
				MCAP_RSP_INVALID_PARAMETER_VALUE,
				0, 0, 0)
	}

	def valid_btclock(self, btclock):
		'''
		Tests whether btclock is a 28-bit value
		'''
		return btclock >= 0 and btclock <= btclock_max

def test(argv0, target=None, l2cap_psm=None, ertm=None):
	assert(CSPStateMachine.btdiff(0, 1) == 1)
	assert(CSPStateMachine.btdiff(1, 0) == -1)
	assert(CSPStateMachine.btdiff(1, 3) == 2)
	assert(CSPStateMachine.btdiff(3, 1) == -2)
	assert(CSPStateMachine.btdiff(0xfffffff, 1) == 2)
	assert(CSPStateMachine.btdiff(1, 0xfffffff) == -2)
	assert(CSPStateMachine.btdiff(0xffffff8, 1) == 9)
	assert(CSPStateMachine.btdiff(1, 0xffffffe) == -3)
	assert(CSPStateMachine.bt2us(1600) == 500000)
	assert(CSPStateMachine.bt2us(-1600) == -500000)
	assert(CSPStateMachine.us2bt(1000000) == 3200)
	assert(CSPStateMachine.us2bt(-1000000) == -3200)

	import time
	b = BluetoothClock(0)

	print "Read clock RTT in microseconds: %d" % b.latency()
	print

	print "Reading native clock"
	# Can't fail
	clock1, accuracy = b.read()
	time.sleep(0.1)
	clock2, accuracy = b.read()
	diff = clock2 - clock1
	print "Clocks: %d - %d = %d" % (clock1, clock2, diff)
	diff *= 312.5 / 1000000.0 # 312.5us per tick
	print "Diff in seconds (should be around 0.1): %f" % diff
	print "Accuracy: ", accuracy

	if not target:
		return

	# Creates an L2CAP connection just to make sure ACL is up
	s = mcap_sock.create_socket("")
	try:
		s.connect((target, l2cap_psm))
	except IOError:
		# It doesn't really matter if connection went up.
		pass

	print "Reading native clock"
	# Can fail
	clock1 = b.read(target)
	if not clock1:
		print "Could not read clock (remote addr down?)"
		return

	time.sleep(0.1)
	clock2 = b.read(target)
	if not clock2:
		print "Could not read clock (remote addr down?)"
		return

	diff = clock2[0] - clock1[0]
	print "Clocks: %d - %d = %d" % (clock1[0], clock2[0], diff)
	diff *= 312.5 / 1000000.0 # 312.5us per tick
	print "Diff in seconds (should be around 0.1): %f" % diff
	print "Accuracy: ", clock2[1]
	s.close()


if __name__ == '__main__':
	import sys
	test(*sys.argv)
