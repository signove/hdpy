#!/usr/bin/env python

import struct

# Op Codes
MCAP_ERROR_RSP				= 0x00
MCAP_MD_CREATE_MDL_REQ			= 0x01
MCAP_MD_CREATE_MDL_RSP			= 0x02
MCAP_MD_RECONNECT_MDL_REQ		= 0x03
MCAP_MD_RECONNECT_MDL_RSP		= 0x04
MCAP_MD_ABORT_MDL_REQ			= 0x05
MCAP_MD_ABORT_MDL_RSP			= 0x06
MCAP_MD_DELETE_MDL_REQ			= 0x07
MCAP_MD_DELETE_MDL_RSP			= 0x08

# CSP Op Coodes

MCAP_MD_SYNC_CAP_REQ			= 0x11
MCAP_MD_SYNC_CAP_RSP			= 0x12
MCAP_MD_SYNC_SET_REQ			= 0x13
MCAP_MD_SYNC_SET_RSP			= 0x14
MCAP_MD_SYNC_INFO_IND			= 0x15
MCAP_MD_SYNC_INFO_IND_RESEREVED		= 0x16

# Response Codes
MCAP_RSP_SUCCESS			= 0x00
MCAP_RSP_INVALID_OP_CODE		= 0x01
MCAP_RSP_INVALID_PARAMETER_VALUE	= 0x02
MCAP_RSP_INVALID_MDEP			= 0x03
MCAP_RSP_MDEP_BUSY			= 0x04
MCAP_RSP_INVALID_MDL			= 0x05
MCAP_RSP_MDL_BUSY			= 0x06
MCAP_RSP_INVALID_OPERATION		= 0x07
MCAP_RSP_RESOURCE_UNAVAILABLE		= 0x08
MCAP_RSP_UNSPECIFIED_ERROR		= 0x09
MCAP_RSP_REQUEST_NOT_SUPPORTED		= 0x0A
MCAP_RSP_CONFIGURATION_REJECTED		= 0x0B

# MDL IDs
MCAP_MDL_ID_INITIAL			= 0x0001
MCAP_MDL_ID_FINAL			= 0xFEFF
MCAP_MDL_ID_ALL				= 0xFFFF

# MDEP IDs
MCAP_MDEP_ID_INITIAL			= 0x00
MCAP_MDEP_ID_FINAL			= 0x7F

# Errors

class InvalidMessage(Exception):
	pass

class InvalidOperation(Exception):
	pass

# General messages

class MDLRequest:
	mask1 = ">BH"
	mask1_size = struct.calcsize(mask1)

	def __init__(self, opcode, mdlid):
		self.opcode = opcode
		self.mdlid = mdlid

	def encode(self):
		return struct.pack(self.mask1, self.opcode, self.mdlid)

	@staticmethod
	def length():
		return MDLRequest.mask1_size

	@staticmethod
	def _decode(message):
		data = struct.unpack(MDLRequest.mask1, message[0:MDLRequest.mask1_size])
		return list(data[1:]), message[MDLRequest.mask1_size:]


class MDLResponse:
	mask1 = ">BBH"
	mask1_size = struct.calcsize(mask1)

	def __init__(self, opcode, rspcode, mdlid):
		self.opcode = opcode
		self.rspcode = rspcode
		self.mdlid = mdlid

	def encode(self):
		return struct.pack(self.mask1, self.opcode, self.rspcode, self.mdlid)

	@staticmethod
	def length():
		return MDLResponse.mask1_size

	@staticmethod
	def _decode(message):
		data = struct.unpack(MDLResponse.mask1, message[0:MDLResponse.mask1_size])
		return list(data[1:]), message[MDLResponse.mask1_size:]


class CSPRequest:
	mask1 = ">B"
	mask1_size = struct.calcsize(mask1)

	def __init__(self, opcode):
		self.opcode = opcode

	def encode(self):
		return struct.pack(mask1, self.opcode)

	@staticmethod
	def length():
		return mask1_size

	@staticmethod
	def _decode(message):
		data = struct.unpack(mask1, message[0:mask1_size])
		return list(data[1:]), message[mask1_size:]


