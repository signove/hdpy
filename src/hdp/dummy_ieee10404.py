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

#From IEEE Standard 11073-10404 page 62

from hdp_utils import *
from random import randint

assoc_resp_msg = (
	0xe3, 0x00, #APDU CHOICE Type(AareApdu)
	0x00, 0x2c, #CHOICE.length = 44
	0x00, 0x00, #result=accept
	0x50, 0x79, #data-proto-id = 20601
	0x00, 0x26, #data-proto-info length = 38
	0x80, 0x00, 0x00, 0x00, #protocolVersion
	0x80, 0x00, #encoding rules = MDER
	0x80, 0x00, 0x00, 0x00, #nomenclatureVersion
	0x00, 0x00, 0x00, 0x00, #functionalUnits, normal Association
	0x80, 0x00, 0x00, 0x00, #systemType = sys-type-manager
	0x00, 0x08, #system-id length = 8 and value (manufacturer- and device- specific) 
	0x88, 0x77, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11,
	0x00, 0x00, #Manager's response to config-id is always 0
	0x00, 0x00, #Manager's response to data-req-mode-flags is always 0
	0x00, 0x00, #data-req-init-agent-count and data-req-init-manager-count are always 0
	0x00, 0x00, 0x00, 0x00, #optionList.count = 0 | optionList.length = 0
	)

release_response = (0xe5, 0x00, 0x00, 0x02, 0x00, 0x00)

def parse_message(msg):
	resp = ()

	if int(msg[0]) == 0xe2:
		print 'IEEE association request'
		resp = assoc_resp_msg

	elif int(msg[0]) == 0xe7:
		print 'IEEE agent data'
		resp = (
			0xe7, 0x00, #APDU CHOICE Type(PrstApdu)
			0x00, 0x12, #CHOICE.length = 18
			0x00, 0x10, #OCTET STRING.length = 16
			int(msg[6]), int(msg[7]), #invoke-id (mirrored from invocation) 
			0x02, 0x01, #CHOICE(Remote Operation Response | Confirmed Event Report)
			0x00, 0x0a, #CHOICE.length = 10
			0x00, 0x00, #obj-handle = 0 (MDS object)
			0x00, 0x00, 0x00, 0x00, #currentTime = 0
			0x0d, 0x1d, #event-type = MDC_NOTI_SCAN_REPORT_FIXED
			0x00, 0x00, #event-reply-info.length = 0
			)
		print '\nSpO2 Level: %d, Beats/second: %d\n' % \
			(int(msg[35]), int(msg[49]))

	elif int(msg[0]) == 0xe4 or int(msg[0]) == 0xe5:
		print "IEEE release requested %x" % int(msg[0])
		resp = release_response

	return resp


def parse_message_str(msg):
	return b2s(parse_message(s2b(msg)))


# Dumped from Nonin Oximeter
sample_assoc_request = (0xe2, 0x0, 0x0, 0x32, 0x80, 0x0, 0x0, 0x0, 0x0, 0x1, 0x0, 0x2a, 0x50, 0x79, 0x0, 0x26, 0x80, 0x0, 0x0, 0x0, 0x80, 0x0, 0x80, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x80, 0x0, 0x0, 0x0, 0x8, 0x0, 0x1c, 0x5, 0x1, 0x0, 0x0, 0x28, 0x85, 0x1, 0x91, 0x0, 0x1, 0x1, 0x0, 0x0, 0x0, 0x0, 0x0)


# Dumped from Nonin Oximeter
sample_indication = [0xe7, 0x0, 0x0, 0x36, 0x0, 0x34, 0x80, 0x0, 0x1, 0x0, 0x0, 0x2e, 0x0, 0x0, 0x0, 0x8, 0xa3, 0x40, 0xd, 0x1d, 0x0, 0x24, 0xf0, 0x0, 0x0, 0x0, 0x0, 0x2, 0x0, 0x1c, 0x0, 0x1, 0x0, 0xa, 0x0, 0x62, 0x20, 0x7, 0x10, 0x1, 0x8, 0x31, 0x42, 0x0, 0x0, 0xa, 0x0, 0xa, 0x0, 0x69, 0x20, 0x7, 0x10, 0x1, 0x8, 0x31, 0x42, 0x0]


def make_assoc():
	return sample_assoc_request

def make_assoc_str():
	return b2s(make_assoc())

def make_sample():
	ind = sample_indication[:]
	ind[35] = randint(90, 100)
	ind[49] = randint(55, 105)
	return tuple(ind)

def make_sample_str():
	return b2s(make_sample())
