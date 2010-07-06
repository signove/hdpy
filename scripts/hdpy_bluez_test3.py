#!/usr/bin/env python
# -*- coding: utf-8

################################################################
#
# Copyright (c) 2010 Signove. All rights reserved.
# See the COPYING file for licensing details.
#
# Autors: Elvis Pfützenreuter < epx at signove dot com >
#         Raul Herbster < raul dot herbster at signove dot com >
################################################################

'''
Test 3. Simple MDL creation, communication and close.
Procedure:
1. Start the server (hdpy_bluez_server.py)
2. Run this script
'''

from hdpy_bluez_client import MyInstance
from hdpy_bluez_client import run_test
from hdpy_bluez_client import MCAP_MCL_STATE_ACTIVE
from hdpy_bluez_client import MCAP_MCL_STATE_PENDING


#               CREATE_MD_REQ(0x01)   mdlid, mdepid, conf
SEND_SCRIPT = [(MyInstance.CreateMDL, 0x0023, 0x0a, 0xbc),
               (MyInstance.SendOnce, 'Hello '),
               (MyInstance.SendAndWait, 'mcap server'),
               (MyInstance.CloseMDL,),
               ]

# Sent raw data
SENT = ["0100230ABC",
        "",
        "",
        "050027",
        "07FFFF",
        ]

# Received raw data
RECEIVED = ["02000023BC", # CREATE_MD_RSP (0x02) with RSP Success (0x00)
            "",
            "Hello mcap client",
            "06000027", # ABORT_MD_RSP (0x06) with RSP Success
            "0800FFFF", # DELETE_MD_RSP (0x08) with RSP Success (0x00)
            ]

def check_asserts_cb(mcap, mcl):
    '''
    Check the mcap status
    '''
    if (mcap.counter == 0):
        assert(mcl.count_mdls() == 1)
        assert(mcl.sm.request_in_flight == 0)
        assert(mcl.state == MCAP_MCL_STATE_PENDING)
    elif (mcap.counter == 1):
        assert(mcl.count_mdls() == 1)
        assert(mcl.sm.request_in_flight == 0)
        assert(mcl.state == MCAP_MCL_STATE_ACTIVE)
#    elif (mcap.counter == 3):
#        assert(mcl.count_mdls() == 3)
#        assert(mcl.sm.request_in_flight == 0)
#        assert(mcl.state == MCAP_MCL_STATE_PENDING)

run_test(SEND_SCRIPT, SENT, RECEIVED, check_asserts_cb)
