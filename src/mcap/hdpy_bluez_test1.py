#!/usr/bin/env python

'''
A simple test case, sends an invalid message
'''

from hdpy_bluez_client import *

#send an invalid message (Op Code does not exist)
SEND_SCRIPT = [(MyInstance.SendRawRequest, 0x0b, 0xff, 0x00, 0x0a, 0xbc)]
SENT = ['0BFF000ABC'] # send an invalid message (Op Code does not exist)
RECEIVED = ['00010000'] # receive a ERROR_RSP (0x00) with RSP Invalid OP (0x01)

run_test(SEND_SCRIPT, SENT, RECEIVED, None)
