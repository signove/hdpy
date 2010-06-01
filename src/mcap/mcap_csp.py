#!/usr/bin/env ptyhon

import mcap_sock

class BluetoothClock:
	"""
	This class is intended to be used as a singleton by all
	MCAP instances, as a Bluetooth Clock source.
	"""

	def __init__(self, device_id):
		self.raw_socket = mcap_sock.hci_open_dev(device_id)
	
	def get_clock(self):
		"""
		Returns a tuple with BT clock and accuracy.
		Accuracy may be zero (means theoretical infinit precision).
		Unit is Bluetooth "ticks" (312.5 us each), wraps 32 bits
		"""
		return mcap_sock.hci_read_clock(self.raw_socket)


def test():
	import time
	b = BluetoothClock(0)
	clock1, dummy = b.get_clock()
	time.sleep(0.1)
	clock2, dummy = b.get_clock()
	diff = clock2 - clock1
	print "Clocks: %d - %d = %d" % (clock1, clock2, diff)
	diff *= 312.5 / 1000000.0 # 312.5us per tick
	print "Diff in seconds (should be around 0.1): %f" % diff

# test()
