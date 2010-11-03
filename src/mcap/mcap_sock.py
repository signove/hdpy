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

ENABLE_ERTM = True
SECURITY = True
DC_MTU = 512

DEFER_SETUP = True

import bluetooth

try:
	version = bluetooth.__version__
except:
	version = 0.18 # or less

if version < 0.19:
	raise ImportError("HDPy depends on PyBlueZ version 0.19 or better")


import time
from bluetooth import *
import bluetooth._bluetooth as bz
import errno
import socket
import select


pos = ["omtu", "imtu", "flush_to", "mode", "fcs", "max_tx", "txwin_size"]
i_mode = pos.index("mode")
i_fcs = pos.index("fcs")


def get_options(sock):
	return list(sock.get_l2cap_options())


def get_mode(sock):
	mode = 0x00
	option = sock.get_l2cap_options()
	if option[i_mode] == bz.L2CAP_MODE_ERTM:
		mode = 0x01
	elif option[i_mode] == bz.L2CAP_MODE_STREAMING:
		mode = 0x02
	return mode


def set_options(sock, options):
	return sock.set_l2cap_options(options)


def set_ertm(sock):
	if ENABLE_ERTM:
		options = get_options(sock)
		options[i_fcs] = 1
		options[i_mode] = bz.L2CAP_MODE_ERTM
		set_options(sock, options)


def set_security(sock):
	if SECURITY:
		sock.setl2capsecurity(bz.BT_SECURITY_MEDIUM)


def set_streaming(sock):
	if ENABLE_ERTM:
		options = get_options(sock)
		options[i_fcs] = 1
		options[i_mode] = bz.L2CAP_MODE_STREAMING
		set_options(sock, options)


def set_mtu(sock, mtu):
	return sock.set_l2cap_mtu(mtu)


def get_available_psm(adapter):
	# Ripped from PyBlueZ source

	for psm in range (0x1001, 0x8000, 2):
		s = BluetoothSocket(L2CAP)
		try:
			s.bind((adapter, psm))
			s.close()
			return psm
		except Exception as msg:
			s.close()

	raise Exception("No free PSM could be found")


def create_socket():
	return BluetoothSocket(proto=L2CAP)


def set_reliable(s, reliable):
	if reliable:
		set_ertm(s)
	else:
		set_streaming(s)
	print s, get_options(s)


def defer_setup(s):
	if DEFER_SETUP:
		s.setsockopt(bz.SOL_BLUETOOTH, bz.BT_DEFER_SETUP, 1)


def do_accept(s):
	if not DEFER_SETUP:
		return True

	try:
		r, w, x = select.select([], [s], [], 1)
		if not w:
			s.setblocking(False)
			try:
				s.recv(1)
			except IOError:
				pass
		return True
	except IOError:
		try:
			s.close()
		except IOError:
			pass
		return False


def create_control_socket():
	s = create_socket()
	set_security(s)
	set_reliable(s, True)
	set_mtu(s, 48)
	return s


def create_data_socket(reliable):
	s = create_socket()
	set_security(s)
	set_reliable(s, reliable)
	set_mtu(s, DC_MTU)
	return s


def create_control_listening_socket(btaddr):
	psm = get_available_psm(btaddr)
	print "Control socket: PSM %d" % psm
	s = create_control_socket()

	dev_id = bz.hci_devid(btaddr)
	if dev_id < 0 and btaddr and btaddr != "00:00:00:00:00:00":
		print "WARNING: the adapter address %s is invalid, " \
			"using default adapter" % btaddr
		btaddr = ""

	s.bind((btaddr, psm))
	s.listen(5)
	defer_setup(s)
	return (s, psm)


def create_data_listening_socket(btaddr):
	psm = get_available_psm(btaddr)
	# print "Data socket: PSM %d" % psm
	s = create_data_socket(True)

	dev_id = bz.hci_devid(btaddr)
	if dev_id < 0 and btaddr and btaddr != "00:00:00:00:00:00":
		print "WARNING: the adapter address %s is invalid, " \
			"using default adapter" % btaddr
		btaddr = ""

	s.bind((btaddr, psm))
	s.listen(5)
	defer_setup(s)

	return (s, psm)


def async_connect(sk, addr):
	sk.setblocking(False)
	try:
		sk.connect(addr)
	except IOError, e:
		# damn BluetoothError!
		e = eval(e[0])
		if e[0] == errno.EINPROGRESS:
			pass
		else:
			print "async connect() failed:", e[0]
			raise


def connection_ok(sk):
	''' Check if async connection went ok '''
	try:
		err = sk.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
	except IOError:
		err = -1
	return not err


def hci_open_dev(remote_addr):
	dev_id = bz.hci_get_route(remote_addr)
	# print "Device ID: %d" % dev_id
	return bz.hci_open_dev(dev_id), dev_id


def hci_read_clock(sock, remote_addr):
	acl = 0
	which_clock = 0 # native
	if remote_addr:
		which_clock = 1
		acl = bz.hci_acl_conn_handle(sock.fileno(), remote_addr)
		if acl < 0:
			print "ERROR in get_acl_conn (resorting to native clk)"
			return None

	return bz.hci_read_clock(sock.fileno(), acl, which_clock, 1000)


def hci_role(fd, dev_id):
	if dev_id < 0:
		return 0
	return bz.hci_role(fd.fileno(), dev_id)


def test():
	# all-zeros means default adapter
	raw, dev_id = hci_open_dev("00:00:00:00:00:00")
	print "Dev id", dev_id

	# Sometimes the very first read fails
	hci_read_clock(raw, None)
	hci_read_clock(raw, None)

	clock1, accuracy1 = hci_read_clock(raw, None)
	time.sleep(0.1)
	clock2, accuracy2 = hci_read_clock(raw, None)
	print "Native Clocks: %s %s" % (clock1, clock2)
	print "Accuracies: %s %s" % (accuracy1, accuracy2)
	print "Difference: %fs (should be near 0.1)" % ((clock2 - clock1) * 312.5 / 1000000.0)
	print

	s, psm = create_control_listening_socket("00:00:00:00:00:00")
	print "Listening control socket at PSM %d" % psm
	print "Options", get_options(s)

	t, psm = create_data_listening_socket("00:00:00:00:00:00")
	print "Listening data socket at PSM %d" % psm
	print "Options", get_options(t)

	v = create_control_socket()
	print "Control socket"
	print "Options", get_options(v)

	w = create_data_socket(True)
	print "Reliable data socket at PSM"
	print "Options", get_options(w)

	x = create_data_socket(False)
	print "Streaming data socket"
	print "Options", get_options(x)

	print "Role:", hci_role(raw, 0);

	time.sleep(1)


if __name__ == "__main__":
	test()
