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
		self.clock_rtt = self._determine_clock_rtt()

	def read_clock_rtt(self):
		"""
		Returns how much time it takes to read HCI clock.
		Value in microseconds.
		"""
		return self.clock_rtt

	def _determine_clock_rtt(self):
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
		mcap_sock.hci_read_clock(self.raw_socket, None)
		t2 = time.time()
		# FIXME how to detect that we have been preempted?
		return int((t2 - t1) * 1000000)
	
	def get_clock(self, remote_addr=None):
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
		return mcap_sock.hci_read_clock(self.raw_socket, remote_addr)


class CSPStateMachine(object):
	def __init__(self, mainsm, mcl):
		self.mainsm = mainsm
		self.mcl = mcl
		self.csp_base_time = time.time()
		self.csp_base_counter = 0

	def is_mine(self, opcode):
		return opcode >= MCAP_MD_SYNC_MIN and \
			opcode <= MCAP_MD_SYNC_MAX

	def get_csp_timestamp(self):
		now = time.time()
		offset = now - self.csp_base_time
		offset = int(1000000 * offset) # convert to microseconds
		return self.csp_base_counter + offset

	def set_csp_timestamp(self, counter):
		# Reset counter to value provided by CSP-Master
		self.csp_base_time = time.time()
		self.csp_base_counter = counter

	def receive_message(self, opcode, message):
		pass
		

def test(argv0, target=None, l2cap_port=None, ertm=None):
	import time
	b = BluetoothClock(0)

	print "Read clock RTT in microseconds: %d" % b.read_clock_rtt()
	print

	print "Reading native clock"
	# Can't fail
	clock1, accuracy = b.get_clock()
	time.sleep(0.1)
	clock2, accuracy = b.get_clock()
	diff = clock2 - clock1
	print "Clocks: %d - %d = %d" % (clock1, clock2, diff)
	diff *= 312.5 / 1000000.0 # 312.5us per tick
	print "Diff in seconds (should be around 0.1): %f" % diff
	print "Accuracy: ", accuracy

	if not target:
		return

	# Creates an L2CAP connection just to make sure ACL is up
	s, psm = mcap_sock.create_socket("", ertm)
	try:
		s.connect((target, l2cap_port))
	except IOError:
		# It doesn't really matter if connection went up.
		pass

	print "Reading native clock"
	# Can fail
	clock1 = b.get_clock(target)
	if not clock1:
		print "Could not read clock (remote addr down?)"
		return

	time.sleep(0.1)
	clock2 = b.get_clock(target)
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
