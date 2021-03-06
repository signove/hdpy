#!/usr/bin/env ptyhon
# -*- coding: utf-8

#######################################################################
# Copyright 2010 Signove Corporation - All rights reserved.
# Contact: Signove Corporation (contact@signove.com)
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330,
# Boston, MA 02111-1307  USA
#
# If you have questions regarding the use of this file, please contact
# Signove at contact@signove.com.
#######################################################################

CLOCK_ACCURACY_PPM = 10
CLOCK_RESOLUTION_US = 1

import mcap_sock
from mcap_defs import *
import string
import time
from mcap_loop import *
import math

class BluetoothClock:
	clock_latency = None

	def __init__(self, remote_addr):
		self.addr = remote_addr
		self.raw_socket, self.dev_id = mcap_sock.hci_open_dev(remote_addr)
		if BluetoothClock.clock_latency is None:
			BluetoothClock.clock_latency = self._determine_latency()

	def _determine_latency(self):
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

		# take a bunch of measures
		latencies = []
		latencies2 = []
		for x in range(0, 20):
			t1 = time.time()
			# FIXME handle temporary failure
			mcap_sock.hci_read_clock(self.raw_socket, None)
			t2 = time.time()
			latency = t2 - t1
			latencies.append(latency)
			latencies2.append(latency * latency)

		s = sum(latencies)
		n = len(latencies)
		avg = s / n
		stdev = math.sqrt((n * sum(latencies2) - s * s)) / n

		filtered = []
		for latency in latencies:
			# leap of faith here: we assume that latencies too
			# high are result of preemption between calls
			if latency < avg + 6 * stdev:
				filtered.append(latency)

		# Return average without freak samples
		avg = sum(filtered) / len(filtered)
		return int(avg * 1000000)

	def latency(self):
		return BluetoothClock.clock_latency

	def role(self):
		return mcap_sock.hci_role(self.raw_socket, self.dev_id)

	def read_native(self):
		# FIXME handle temporary failure
		return mcap_sock.hci_read_clock(self.raw_socket, None)
	
	def read(self, piconet):
		"""
		Reads Bluetooth clock.

		If piconet is True, reads piconet clock. If False, reads
		native clock (which is the same as piconet clock if
		local BT is piconet master).

		Returns a tuple with BT clock and accuracy, or None if
		not successful.

		Accuracy may be zero (means theoretical infinit precision).
		Unit is Bluetooth "ticks" (312.5 us each), wraps 32 bits
		"""
		addr = None
		if piconet:
			addr = self.addr
		# FIXME handle temporary failure
		return mcap_sock.hci_read_clock(self.raw_socket, addr)


btclock_field = btclock_max + 1
btclock_half  = btclock_field // 2