class CSPResponse:
	mask1 = ">BB"
	mask1_size = struct.calcsize(mask1)

	def __init__(self, opcode, rspcode):
		self.opcode = opcode
		self.rspcode = rspcode

	def encode(self):
		return struct.pack(mask1, self.opcode, self.rspcode)

	@staticmethod
	def length():
		return mask1_size

	@staticmethod
	def _decode(message):
		data = struct.unpack(mask1, message[0:mask1_size])
		return list(data[1:]), message[mask1_size:]


# Specific request messages

class CreateMDLRequest( MDLRequest ):
	mask2 = ">BB"
	mask2_size = struct.calcsize(mask2)

	def __init__(self, mdlid, mdepid, conf):
		MDLRequest.__init__(self, MCAP_MD_CREATE_MDL_REQ, mdlid)
		self.mdepid = mdepid
		self.conf = conf

	def encode(self):
		return MDLRequest.encode(self) + \
			struct.pack(mask2, self.mdepid, self.conf)

	@staticmethod
	def length():
		return MDLRequest.length() + CreateMDLRequest.mask2_size

	@staticmethod
	def decode(message):
		if len(message) != CreateMDLRequest.length():
			raise InvalidMessage("Invalid msg length")
		data, message = CreateMDLRequest._decode(message)
		data.extend(struct.unpack(CreateMDLRequest.mask2, message))
		return CreateMDLRequest(*data)


class ReconnectMDLRequest( MDLRequest ):

	def __init__(self, mdlid):
		MDLRequest.__init__(self, MCAP_MD_RECONNECT_MDL_REQ, mdlid)

	@staticmethod
	def decode(message):
		if len(message) != ReconnectMDLRequest.length():
			raise InvalidMessage("Invalid msg length")
		data, message = ReconnectMDLRequest._decode(message)
		return ReconnectMDLRequest(*data)


class AbortMDLRequest( MDLRequest ):

	def __init__(self, mdlid):
                MDLRequest.__init__(self, MCAP_MD_ABORT_MDL_REQ, mdlid)

	@staticmethod
	def decode(message):
		if len(message) != AbortMDLRequest.length():
			raise InvalidMessage("Invalid msg length")
		data, message = AbortMDLRequest._decode(message)
		return AbortMDLRequest(*data)


class DeleteMDLRequest( MDLRequest ):

	def __init__(self, mdlid):
                MDLRequest.__init__(self, MCAP_MD_DELETE_MDL_REQ, mdlid)

	@staticmethod
	def decode(message):
		if len(message) != DeleteMDLRequest.length():
			raise InvalidMessage("Invalid msg length")
		data, message = DeleteMDLRequest._decode(message)
		return DeleteMDLRequest(*data)


class CSPCapabilitiesRequest( CSPRequest ):
	mask2 = ">H"
	mask2_size = struct.calcsize(mask2)

	def __init__(self, reqaccuracy):
		CSPRequest.__init__(self, MCAP_MD_SYNC_CAP_REQ)
		self.reqaccuracy = reqaccuracy

	def encode(self):
		return CSPRequest.encode(self) + \
			struct.pack(mask2, self.reqaccuracy)

	@staticmethod
	def length():
		return CSPRequest.length() + mask2_size

	@staticmethod
	def decode(message):
		if len(message) != CSPCapabilitiesRequest.length():
			raise InvalidMessage("Invalid msg length")
		data, message = CSPCapabilitiesRequest._decode(message)
		data.extend(struct.unpack(mask2, message))
		return CSPCapabilitiesRequest(*data)


class CSPSetRequest( CSPRequest ):
	mask2 = ">BIQ"
	mask2_size = struct.calcsize(mask2)

	def __init__(self, update, btclock, timestamp):
		CSPRequest.__init__(self, MCAP_MD_SYNC_SET_REQ)
		self.update = update
		self.btclock = btclock
		self.timestamp = timestamp

	def encode(self):
		return CSPRequest.encode(self) + \
			struct.pack(mask2, self.update, self.btclock, self.timestamp)

	@staticmethod
	def length():
		return CSPRequest.length() + CSPSetRequest.mask2_size

	@staticmethod
	def decode(message):
		if len(message) != CSPSetRequest.length():
			raise InvalidMessage("Invalid msg length")
		data, message = CSPSetRequest._decode(message)
		data.extend(struct.unpack(mask2, message))
		return CSPSetRequest(*data)


