#!/usr/bin/env python

import mcap_defs
import mcaptest
import mcap
import time

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

print "TESTS OK"
