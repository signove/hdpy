#!/usr/bin/env python

import mcaptest_defs
import mcaptest

createReq = mcaptest_defs.CreateMDLRequestMessage(0x01, 0x01, 0x0001)
assert(createReq.mdlid == 0x01)
assert(createReq.mdepid == 0x01)
assert(createReq.opcode == mcaptest_defs.MCAP_MD_CREATE_MDL_REQ)

print 'TESTS OK' 