class CSPStateMachine(object):
	def __init__(self, mainsm, mcl):
		self.mainsm = mainsm
		self.parser = mainsm.parser
		self.mcl = mcl
		self.observer = mcl.observer
		self.reset_timestamp(time.time(), 0)
		self.request_in_flight = 0
		self.indication_expected = False
		self.indication_alarm = None
		self.remote_got_caps = False
		self.local_got_caps = False
		self._clock = None
		self._latency = None
		self._preemption_thresh = None
		self._synclead = None

		self.tmstampacc = CLOCK_ACCURACY_PPM
		self.tmstampres = CLOCK_RESOLUTION_US

	def clock(self):
		if not self._clock:
			self._clock = BluetoothClock(self.mcl.remote_addr[0])
		return self._clock

	def latency(self):
		if self._latency is None:
			self._latency = self.clock().latency()
		return self._latency

	def synclead_ms(self):
		if self._synclead is None:
			self._synclead = self.clock().latency() * 50 // 1000
		return self._synclead

	def preemption_thresh(self):
		# We assume that observed latencies bigger than
		# 4 x "normal" latency is sympthom of preemption
		if self._preemption_thresh is None:
			self._preemption_thresh = self.clock().latency() \
						* 4.0 / 1000000.0
		return self._preemption_thresh

	def reset_timestamp(self, now, new_timestamp):
		self.base_time = now
		self.base_timestamp = new_timestamp

	def get_timestamp(self):
		'''
		Get current relative timestamp
		'''
		return int(1000000 * (time.time() - self.base_time)) \
			+ self.base_timestamp

	def get_btclock(self):
		return self.clock().read(self.mcl.remote_addr)
	
	def get_btclock_native(self):
		return self.clock().read_native()

	@staticmethod 
	def bt2us(btclock):
		return int(312.5 * btclock)

	@staticmethod 
	def btdiff(btclock1, btclock2):
		return CSPStateMachine.btoffset(btclock1, btclock2)

	@staticmethod
	def btoffset(btclock1, btclock2):
		offset = btclock2 - btclock1
		if offset <= -btclock_half:
			offset += btclock_field
		elif offset > btclock_half:
			offset -= btclock_field
		return offset

	@staticmethod
	def btoffsetdiff(offset1, offset2):
		ofd = offset2 - offset1
		if ofd <= -btclock_half:
			ofd += btclock_field
		elif ofd > btclock_half:
			oft -= btclock_field
		return ofd

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
			self.last_request = message

		if message.opcode == MCAP_MD_SYNC_SET_REQ:
			self.indication_expected = True

		return self.mainsm.send_mcap_command(message)

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
			res = self.send_response(self.invalid_responses[opcode])
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

		clk = self.get_btclock()

		if not self.mcl.observer.csp_enabled:
			rspcode = MCAP_RSP_REQUEST_NOT_SUPPORTED
		elif message.reqaccuracy < self.tmstampacc:
			rspcode = MCAP_RSP_REQUEST_NOT_SUPPORTED
		elif not clk:
			rspcode = MCAP_RSP_RESOURCE_UNAVAILABLE
		else:
			self.remote_got_caps = True
			self.remote_reqaccuracy = message.reqaccuracy

			btclockres = clk[1]
			synclead = self.synclead_ms()
			tmstampres = self.tmstampres
			tmstampacc = self.tmstampacc
		
		rsp = CSPCapabilitiesResponse(rspcode,
				btclockres, synclead,
				tmstampres, tmstampacc)

		return self.send_response(rsp)

	def capabilities_response(self, message):
		if message.rspcode == MCAP_RSP_SUCCESS:
			self.local_got_caps = True

		schedule(self.observer.csp_capabilities,
				self.mcl,
				message.rspcode != MCAP_RSP_SUCCESS,
				message.btclockres, message.synclead,
				message.tmstampres, message.tmstampacc)

	def set_request(self, message):
		self.set_req_role = -2
		rspcode = MCAP_RSP_SUCCESS

		if not self.mcl.observer.csp_enabled:
			rspcode = MCAP_RSP_REQUEST_NOT_SUPPORTED

		elif message.btclock != btclock_immediate and \
			not self.valid_btclock(message.btclock):
			rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE

		elif message.update not in (0, 1):
			rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE

		elif message.update and not self.remote_got_caps:
			rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE

		else:
			bt_now = self.get_btclock()
			if not bt_now:
				rspcode = MCAP_RSP_UNSPECIFIED_ERROR
			else:
				bt_now = bt_now[0]
				self.set_req_role = self.clock().role()

		if message.btclock == btclock_immediate \
				or rspcode != MCAP_RSP_SUCCESS:
			to = 0
		else:
			if not self.remote_got_caps:
				rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE

			to = self.btdiff(bt_now, message.btclock)

			if to < 0:
				# can not update timestamp in the past :)
				rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE
			
			# convert to us
			to = self.bt2us(to)

			if to > (60*1000*1000 + 1):
				# more than 60 seconds in the future
				rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE

			elif to < self.latency():
				# would never make it in time
				rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE
			
		if rspcode == MCAP_RSP_SUCCESS and message.update:
			ito = int(1000000 \
				* self.remote_reqaccuracy \
				/ self.tmstampacc) # us

			if ito < (self.latency() * 2) or ito < 100000:
				# unreasonable indication rhythm due to
				# low local precision or too high remote
				# precision requirement
				rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE
			else:
				print "CSP: indication sent every %d us" \
					" (req %dppm, ours %dppm)" % \
					(ito, self.remote_reqaccuracy,
					self.tmstampacc)
		else:
			ito = "None"
			
		if rspcode == MCAP_RSP_SUCCESS:
			self.stop_indication_alarm()

			if message.timestamp == tmstamp_dontset:
				# fast-track response
				self.set_request_phase2(message.update,
							message.btclock,
							message.timestamp,
							ito)
			else:
				# send response only when tmstamp is set
				timeout_call(to // 1000 + self.synclead_ms(),
					self.set_request_phase2,
					message.update, message.btclock,
					message.timestamp, ito)

			if message.update:
				# First indication is immediate
				self.send_indication_cb(False)

			return True

		# Fail
		rsp = CSPSetResponse(rspcode, 0, 0, 0)
		return self.send_response(rsp)

	def set_request_phase2(self, update, sched_btclock, new_tmstamp, ito):
		latency = self.preemption_thresh() + 1
		retry = 5

		while latency > self.preemption_thresh() and retry:
			t1 = time.time()
			btclock = self.get_btclock()
			timestamp = self.get_timestamp()
			latency = time.time() - t1
			retry -= 1

		if not btclock:
			# damn!
			rspcode = MCAP_RSP_UNSPECIFIED_ERROR
			rsp = CSPSetResponse(rspcode, 0, 0, 0)
			self.send_response(rsp)
			return False

		btclock = btclock[0]

		if self.clock().role() != self.set_req_role:
			print "Role changed between set req and set rsp"
			rspcode = MCAP_RSP_INVALID_OPERATION
			rsp = CSPSetResponse(rspcode, 0, 0, 0)
			self.send_response(rsp)
			return False

		reset = new_tmstamp != tmstamp_dontset

		if reset:
			if sched_btclock != btclock_immediate:
				# compensate timestamp for lateness
				# of this callback
				delay = self.bt2us(self.btdiff(sched_btclock,
								btclock))
				if delay > 0 or new_tmstamp > -delay:
					new_tmstamp += delay
					action = "compensated"
				else:
					action = "not compensated"
				print "CSP set %dus late (%s)" \
					 % (delay, action)
			else:
				print "CSP set immediately, no compensation"

			self.reset_timestamp(t1 + latency, new_tmstamp)
			timestamp = new_tmstamp

		else:
			if sched_btclock != btclock_immediate:
				print "CSP scheduled query"
			else:
				print "CSP immediate query"

		# this is different from timestamp accuracy;
		# it needs to take latency into account
		tmstampacc = self.latency() + self.tmstampacc

		if update:
			# First indication after set rsp is immediate
			self.send_indication_cb(False)
			self.start_indication_alarm(ito)

		rspcode = MCAP_RSP_SUCCESS
		rsp = CSPSetResponse(rspcode, btclock, timestamp, tmstampacc)
		self.send_response(rsp)
		return False

	def set_response(self, message):
		if not self.valid_btclock(message.btclock):
			self.indication_expected = False
			return

		self.indication_expected = self.last_request.update

		schedule(self.observer.csp_set,
				self.mcl,
				message.rspcode != MCAP_RSP_SUCCESS,
				message.btclock, message.timestamp,
				message.tmstampacc)
	
	def info_indication(self, message):
		if not self.indication_expected:
			print "Unexpected indication received, ignoring"
			return
		elif not self.valid_btclock(message.btclock):
			return

		schedule(self.observer.csp_indication,
					self.mcl,
					message.btclock,
					message.timestamp,
					message.accuracy)

	def send_indication_cb(self, periodic):
		latency = self.preemption_thresh() + 1
		retry = 5

		while latency > self.preemption_thresh() and retry:
			t1 = time.time()
			btclock = self.get_btclock()
			timestamp = self.get_timestamp()
			latency = time.time() - t1
			retry -= 1

		if not btclock:
			return False

		btclock = btclock[0]
		tmstampacc = self.latency()
		rsp = CSPInfoIndication(btclock, timestamp, tmstampacc)
		self.send_request(rsp)
		return periodic

	def start_indication_alarm(self, ito):
		self.stop_indication_alarm()
		self.indication_alarm = timeout_call(ito // 1000 +
					self.synclead_ms(),
					self.send_indication_cb, True)
		timeout_call(0, self.send_indication_cb, False)

	def stop_indication_alarm(self):
		if self.indication_alarm:
			timeout_cancel(self.indication_alarm)
			self.indication_alarm = None

	def stop(self):
		self.stop_indication_alarm()

	@staticmethod
	def valid_btclock(btclock):
		'''
		Tests whether btclock is a 28-bit value
		'''
		return btclock >= 0 and btclock <= btclock_max

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
	assert(CSPStateMachine.btoffset(500, 500) == 0)
	assert(CSPStateMachine.btoffset(500, 501) == 1)
	assert(CSPStateMachine.btoffset(502, 500) == -2)
	assert(CSPStateMachine.btoffset(0, 0xfffffff) == -1)
	assert(CSPStateMachine.btoffset(0xffffffe, 0) == 2)
	assert(CSPStateMachine.btoffset(0, 0x7ffffff) == 0x7ffffff)
	assert(CSPStateMachine.btoffset(0, 0x8000000) == 0x8000000) 
	assert(CSPStateMachine.btoffset(0, 0x8000001) == -0x7ffffff)
	assert(CSPStateMachine.btoffsetdiff(1, 1) == 0)
	assert(CSPStateMachine.btoffsetdiff(1, 1000) == 999)
	assert(CSPStateMachine.btoffsetdiff(1000, 1) == 999)
	assert(CSPStateMachine.btoffsetdiff(-100000, 100000) == 200000)
	assert(CSPStateMachine.btoffsetdiff(100000, -100000) == 200000)
	assert(CSPStateMachine.btoffsetdiff(-100000, -100001) == 1)
	assert(CSPStateMachine.btoffsetdiff(-100000, -100001) == 1)

	import time
	b = BluetoothClock("00:00:00:00:00:00")

	print "Read clock RTT in microseconds: %d" % b.latency()
	print

	print "Reading native clock"
	# Can't fail
	clock1, accuracy = b.read(False)
	time.sleep(0.1)
	clock2, accuracy = b.read(False)
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