class CSPSyncInfoIndication( CSPRequest ):
	mask2 = ">IQH"
	mask2_size = struct.calcsize(mask2)

	def __init__(self, update, btclock, timestamp, accuracy):
		CSPRequest.__init__(self, MCAP_MD_SYNC_INFO_IND)
		self.btclock = btclock
		self.timestamp = timestamp
		self.accuracy = accuracy # us

	def encode(self):
		return CSPRequest.encode(self) + \
			struct.pack(mask2, self.btclock, self.timestamp, self.accuracy)

	@staticmethod
	def length():
		return CSPRequest.length() + CSPSyncInfoIndication.mask2_size

	@staticmethod
	def decode(message):
		if len(message) != CSPSyncInfoIndication.length():
			raise InvalidMessage("Invalid msg length")
		data, message = CSPSyncInfoIndication._decode(message)
		data.extend(struct.unpack(mask2, message))
		return CSPSyncInfoIndication(*data)


# Specific response messages

class ErrorMDLResponse( MDLResponse ):

        def __init__(self):
                MDLResponse.__init__(self, MCAP_ERROR_RSP, MCAP_RSP_INVALID_OP_CODE, 0x0000)

	@staticmethod
	def decode(message):
		if len(message) != ErrorMDLResponse.length():
			raise InvalidMessage("Invalid msg length")
		data, message = ErrorMDLResponse._decode(message)
		return ErrorMDLResponse(*data)


class CreateMDLResponse( MDLResponse ):
	mask2 = ">B"
	mask2_size = struct.calcsize(mask2)

        def __init__(self, rspcode, mdlid, config):
                MDLResponse.__init__(self, MCAP_MD_CREATE_MDL_RSP, rspcode, mdlid)
                self.config = config
	
	def encode(self):
		return MDLResponse.encode(self) + \
			struct.pack(mask2, self.config)

	@staticmethod
	def length():
		return MDLResponse.length() + CreateMDLResponse.mask2_size

	@staticmethod
	def decode(message):
		if len(message) != CreateMDLResponse.length():
			raise InvalidMessage("Invalid msg length")
		data, message = CreateMDLResponse._decode(message)
		data.extend(struct.unpack(CreateMDLResponse.mask2, message))
		return CreateMDLResponse(*data)


class ReconnectMDLResponse( MDLResponse ):

        def __init__(self, rspcode, mdlid):
                MDLResponse.__init__(self, MCAP_MD_RECONNECT_MDL_RSP, rspcode, mdlid)

	@staticmethod
	def decode(message):
		if len(message) != ReconnectMDLResponse.length():
			raise InvalidMessage("Invalid msg length")
		data, message = ReconnectMDLResponse._decode(message)
		return ReconnectMDLResponse(*data)


class AbortMDLResponse( MDLResponse ):

        def __init__(self, rspcode, mdlid):
                MDLResponse.__init__(self, MCAP_MD_ABORT_MDL_RSP, rspcode, mdlid)

	@staticmethod
	def decode(message):
		if len(message) != AbortMDLResponse.length():
			raise InvalidMessage("Invalid msg length")
		data, message = AbortMDLResponse._decode(message)
		return AbortMDLResponse(*data)


class DeleteMDLResponse( MDLResponse ):

        def __init__(self, rspcode, mdlid):
                MDLResponse.__init__(self, MCAP_MD_DELETE_MDL_RSP, rspcode, mdlid)

	@staticmethod
	def decode(message):
		if len(message) != DeleteMDLResponse.length():
			raise InvalidMessage("Invalid msg length")
		data, message = DeleteMDLResponse._decode(message)
		return DeleteMDLResponse(*data)


