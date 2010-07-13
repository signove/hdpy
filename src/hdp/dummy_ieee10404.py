# -*- coding: utf-8

################################################################
#
# Copyright (c) 2010 Signove. All rights reserved.
# See the COPYING file for licensing details.
#
# Autors: Elvis Pfützenreuter < epx at signove dot com >
#         Raul Herbster < raul dot herbster at signove dot com >
################################################################

#From IEEE Standard 11073-10404 page 62

from hdp_utils import *

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


def parse_message(msg):
	global assoc_resp_msg
	resp = ()

	if int(msg[0]) == 0xe2:
		print 'IEEE association request'
		resp = assoc_resp_msg

	elif int(msg[0])==0xe7:
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

	return resp


def parse_message_str(msg):
	return b2s(parse_message(s2b(msg)))
