#!/usr/bin/env python

import mcap_defs
import mcaptest
import mcap

createReq = mcap_defs.CreateMDLRequestMessage(0x01, 0x01, 0x0001)
assert(createReq.mdlid == 0x01)
assert(createReq.mdepid == 0x01)
assert(createReq.opcode == mcap_defs.MCAP_MD_CREATE_MDL_REQ)

reconnectReq = mcap_defs.ReconnectMDLRequestMessage(0x01)
assert(reconnectReq.mdlid == 0x01)
assert(reconnectReq.opcode == mcap_defs.MCAP_MD_RECONNECT_MDL_REQ)

deleteReq = mcap_defs.DeleteMDLRequestMessage(0x02)
assert(deleteReq.mdlid == 0x02)
assert(deleteReq.opcode == mcap_defs.MCAP_MD_DELETE_MDL_REQ)

abortReq = mcap_defs.AbortMDLRequestMessage(0x03)
assert(abortReq.mdlid == 0x03)
assert(abortReq.opcode == mcap_defs.MCAP_MD_ABORT_MDL_REQ)

# TEST PARSER

messageParser = mcap_defs.MessageParser()


# test CreateReq message parsing
createReqMessage = 0x0100230ABC
createReqPackage = messageParser.parse_message(createReqMessage)
assert(createReqPackage.opcode == mcap_defs.MCAP_MD_CREATE_MDL_REQ)
assert(createReqPackage.mdlid == 0x0023)
assert(createReqPackage.mdepid == 0x0A)
assert(createReqPackage.conf == 0xBC)


# test ReconnectReq message parsing
reconnectReqMessage = 0x0300AB
reconnectReqPackage = messageParser.parse_message(reconnectReqMessage)
assert(reconnectReqPackage.opcode == mcap_defs.MCAP_MD_RECONNECT_MDL_REQ)
assert(reconnectReqPackage.mdlid == 0x00AB)


# test AbortReq message parsing
abortReqMessage = 0x0500AB
abortReqPackage = messageParser.parse_message(abortReqMessage)
assert(abortReqPackage.opcode == mcap_defs.MCAP_MD_ABORT_MDL_REQ)
assert(abortReqPackage.mdlid == 0x00AB)


# test DeleteReq message parsing
deleteReqMessage = 0x0700CC
deleteReqPackage = messageParser.parse_message(deleteReqMessage)
assert(deleteReqPackage.opcode == mcap_defs.MCAP_MD_DELETE_MDL_REQ)
assert(deleteReqPackage.mdlid == 0x00CC)


# test CreateRsp message parsing
createRspMessage = 0x0200002307
createRspPackage = messageParser.parse_message(createRspMessage)
assert(createRspPackage.opcode == mcap_defs.MCAP_MD_CREATE_MDL_RSP)
assert(createRspPackage.mdlid == 0x0023)
assert(createRspPackage.rspcode == mcap_defs.MCAP_RSP_SUCCESS)
assert(createRspPackage.params == 0x07)


# test ReconnectRsp message parsing
reconnectRspMessage = 0x040200AB
reconnectRspPackage = messageParser.parse_message(reconnectRspMessage)
assert(reconnectRspPackage.opcode == mcap_defs.MCAP_MD_RECONNECT_MDL_RSP)
assert(reconnectRspPackage.mdlid == 0x00AB)
assert(reconnectRspPackage.rspcode == mcap_defs.MCAP_RSP_INVALID_PARAMETER_VALUE)


# test AbortRsp message parsing
abortRspMessage = 0x0605FFFF
abortRspPackage = messageParser.parse_message(abortRspMessage)
assert(abortRspPackage.opcode == mcap_defs.MCAP_MD_ABORT_MDL_RSP)
assert(abortRspPackage.mdlid == 0xFFFF)
assert(abortRspPackage.rspcode == mcap_defs.MCAP_RSP_INVALID_MDL)

# test DeleteRsp message parsing
deleteRspMessage = 0x080000CC
deleteRspPackage = messageParser.parse_message(deleteRspMessage)
assert(deleteRspPackage.opcode == mcap_defs.MCAP_MD_DELETE_MDL_RSP)
assert(deleteRspPackage.mdlid == 0x00CC)
assert(deleteRspPackage.rspcode == mcap_defs.MCAP_RSP_SUCCESS)