class CSPCapabilitiesResponse( CSPResponse ):
	mask2 = ">BBHHH"
	mask2_size = struct.calcsize(mask2)

	def __init__(self, rspcode, btclockres, synclead, tmstampres,
			tmstampacc):
		CSPResponse.__init__(self, MCAP_MD_SYNC_CAP_REQ, rspcode)
		self.btclockres = btclockres # BT clock ticks
		self.synclead = synclead # delay, ms
		self.tmstampres = tmstampres # resolution, us
		self.tmstampacc = tmstampacc # accuracy, parts per million

	def encode(self):
		return CSPResponse.encode(self) + \
			struct.pack(self.mark2, self.btclockres, self.synclead,
				self.tmstampres, self.tmstampacc)

	@staticmethod
	def length():
		return CSPResponse.length() + CSPCapabilitiesResponse.mask2_size

	@staticmethod
	def decode(message):
		if len(message) != CSPCapabilitiesResponse.length():
			raise InvalidMessage("Invalid msg length")
		data, message = CSPCapabilitiesResponse._decode(message)
		data.extend(struct.unpack(CSPCapabilitiesResponse.mask2, message))
		return CSPCapabilitiesResponse(*data)


class CSPSetResponse( CSPResponse ):
	mask2 = ">BIQH"
	mask2_size = struct.calcsize(mask2)

	def __init__(self, rspcode, btclock, timestamp, tmstampacc):
		CSPResponse.__init__(self, MCAP_MD_SYNC_SET_REQ, rspcode)
		self.btclock = btclock
		self.timestamp = timestamp
		self.tmstampacc = tmstampacc # accuracy, us

	def encode(self):
		return CSPResponse.encode(self) + \
			struct.pack(self.mask2, self.btclock, self.timestamp, self.tmstampacc)
	
	@staticmethod
	def length():
		return CSPResponse.length() + CSPSetResponse.mask2_size

	@staticmethod
	def decode(message):
		if len(message) != CSPSetResponse.length():
			raise InvalidMessage("Invalid msg length")
		data, message = CSPSetResponse._decode(message)
		data.extend(struct.unpack(CSPSetResponse.mask2, message))
		return CSPSetResponse(*data)


class MessageParser:
	known_opcodes = { \
		MCAP_MD_CREATE_MDL_REQ: CreateMDLRequest,
		MCAP_MD_RECONNECT_MDL_REQ: ReconnectMDLRequest,
		MCAP_MD_ABORT_MDL_REQ: AbortMDLRequest,
		MCAP_MD_DELETE_MDL_REQ: DeleteMDLRequest,
		MCAP_MD_SYNC_CAP_REQ: CSPCapabilitiesRequest,
		MCAP_MD_SYNC_SET_REQ: CSPSetRequest,
		MCAP_MD_SYNC_INFO_IND: CSPSyncInfoIndication,
		MCAP_ERROR_RSP:	ErrorMDLResponse,
               	MCAP_MD_CREATE_MDL_RSP: CreateMDLResponse,
               	MCAP_MD_RECONNECT_MDL_RSP: ReconnectMDLResponse,
               	MCAP_MD_ABORT_MDL_RSP: AbortMDLResponse,
               	MCAP_MD_DELETE_MDL_RSP: DeleteMDLResponse,
		MCAP_MD_SYNC_CAP_RSP: CSPCapabilitiesResponse,
		MCAP_MD_SYNC_SET_RSP: CSPSetResponse }

	def __init__(self):
		pass

	def get_opcode(self, message):
		if len(message) < 1:
			raise InvalidMessage("Empty message")
		return struct.unpack("B", message[0])[0]

	def parse(self, message):
                opcode = self.get_opcode(message)
		if opcode not in self.known_opcodes:
			raise InvalidMessage("Bad message opcode: %d" % opcode)
		k = self.known_opcodes[opcode]
		o = k.decode(message)
		return o


def testmsg(hexmsg):
	binmsg = [ chr(int(hexmsg[i:i+2], 16)) for i in range(0, len(hexmsg), 2) ]
	return "".join(binmsg)


