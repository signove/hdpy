import time
from bluetooth import *

L2CAP_MODE_ERTM = 0x03
L2CAP_MODE_STREAMING = 0x04


# We handle options here because PyBluez has incomplete and buggy support
# FIXME implementation-dependent interpretation of a C struct!

options_len = 12
pos = ["omtu", "imtu", "flush_to", "mode", "fcs", "max_tx", "txwin_size"]
mask = "HHHBBBH"
i_omtu = pos.index("omtu")
i_imtu = pos.index("imtu")
i_mode = pos.index("mode")
i_fcs = pos.index("fcs")


def get_options(sock):
	s = sock.getsockopt(SOL_L2CAP, L2CAP_OPTIONS, options_len)
	options = struct.unpack(mask, s)
	return list(options)


def set_options(sock, options):
	s = struct.pack(mask, *options)
	sock.setsockopt(SOL_L2CAP, L2CAP_OPTIONS, s)


def set_ertm(sock):
	options = get_options(sock)
	options[i_fcs] = 1
	options[i_mode] = L2CAP_MODE_ERTM
	set_options(sock, options)


def set_streaming(sock):
	options = get_options(sock)
	options[i_fcs] = 1
	options[i_mode] = L2CAP_MODE_STREAMING
	set_options(sock, options)


def set_mtu(sock, mtu):
	options = get_options(sock)
	options[i_omtu] = options[i_imtu] = mtu
	set_options(sock, options)


def get_available_psm():
	# Ripped from PyBlueZ source

	for psm in range (0x1001, 0x8000, 2):
		s = BluetoothSocket(L2CAP)
		try:
			s.bind(("", psm))
			s.close()
			return psm
		except:
			s.close()

	raise Exception("No free PSM could be found")


def create_socket(btaddr, reliable):
	psm = get_available_psm()
	s = BluetoothSocket(proto=L2CAP)
	if reliable:
		set_ertm(s)
	else:
		set_streaming(s)
	s.bind((btaddr, psm))
	return (s, psm)


def create_control_socket(btaddr):
	s, psm = create_socket(btaddr, True)
	set_mtu(s, 48)
	return (s, psm)


def create_data_socket(btaddr, reliable, mtu):
	s, psm = create_socket(btaddr, reliable)
	set_mtu(s, mtu)
	return (s, psm)


def create_control_listening_socket(btaddr):
	s, psm = create_control_socket(btaddr)
	s.listen(5)
	return (s, psm)


def create_data_listening_socket(btaddr, reliable, mtu):
	s, psm = create_data_socket(btaddr, reliable, mtu)
	s.listen(5)
	return (s, psm)


def test():
	s, psm = create_control_listening_socket("00:00:00:00:00:00")
	print "Listening control socket at PSM %d" % psm
	print "Options", get_options(s)

	t, psm = create_data_listening_socket("00:00:00:00:00:00", True, 512)
	print "Listening reliable data socket at PSM %d" % psm
	print "Options", get_options(t)

	u, psm = create_data_listening_socket("00:00:00:00:00:00", False, 512)
	print "Listening streaming data socket at PSM %d" % psm
	print "Options", get_options(u)

	v, psm = create_control_socket("00:00:00:00:00:00")
	print "Control socket at PSM %d" % psm
	print "Options", get_options(v)

	w, psm = create_data_socket("00:00:00:00:00:00", True, 512)
	print "Reliable data socket at PSM %d" % psm
	print "Options", get_options(w)

	x, psm = create_data_socket("00:00:00:00:00:00", False, 512)
	print "Rtreaming data socket at PSM %d" % psm
	print "Options", get_options(x)

	time.sleep(1)

# test()