# test state machine
mcl_init = mcap.MCL("00:21:FE:A0:EC:49")
mcl_acep = mcap.MCL("00:1D:D9:EE:C5:78")

mcap_session_initiator = mcap.MCAPImpl(mcl_init)
mcap_session_acceptor = mcap.MCAPImpl(mcl_acep)
mcap_session_acceptor.role = mcap.MCAP_MCL_ROLE_ACCEPTOR

assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_IDLE)
assert(mcap_session_acceptor.mcl.state == mcap.MCAP_MCL_STATE_IDLE)

mcap_session_initiator.remote = mcap_session_acceptor
mcap_session_acceptor.remote = mcap_session_initiator

# create control channel
mcap_session_initiator.init_session()
mcap_session_acceptor.init_session()
assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)
assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)

#### send an invalid message (Op Code does not exist) ####
#mcap_session_initiator.send_message(0x0AFF000ABC)
#assert(mcap_session_initiator.last_sent == 0x0AFF000ABC)
#assert(mcap_session_acceptor.last_received == 0x0AFF000ABC)
# return a ERROR_RSP (0x00) with RSP Invalid OP (0x01)
#assert(mcap_session_acceptor.last_sent == 0x00010000)
#assert(mcap_session_initiator.last_received == 0x00010000)

#assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)
#assert(mcap_session_initiator.state == mcap.MCAP_STATE_READY)
#assert(mcap_session_acceptor.mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)
#assert(mcap_session_acceptor.state == mcap.MCAP_STATE_READY)


#### receive a CREATE_MD_REQ (0x01) with invalid MDLID == 0xFF00 (DO NOT ACCEPT) ####
mcap_session_initiator.send_message(0x01FF000ABC)
assert(mcap_session_initiator.last_sent == 0x01FF000ABC)
assert(mcap_session_acceptor.last_received == 0x01FF000ABC)
# return a CREATE_MD_RSP (0x02) with RSP Invalid MDL (0x05)
assert(mcap_session_acceptor.last_sent == 0x0205FF00BC)
assert(mcap_session_initiator.last_received == 0x0205FF00BC)

assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)
assert(mcap_session_initiator.state == mcap.MCAP_STATE_READY)
assert(mcap_session_acceptor.mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)
assert(mcap_session_acceptor.state == mcap.MCAP_STATE_READY)

#### receive a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0023 CONF = 0xBC (ACCEPT) ####
mcap_session_initiator.send_message(0x0100230ABC)
assert(mcap_session_initiator.last_sent == 0x0100230ABC)
assert(mcap_session_acceptor.last_received == 0x0100230ABC)
# return a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
assert(mcap_session_acceptor.last_sent == 0x02000023BC)
assert(mcap_session_initiator.last_received == 0x02000023BC)

assert(mcap_session_initiator.mcl.count_mdls() == 1)
assert(mcap_session_acceptor.mcl.count_mdls() == 1)
assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_initiator.state == mcap.MCAP_STATE_READY)
assert(mcap_session_acceptor.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_acceptor.state == mcap.MCAP_STATE_READY)

#### receive a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0024 CONF = 0xBC (ACCEPT) ####
mcap_session_initiator.send_message(0x0100240ABC)
assert(mcap_session_initiator.last_sent == 0x0100240ABC)
assert(mcap_session_acceptor.last_received == 0x0100240ABC)
# return a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
assert(mcap_session_acceptor.last_sent == 0x02000024BC)
assert(mcap_session_initiator.last_received == 0x02000024BC)

assert(mcap_session_initiator.mcl.count_mdls() == 2)
assert(mcap_session_acceptor.mcl.count_mdls() == 2)
assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_initiator.state == mcap.MCAP_STATE_READY)
assert(mcap_session_acceptor.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_acceptor.state == mcap.MCAP_STATE_READY)