def test():
	createReq = CreateMDLRequest(0x01, 0x01, 0x0001)
	assert(createReq.mdlid == 0x01)
	assert(createReq.mdepid == 0x01)
	assert(createReq.opcode == MCAP_MD_CREATE_MDL_REQ)

	reconnectReq = ReconnectMDLRequest(0x01)
	assert(reconnectReq.mdlid == 0x01)
	assert(reconnectReq.opcode == MCAP_MD_RECONNECT_MDL_REQ)

	deleteReq = DeleteMDLRequest(0x02)
	assert(deleteReq.mdlid == 0x02)
	assert(deleteReq.opcode == MCAP_MD_DELETE_MDL_REQ)

	abortReq = AbortMDLRequest(0x03)
	assert(abortReq.mdlid == 0x03)
	assert(abortReq.opcode == MCAP_MD_ABORT_MDL_REQ)

	# TEST PARSER

	parser = MessageParser()
	
	# test CreateReq message parsing
	createReq = testmsg("0100230ABC")
	createReqObj = parser.parse(createReq)
	assert(createReqObj.opcode == MCAP_MD_CREATE_MDL_REQ)
	assert(createReqObj.mdlid == 0x0023)
	assert(createReqObj.mdepid == 0x0A)
	assert(createReqObj.conf == 0xBC)
	
	
	# test ReconnectReq message parsing
	reconnectReq = testmsg("0300AB")
	reconnectReqObj = parser.parse(reconnectReq)
	assert(reconnectReqObj.opcode == MCAP_MD_RECONNECT_MDL_REQ)
	assert(reconnectReqObj.mdlid == 0x00AB)
	
	
	# test AbortReq message parsing
	abortReq = testmsg("0500AB")
	abortReqObj = parser.parse(abortReq)
	assert(abortReqObj.opcode == MCAP_MD_ABORT_MDL_REQ)
	assert(abortReqObj.mdlid == 0x00AB)
	
	
	# test DeleteReq message parsing
	deleteReq = testmsg("0700CC")
	deleteReqObj = parser.parse(deleteReq)
	assert(deleteReqObj.opcode == MCAP_MD_DELETE_MDL_REQ)
	assert(deleteReqObj.mdlid == 0x00CC)
	
	
	# test CreateRsp message parsing
	createRsp = testmsg("0200002307")
	createRspObj = parser.parse(createRsp)
	assert(createRspObj.opcode == MCAP_MD_CREATE_MDL_RSP)
	assert(createRspObj.mdlid == 0x0023)
	assert(createRspObj.rspcode == MCAP_RSP_SUCCESS)
	assert(createRspObj.config == 0x07)
	
	
	# test ReconnectRsp message parsing
	reconnectRsp = testmsg("040200AB")
	reconnectRspObj = parser.parse(reconnectRsp)
	assert(reconnectRspObj.opcode == MCAP_MD_RECONNECT_MDL_RSP)
	assert(reconnectRspObj.mdlid == 0x00AB)
	assert(reconnectRspObj.rspcode == MCAP_RSP_INVALID_PARAMETER_VALUE)
	
	
	# test AbortRsp message parsing
	abortRsp = testmsg("0605FFFF")
	abortRspObj = parser.parse(abortRsp)
	assert(abortRspObj.opcode == MCAP_MD_ABORT_MDL_RSP)
	assert(abortRspObj.mdlid == 0xFFFF)
	assert(abortRspObj.rspcode == MCAP_RSP_INVALID_MDL)
	

	# test DeleteRsp message parsing
	deleteRsp = testmsg("080000CC")
	deleteRspObj = parser.parse(deleteRsp)
	assert(deleteRspObj.opcode == MCAP_MD_DELETE_MDL_RSP)
	assert(deleteRspObj.mdlid == 0x00CC)
	assert(deleteRspObj.rspcode == MCAP_RSP_SUCCESS)


	exc = None
	try:
		parser.parse(testmsg("8B003344"))
	except Exception, e:
		exc = e
	assert(isinstance(exc, InvalidMessage))
	
	exc = None
	try:
		parser.parse(testmsg("01"))
	except Exception, e:
		exc = e
	assert(isinstance(exc, InvalidMessage))

	exc = None
	try:
		parser.parse("")
	except Exception, e:
		exc = e
	assert(isinstance(exc, InvalidMessage))

	print "TESTS OK"

if __name__ == "__main__":
	test()
