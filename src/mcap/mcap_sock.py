import time
from bluetooth import *
import bluetooth._bluetooth as bz

L2CAP_MODE_ERTM = 0x03
L2CAP_MODE_STREAMING = 0x04

bz.OCF_READ_CLOCK = 0x07

# We handle options here because PyBluez has incomplete and buggy support
# Remove this from here if we settle using CVS version of PyBluez
# TODO add those features to PyBluez itself

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


def create_socket(btaddr, psm, reliable):
	if psm is None:
		psm = 0
	s = BluetoothSocket(proto=L2CAP)
	if reliable:
		set_ertm(s)
	else:
		set_streaming(s)
	s.setblocking(True)
	s.bind((btaddr, psm))
	return s


def create_control_socket(btaddr, psm=None):
	s = create_socket(btaddr, psm, True)
	set_mtu(s, 48)
	return s


def create_data_socket(btaddr, psm, reliable, mtu):
	s = create_socket(btaddr, psm, reliable)
	set_mtu(s, mtu)
	return s


def create_control_listening_socket(btaddr):
	psm = get_available_psm()
	s = create_control_socket(btaddr, psm)
	s.listen(5)
	return (s, psm)


def create_data_listening_socket(btaddr, reliable, mtu):
	psm = get_available_psm()
	s = create_data_socket(btaddr, psm, reliable, mtu)
	s.listen(5)
	return (s, psm)


def hci_open_dev(dev_id):
	return bz.hci_open_dev(dev_id)


# Ripped from PyBlueZ advanced examples
def _get_acl_conn_handle(sock, addr):
	hci_fd = sock.fileno()
	reqstr = struct.pack("6sB17s", bz.str2ba(addr), bz.ACL_LINK, "\0" * 17)
	request = array.array( "c", reqstr )
	try:
		fcntl.ioctl( hci_fd, bz.HCIGETCONNINFO, request, 1 )
		handle = struct.unpack("8xH14x", request.tostring())[0]
	except IOError:
		handle = -1
	return handle


# TODO add to pybluez
def hci_read_clock(sock, remote_addr):
	acl = 0
	which_clock = 0 # native
	if remote_addr:
		which_clock = 1
		acl = _get_acl_conn_handle(sock, remote_addr)
		if acl < 0:
			return None

	old_filter = sock.getsockopt(bz.SOL_HCI, bz.HCI_FILTER, 14)

	opcode = bz.cmd_opcode_pack(bz.OGF_STATUS_PARAM,
			bz.OCF_READ_CLOCK)
	flt = bz.hci_filter_new()
	bz.hci_filter_set_ptype(flt, bz.HCI_EVENT_PKT)
	bz.hci_filter_set_event(flt, bz.EVT_CMD_COMPLETE);
	bz.hci_filter_set_opcode(flt, opcode)
	sock.setsockopt( bz.SOL_HCI, bz.HCI_FILTER, flt )
	pkt = struct.pack("<HB", acl, which_clock)
	bz.hci_send_cmd(sock, bz.OGF_STATUS_PARAM, bz.OCF_READ_CLOCK, pkt)

	while True:
		pkt = sock.recv(255)
		# HCI is little-endian
		status, handle, clock, accuracy = struct.unpack("<xxxxxxBHIH", pkt)
		if handle == acl:
			break

	sock.setsockopt(bz.SOL_HCI, bz.HCI_FILTER, old_filter)
	
	if status:
		return None

	return (clock, accuracy)


def test():
	raw = hci_open_dev(0)
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

	t, psm = create_data_listening_socket("00:00:00:00:00:00", True, 512)
	print "Listening reliable data socket at PSM %d" % psm
	print "Options", get_options(t)

	u, psm = create_data_listening_socket("00:00:00:00:00:00", False, 512)
	print "Listening streaming data socket at PSM %d" % psm
	print "Options", get_options(u)

	v = create_control_socket("00:00:00:00:00:00")
	print "Control socket"
	print "Options", get_options(v)

	w = create_data_socket("00:00:00:00:00:00", None, True, 512)
	print "Reliable data socket at PSM"
	print "Options", get_options(w)

	x = create_data_socket("00:00:00:00:00:00",  None, False, 512)
	print "Streaming data socket"
	print "Options", get_options(x)

	time.sleep(1)


if __name__ == "__main__":
	test()
