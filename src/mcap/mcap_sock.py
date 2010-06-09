import time
from bluetooth import *
import bluetooth._bluetooth as bz

L2CAP_MODE_ERTM = 0x03
L2CAP_MODE_STREAMING = 0x04

bz.OCF_READ_CLOCK = 0x07


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
		except Exception as msg:
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


def hci_open_dev(dev_id):
	return bz.hci_open_dev(dev_id)


def hci_read_clock(sock):
	old_filter = sock.getsockopt(bz.SOL_HCI, bz.HCI_FILTER, 14)

	opcode = bz.cmd_opcode_pack(bz.OGF_STATUS_PARAM,
			bz.OCF_READ_CLOCK)
	flt = bz.hci_filter_new()
	bz.hci_filter_set_ptype(flt, bz.HCI_EVENT_PKT)
	bz.hci_filter_set_event(flt, bz.EVT_CMD_COMPLETE);
	bz.hci_filter_set_opcode(flt, opcode)
	sock.setsockopt( bz.SOL_HCI, bz.HCI_FILTER, flt )
	pkt = struct.pack("BBB", 0, 0, 0)
	bz.hci_send_cmd(sock, bz.OGF_STATUS_PARAM, bz.OCF_READ_CLOCK, pkt)

	pkt = sock.recv(255)

	sock.setsockopt(bz.SOL_HCI, bz.HCI_FILTER, old_filter)
	
	# HCI is little-endian
	status, handle, clock, accuracy = struct.unpack("<xxxxxxBHIH", pkt)
	return (clock, accuracy)


def test():
	raw = hci_open_dev(0)
	clock1, accuracy1 = hci_read_clock(raw)
	time.sleep(0.1)
	clock2, accuracy2 = hci_read_clock(raw)
	print "Clocks: %s %s" % (clock1, clock2)
	print "Accuracies: %s %s" % (accuracy1, accuracy2)
	print "Difference: %fs (should be near 0.1)" % ((clock2 - clock1) * 312.5 / 1000000.0)
	print

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
