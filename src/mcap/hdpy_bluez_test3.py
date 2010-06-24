#!/usr/bin/env python

'''
Test 2. Simple MCL creation
'''

#!/usr/bin/env python

from hdpy_bluez_client import *


#               CREATE_MD_REQ(0x01)   mdlid, mdepid, conf
SEND_SCRIPT = [(MyInstance.CreateMDL, 0x0023, 0x0a, 0xbc),
               (MyInstance.SendOnce, 'Hello '),
               (MyInstance.SendAndWait, 'mcap server'),
               ]

# Sent raw data
SENT = ["0100230ABC",
        "",
        "",
        ]

# Received raw data
RECEIVED = ["02000023BC", # CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
            "",
            "Hello mcap client",
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
