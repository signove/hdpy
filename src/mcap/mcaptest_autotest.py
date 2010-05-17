#!/usr/bin/env python

import mcaptest_defs
import mcaptest

createReq = mcaptest_defs.CreateMDLRequestMessage(0x01, 0x01, 0x0001)
assert(createReq.mdlid == 0x01)
assert(createReq.mdepid == 0x01)
assert(createReq.opcode == mcaptest_defs.MCAP_MD_CREATE_MDL_REQ)

reconnectReq = mcaptest_defs.ReconnectMDLRequestMessage(0x01)
assert(reconnectReq.mdlid == 0x01)
assert(reconnectReq.opcode == mcaptest_defs.MCAP_MD_RECONNECT_MDL_REQ)

deleteReq = mcaptest_defs.DeleteMDLRequestMessage(0x02)
assert(deleteReq.mdlid == 0x02)
assert(deleteReq.opcode == mcaptest_defs.MCAP_MD_DELETE_MDL_REQ)

abortReq = mcaptest_defs.AbortMDLRequestMessage(0x03)
assert(abortReq.mdlid == 0x03)
assert(abortReq.opcode == mcaptest_defs.MCAP_MD_ABORT_MDL_REQ)

print 'TESTS OK' 
