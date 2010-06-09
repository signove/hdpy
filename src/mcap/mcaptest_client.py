#!/usr/bin/env python

import mcap_defs
import mcaptest
import mcap
import time
import sys
import gobject

btaddr = sys.argv[1]
psm = sys.argv[2]

mcl = mcap.MCL(btaddr, mcap.MCAP_MCL_ROLE_INITIATOR)

mcap_session = mcap.MCAPSession(mcl)

assert(mcl.state == mcap.MCAP_MCL_STATE_IDLE)

print "Requesting connection..."
if ( not mcl.is_cc_open() ):
	mcl.connect_cc((btaddr, int(psm)))

print "Connected!"
assert(mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)

if ( mcl.is_cc_open() ):
	mcap_session.start_session()
else:
	raise Exception ('ERROR: Cannot open control channel for initiator')

gobject.MainLoop().run()

#### send an invalid message (Op Code does not exist) ####
mcap_session.send_message(0x0AFF000ABC)
# receive a ERROR_RSP (0x00) with RSP Invalid OP (0x01)
# 0x00010000

mcap_session.wait_for_response()

#### send a CREATE_MD_REQ (0x01) with invalid MDLID == 0xFF00 (DO NOT ACCEPT) ####
mcap_session.send_message(0x01FF000ABC)
# receive a CREATE_MD_RSP (0x02) with RSP Invalid MDL (0x05)
# 0x0205FF00BC 

mcap_session.wait_for_response()

#### send a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0023 CONF = 0xBC (ACCEPT) ####
mcap_session.send_message(0x0100230ABC)
# receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
# 0x02000023BC

mcap_session.wait_for_response()

assert(mcap_session.mcl.count_mdls() == 1)
assert(mcap_session.state == mcap.MCAP_STATE_READY)
assert(mcap_session.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)

#### receive a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0024 CONF = 0xBC (ACCEPT) ####
mcap_session.send_message(0x0100240ABC)
# receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
# 0x02000024BC

mcap_session.wait_for_response()

assert(mcap_session.mcl.count_mdls() == 2)
assert(mcap_session.state == mcap.MCAP_STATE_READY)
assert(mcap_session.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)

#### receive a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0027 CONF = 0xBC (ACCEPT) ####
mcap_session.send_message(0x0100270ABC)
# receive a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
# 0x02000027BC

mcap_session.wait_for_response()

assert(mcap_session.mcl.count_mdls() == 3)
assert(mcap_session.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session.state == mcap.MCAP_STATE_READY)

#### send an invalid ABORT_MD_REQ (0x05) MDLID == 0x0027 (DO NOT ACCEPT - not on PENDING state)
mcap_session.send_message(0x050027)
# receive a ABORT_MD_RSP (0x06) with RSP Invalid Operation (0x07)
# 0x06070027

mcap_session.wait_for_response()

assert(mcap_session.mcl.count_mdls() == 3)
assert(mcap_session.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session.state == mcap.MCAP_STATE_READY)

#### send an invalid DELETE_MD_REQ (0x07) MDLID == 0x0030 (DO NOT ACCEPT - MDLID do not exist)
mcap_session.send_message(0x070030)
# receive a DELETE_MD_RSP (0x08) with RSP Invalid MDL (0x05)
# 0x08050030

mcap_session.wait_for_response()

assert(mcap_session.mcl.count_mdls() == 3)
assert(mcap_session.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session.state == mcap.MCAP_STATE_READY)

#### send a valid DELETE_MD_REQ (0x07) MDLID == 0x0027
mcap_session.send_message(0x070027)
# receive a DELETE_MD_RSP (0x08) with RSP Sucess (0x00)
# 0x08000027

mcap_session.wait_for_response()

assert(mcap_session.mcl.count_mdls() == 2)
assert(mcap_session.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session.state == mcap.MCAP_STATE_READY)

#### send a valid DELETE_MD_REQ (0x07) MDLID == MDL_ID_ALL (0XFFFF)
mcap_session.send_message(0x07FFFF)
# receive a DELETE_MD_RSP (0x08) with RSP Sucess (0x00)
# 0x0800FFFF

mcap_session.wait_for_response()

assert(mcap_session.mcl.count_mdls() == 0)
assert(mcap_session.mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)
assert(mcap_session.state == mcap.MCAP_STATE_READY)

mcap_session.close_session()

print 'TESTS OK' 
