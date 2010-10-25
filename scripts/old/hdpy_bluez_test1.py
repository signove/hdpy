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
A simple test case, sends an invalid message.
Procedure:
1. Start the server (hdpy_bluez_server.py)
2. Run this script
'''

from hdpy_bluez_client import MyInstance
from hdpy_bluez_client import run_test


#send an invalid message (Op Code does not exist)
SEND_SCRIPT = [(MyInstance.SendRawRequest, 0x0b, 0xff, 0x00, 0x0a, 0xbc)]
SENT = ['0BFF000ABC'] # send an invalid message (Op Code does not exist)
RECEIVED = ['00010000'] # receive a ERROR_RSP (0x00) with RSP Invalid OP (0x01)

run_test(SEND_SCRIPT, SENT, RECEIVED, None)
