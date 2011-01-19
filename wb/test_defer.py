#!/usr/bin/env python
# -*- coding: utf-8

ENABLE_ERTM = True
SECURITY = True
DC_MTU = 250
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
import random

pos = ["omtu", "imtu", "flush_to", "mode", "fcs", "max_tx", "txwin_size"]
i_mode = pos.index("mode")
i_fcs = pos.index("fcs")
i_omtu = pos.index("omtu")
i_imtu = pos.index("imtu")


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
	options = get_options(sock)
	options[i_omtu] = mtu
	options[i_imtu] = mtu
	set_options(sock, options)


def get_mtu(sock):
	return get_options(sock)[i_omtu]


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
	# print s, get_options(s)


def defer_setup(s):
	if DEFER_SETUP:
		s.setsockopt(bz.SOL_BLUETOOTH, bz.BT_DEFER_SETUP, 30)


def do_accept(s):
	if not DEFER_SETUP:
		return True

	try:
		p = select.poll()
		p.register(s, select.POLLOUT)
		if not p.poll(1000):
			print "############# defer select failed"
			s.setblocking(False)
			try:
				s.recv(1)
			except IOError:
				pass
		else:
			print "########### defer select ok"

		return True
	except IOError:
		try:
			s.close()
		except IOError:
			pass
		return False



def create_data_socket(reliable):
	s = create_socket()
	set_security(s)
	set_reliable(s, reliable)
	set_mtu(s, DC_MTU)
	return s


def create_data_listening_socket(psm):
	s = create_data_socket(True)
	s.bind(("", psm))
	s.listen(5)
	defer_setup(s)
	return s


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


def initiator(target):
	pending = []
	conns = []
	while True:
		print "Status: %d pending %d up" % (len(pending), len(conns))
		r, w, x = select.select(pending + conns, [], [], 2)
		for sk in r:
			if sk in pending:
				pending.remove(sk)
				if connection_ok(sk):
					print "Connection established"
					print "\tOptions of new client:",
					print get_options(new)[i_omtu]
					conns.append(sk)
				else:
					print "Connection failed"
			else:
				# server is not supposed to send data, but...
				data = sk.recv(4096)

		if random.random() < 0.3 or (not pending and not conns):
			# create new connection
			new = create_data_socket()
			pending.append(new)
			async_connect(target)

		if random.random() < 0.3 and conns:
			# remove some connection
			victim = random.choice(conns)
			victim.close()
			conns.remove(victim)

		for sk in conns:
			if random.random() > 0.5:
				sk.send("a" * (int(random.random() * 10) + 1))
			

def acceptor(psm):
	s = create_data_listening_socket(psm)
	clients = []
	print "Options", get_options(s)
	while True:
		r, w, x = select.select([s] + clients, [], [], 0)
		for sk in r:
			if sk is s:
				print "New connection"
				new, addr = s.accept()
				if not do_accept(new):
					continue
				time.sleep(0.1) # trick
				print "Options of new client:",
				print get_options(new)[i_omtu]
				clients.append(new)
				
			else:
				data = sk.recv(4096)
				print "Read %d bytes from %s" % (len(data), sk)
				if len(data) <= 0:
					sk.close()
					clients.remove(sk)
				

if len(sys.argv) > 1:
	initiator((sys.argv[1], 4099))
else:
	acceptor(4099)