#### receive a CREATE_MD_REQ (0x01) MDEPID == 0x0A MDLID == 0x0027 CONF = 0xBC (ACCEPT) ####
mcap_session_initiator.send_message(0x0100270ABC)
assert(mcap_session_initiator.last_sent == 0x0100270ABC)
assert(mcap_session_acceptor.last_received == 0x0100270ABC)
# return a CREATE_MD_RSP (0x02) with RSP Sucess (0x00)
assert(mcap_session_acceptor.last_sent == 0x02000027BC)
assert(mcap_session_initiator.last_received == 0x02000027BC)

assert(mcap_session_initiator.mcl.count_mdls() == 3)
assert(mcap_session_acceptor.mcl.count_mdls() == 3)
assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_initiator.state == mcap.MCAP_STATE_READY)
assert(mcap_session_acceptor.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_acceptor.state == mcap.MCAP_STATE_READY)

#### send an invalid ABORT_MD_REQ (0x05) MDLID == 0x0027 (DO NOT ACCEPT - not on PENDING state)
mcap_session_initiator.send_message(0x050027)
assert(mcap_session_initiator.last_sent == 0x050027)
assert(mcap_session_acceptor.last_received == 0x050027)
# return a ABORT_MD_RSP (0x06) with RSP Invalid Operation (0x07)
assert(mcap_session_acceptor.last_sent == 0x06070027)
assert(mcap_session_initiator.last_received == 0x06070027)

assert(mcap_session_initiator.mcl.count_mdls() == 3)
assert(mcap_session_acceptor.mcl.count_mdls() == 3)
assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_initiator.state == mcap.MCAP_STATE_READY)
assert(mcap_session_acceptor.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_acceptor.state == mcap.MCAP_STATE_READY)

#### send an invalid DELETE_MD_REQ (0x07) MDLID == 0x0030 (DO NOT ACCEPT - MDLID do not exist)
mcap_session_initiator.send_message(0x070030)
assert(mcap_session_initiator.last_sent == 0x070030)
assert(mcap_session_acceptor.last_received == 0x070030)
# return a DELETE_MD_RSP (0x08) with RSP Invalid MDL (0x05)
assert(mcap_session_acceptor.last_sent == 0x08050030)
assert(mcap_session_initiator.last_received == 0x08050030)

assert(mcap_session_initiator.mcl.count_mdls() == 3)
assert(mcap_session_acceptor.mcl.count_mdls() == 3)
assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_initiator.state == mcap.MCAP_STATE_READY)
assert(mcap_session_acceptor.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_acceptor.state == mcap.MCAP_STATE_READY)

#### send a valid DELETE_MD_REQ (0x07) MDLID == 0x0027
mcap_session_initiator.send_message(0x070027)
assert(mcap_session_initiator.last_sent == 0x070027)
assert(mcap_session_acceptor.last_received == 0x070027)
# return a DELETE_MD_RSP (0x08) with RSP Sucess (0x00)
assert(mcap_session_acceptor.last_sent == 0x08000027)
assert(mcap_session_initiator.last_received == 0x08000027)

assert(mcap_session_initiator.mcl.count_mdls() == 2)
assert(mcap_session_acceptor.mcl.count_mdls() == 2)
assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_initiator.state == mcap.MCAP_STATE_READY)
assert(mcap_session_acceptor.mcl.state == mcap.MCAP_MCL_STATE_ACTIVE)
assert(mcap_session_acceptor.state == mcap.MCAP_STATE_READY)

#### send a valid DELETE_MD_REQ (0x07) MDLID == MDL_ID_ALL (0XFFFF)
mcap_session_initiator.send_message(0x07FFFF)
assert(mcap_session_initiator.last_sent == 0x07FFFF)
assert(mcap_session_acceptor.last_received == 0x07FFFF)
# return a DELETE_MD_RSP (0x08) with RSP Sucess (0x00)
assert(mcap_session_acceptor.last_sent == 0x0800FFFF)
assert(mcap_session_initiator.last_received == 0x0800FFFF)

assert(mcap_session_initiator.mcl.count_mdls() == 0)
assert(mcap_session_acceptor.mcl.count_mdls() == 0)
assert(mcap_session_initiator.mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)
assert(mcap_session_initiator.state == mcap.MCAP_STATE_READY)
assert(mcap_session_acceptor.mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)
assert(mcap_session_acceptor.state == mcap.MCAP_STATE_READY)

print 'TESTS OK' 
