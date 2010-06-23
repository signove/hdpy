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

MCAP_MD_SYNC_MIN = MCAP_MD_SYNC_CAP_REQ
MCAP_MD_SYNC_MAX = MCAP_MD_SYNC_INFO_IND

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

# State
MCAP_MCL_ROLE_ACCEPTOR		= 'ACCEPTOR'
MCAP_MCL_ROLE_INITIATOR		= 'INITIATOR'  

MCAP_MCL_STATE_IDLE		= 'IDLE'
MCAP_MCL_STATE_CONNECTED	= 'CONNECTED'
MCAP_MCL_STATE_PENDING		= 'PENDING'
MCAP_MCL_STATE_ACTIVE		= 'ACTIVE'

MCAP_MDL_STATE_CLOSED		= 'CLOSED'
MCAP_MDL_STATE_LISTENING	= 'LISTENING'
MCAP_MDL_STATE_ACTIVE		= 'ACTIVE'
MCAP_MDL_STATE_CLOSED		= 'CLOSED'
MCAP_MDL_STATE_DELETED		= 'DELETED'

# CSP and Bluetooth clock special values

btclock_immediate = 0xffffffff
tmstamp_dontset   = 0xffffffffffffffff
btclock_max       = 0xfffffff

# Verbose error messages

error_rsp_messages = { 
	MCAP_RSP_INVALID_OP_CODE:		"Invalid Op Code",
	MCAP_RSP_INVALID_PARAMETER_VALUE:	"Invalid Parameter Value",
	MCAP_RSP_INVALID_MDEP:			"Invalid MDEP",
	MCAP_RSP_MDEP_BUSY:			"MDEP Busy",
	MCAP_RSP_INVALID_MDL:			"Invalid MDL",
	MCAP_RSP_MDL_BUSY:			"MDL Busy",
	MCAP_RSP_INVALID_OPERATION:		"Invalid Operation",
	MCAP_RSP_RESOURCE_UNAVAILABLE:		"Resource Unavailable",
	MCAP_RSP_UNSPECIFIED_ERROR:		"Unspecified Error",
	MCAP_RSP_REQUEST_NOT_SUPPORTED:		"Request Not Supported",
	MCAP_RSP_CONFIGURATION_REJECTED:	"Configuration Rejected",
	}

# Error exceptions

class InvalidMessage(Exception):
	pass

class InvalidResponse(Exception):
	pass

# General messages

class RawRequest(object):
	''' This class is for error injection purposes only '''

	def __init__(self, *b):
		self.raw = "".join([chr(x) for x in b])
		self.opcode = b[0]

	def encode(self):
		return self.raw


class MDLRequest(object):
	mask1 = ">BH"
	mask1_size = struct.calcsize(mask1)

	def __init__(self, opcode, mdlid):
		self.opcode = opcode
		self.mdlid = mdlid

	def encode(self):
		return struct.pack(self.mask1, self.opcode, self.mdlid)

	@staticmethod
	def length(rspcode):
		return MDLRequest.mask1_size

	@staticmethod
	def _decode(message):
		data = struct.unpack(MDLRequest.mask1, message[0:MDLRequest.mask1_size])
		return list(data[1:]), message[MDLRequest.mask1_size:]


class MDLResponse(object):
	mask1 = ">BBH"
	mask1_size = struct.calcsize(mask1)

	def __init__(self, opcode, rspcode, mdlid):
		self.opcode = opcode
		self.rspcode = rspcode
		self.mdlid = mdlid

	def encode(self):
		return struct.pack(self.mask1, self.opcode, self.rspcode, self.mdlid)

	@staticmethod
	def length(rspcode):
		return MDLResponse.mask1_size

	@staticmethod
	def _decode(message):
		data = struct.unpack(MDLResponse.mask1, message[0:MDLResponse.mask1_size])
		return list(data[1:]), message[MDLResponse.mask1_size:]


class CSPRequest(object):
	mask1 = ">B"
	mask1_size = struct.calcsize(mask1)

	def __init__(self, opcode):
		self.opcode = opcode

	def encode(self):
		return struct.pack(self.mask1, self.opcode)

	@staticmethod
	def length(rspcode):
		return CSPRequest.mask1_size

	@staticmethod
	def _decode(message):
		data = struct.unpack(CSPRequest.mask1,
					message[0:CSPRequest.mask1_size])
		return list(data[1:]), message[CSPRequest.mask1_size:]


class CSPResponse(object):
	mask1 = ">BB"
	mask1_size = struct.calcsize(mask1)

	def __init__(self, opcode, rspcode):
		self.opcode = opcode
		self.rspcode = rspcode

	def encode(self):
		return struct.pack(self.mask1, self.opcode, self.rspcode)

	@staticmethod
	def length(rspcode):
		return CSPResponse.mask1_size

	@staticmethod
	def _decode(message):
		data = struct.unpack(CSPResponse.mask1,
					message[0:CSPResponse.mask1_size])
		return list(data[1:]), message[CSPResponse.mask1_size:]


# Specific request messages

class CreateMDLRequest( MDLRequest ):
	mask2 = ">BB"
	mask2_size = struct.calcsize(mask2)

	def __init__(self, mdlid, mdepid, config):
		MDLRequest.__init__(self, MCAP_MD_CREATE_MDL_REQ, mdlid)
		self.mdepid = mdepid
		self.config = config

	def encode(self):
		return MDLRequest.encode(self) + \
			struct.pack(self.mask2, self.mdepid, self.config)

	@staticmethod
	def length(rspcode):
		return MDLRequest.length(rspcode) + CreateMDLRequest.mask2_size

	@staticmethod
	def decode(message, rspcode):
		if len(message) != CreateMDLRequest.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = CreateMDLRequest._decode(message)
		data.extend(struct.unpack(CreateMDLRequest.mask2, message))
		return CreateMDLRequest(*data)


class ReconnectMDLRequest( MDLRequest ):

	def __init__(self, mdlid):
		MDLRequest.__init__(self, MCAP_MD_RECONNECT_MDL_REQ, mdlid)

	@staticmethod
	def decode(message, rspcode):
		if len(message) != ReconnectMDLRequest.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = ReconnectMDLRequest._decode(message)
		return ReconnectMDLRequest(*data)


class AbortMDLRequest( MDLRequest ):

	def __init__(self, mdlid):
                MDLRequest.__init__(self, MCAP_MD_ABORT_MDL_REQ, mdlid)

	@staticmethod
	def decode(message, rspcode):
		if len(message) != AbortMDLRequest.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = AbortMDLRequest._decode(message)
		return AbortMDLRequest(*data)


class DeleteMDLRequest( MDLRequest ):

	def __init__(self, mdlid):
                MDLRequest.__init__(self, MCAP_MD_DELETE_MDL_REQ, mdlid)

	@staticmethod
	def decode(message, rspcode):
		if len(message) != DeleteMDLRequest.length(rspcode):
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
			struct.pack(self.mask2, self.reqaccuracy)

	@staticmethod
	def length(rspcode):
		return CSPRequest.length(rspcode) + CSPCapabilitiesRequest.mask2_size

	@staticmethod
	def decode(message, rspcode):
		if len(message) != CSPCapabilitiesRequest.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = CSPCapabilitiesRequest._decode(message)
		data.extend(struct.unpack(CSPCapabilitiesRequest.mask2, message))
		return CSPCapabilitiesRequest(*data)


class CSPSetRequest( CSPRequest ):
	mask2 = ">BIQ"
	mask2_size = struct.calcsize(mask2)

	def __init__(self, update, btclock, timestamp):
		CSPRequest.__init__(self, MCAP_MD_SYNC_SET_REQ)

		# Some coercions
		if update:
			update = 1
		else:
			update = 0

		if btclock is None:
			btclock = btclock_immediate

		if timestamp is None:
			timestamp = tmstamp_dontset

		self.update = update
		self.btclock = btclock
		self.timestamp = timestamp

	def encode(self):
		return CSPRequest.encode(self) + \
			struct.pack(self.mask2, self.update, self.btclock, self.timestamp)

	@staticmethod
	def length(rspcode):
		return CSPRequest.length(rspcode) + CSPSetRequest.mask2_size

	@staticmethod
	def decode(message, rspcode):
		if len(message) != CSPSetRequest.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = CSPSetRequest._decode(message)
		data.extend(struct.unpack(CSPSetRequest.mask2, message))
		return CSPSetRequest(*data)


class CSPInfoIndication( CSPRequest ):
	mask2 = ">IQH"
	mask2_size = struct.calcsize(mask2)

	def __init__(self, btclock, timestamp, accuracy):
		CSPRequest.__init__(self, MCAP_MD_SYNC_INFO_IND)
		self.btclock = btclock
		self.timestamp = timestamp
		self.accuracy = accuracy # us

	def encode(self):
		return CSPRequest.encode(self) + \
			struct.pack(self.mask2, self.btclock, self.timestamp, self.accuracy)

	@staticmethod
	def length(rspcode):
		return CSPRequest.length(rspcode) + CSPInfoIndication.mask2_size

	@staticmethod
	def decode(message, rspcode):
		if len(message) != CSPInfoIndication.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = CSPInfoIndication._decode(message)
		data.extend(struct.unpack(CSPInfoIndication.mask2, message))
		return CSPInfoIndication(*data)


# Specific response messages

class ErrorMDLResponse( MDLResponse ):

        def __init__(self, errcode=MCAP_RSP_INVALID_OP_CODE, mdlid=0x0000):
                MDLResponse.__init__(self, MCAP_ERROR_RSP, errcode, mdlid)

	@staticmethod
	def decode(message, rspcode):
		if len(message) != ErrorMDLResponse.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = ErrorMDLResponse._decode(message)
		return ErrorMDLResponse(*data)


class CreateMDLResponse( MDLResponse ):
	mask2 = ">B"
	mask2_size = struct.calcsize(mask2)

        def __init__(self, rspcode, mdlid, config):
		if not self.is_valid_response(rspcode):
			raise InvalidResponse("%d" % rspcode)
                MDLResponse.__init__(self, MCAP_MD_CREATE_MDL_RSP, rspcode, mdlid)
                self.config = config
	
	def encode(self):
		s = MDLResponse.encode(self)
		if not self.rspcode:
			s += struct.pack(self.mask2, self.config)
		return s

	@staticmethod
	def length(rspcode):
		l = MDLResponse.length(rspcode)
		if not rspcode:
			l += CreateMDLResponse.mask2_size
		return l

	@staticmethod
	def decode(message, rspcode):
		if len(message) != CreateMDLResponse.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = CreateMDLResponse._decode(message)
		if not rspcode:
			data.extend(struct.unpack(CreateMDLResponse.mask2, message))
		else:
			# warning: hardcoded list with same length as mask2
			data.extend([0])
		return CreateMDLResponse(*data)

	@staticmethod
	def is_valid_response(rspcode):
		return rspcode in [ \
			MCAP_RSP_SUCCESS,
			MCAP_RSP_INVALID_PARAMETER_VALUE,
			MCAP_RSP_INVALID_MDEP,
			MCAP_RSP_MDEP_BUSY,
			MCAP_RSP_INVALID_MDL,
			MCAP_RSP_MDL_BUSY,
			MCAP_RSP_INVALID_OPERATION,
			MCAP_RSP_RESOURCE_UNAVAILABLE,
			MCAP_RSP_UNSPECIFIED_ERROR,
			MCAP_RSP_REQUEST_NOT_SUPPORTED,
			MCAP_RSP_CONFIGURATION_REJECTED]

class ReconnectMDLResponse( MDLResponse ):

        def __init__(self, rspcode, mdlid):
		if not self.is_valid_response(rspcode):
			raise InvalidResponse("%d" % rspcode)
                MDLResponse.__init__(self, MCAP_MD_RECONNECT_MDL_RSP, rspcode, mdlid)

	@staticmethod
	def decode(message, rspcode):
		if len(message) != ReconnectMDLResponse.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = ReconnectMDLResponse._decode(message)
		return ReconnectMDLResponse(*data)

	@staticmethod
        def is_valid_response(_rspcode):
                return _rspcode in [ \
			MCAP_RSP_SUCCESS,
			MCAP_RSP_INVALID_PARAMETER_VALUE,
			MCAP_RSP_MDEP_BUSY,
			MCAP_RSP_INVALID_MDL,
			MCAP_RSP_MDL_BUSY,
			MCAP_RSP_INVALID_OPERATION,
			MCAP_RSP_RESOURCE_UNAVAILABLE,
			MCAP_RSP_UNSPECIFIED_ERROR, 
			MCAP_RSP_REQUEST_NOT_SUPPORTED]


class AbortMDLResponse( MDLResponse ):

        def __init__(self, rspcode, mdlid):
		if not self.is_valid_response(rspcode):
			raise InvalidResponse("%d" % rspcode)
                MDLResponse.__init__(self, MCAP_MD_ABORT_MDL_RSP, rspcode, mdlid)

	@staticmethod
	def decode(message, rspcode):
		if len(message) != AbortMDLResponse.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = AbortMDLResponse._decode(message)
		return AbortMDLResponse(*data)

	@staticmethod
        def is_valid_response(_rspcode):
                return _rspcode in [ \
			MCAP_RSP_SUCCESS,
			MCAP_RSP_INVALID_PARAMETER_VALUE,
			MCAP_RSP_INVALID_MDL,
			MCAP_RSP_INVALID_OPERATION,
			MCAP_RSP_UNSPECIFIED_ERROR,
			MCAP_RSP_REQUEST_NOT_SUPPORTED ]


class DeleteMDLResponse( MDLResponse ):

        def __init__(self, rspcode, mdlid):
		if not self.is_valid_response(rspcode):
			raise InvalidResponse("%d" % rspcode)
                MDLResponse.__init__(self, MCAP_MD_DELETE_MDL_RSP, rspcode, mdlid)

	@staticmethod
	def decode(message, rspcode):
		if len(message) != DeleteMDLResponse.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = DeleteMDLResponse._decode(message)
		return DeleteMDLResponse(*data)

	@staticmethod
        def is_valid_response(_rspcode):
                return _rspcode in [ \
			MCAP_RSP_SUCCESS,
			MCAP_RSP_INVALID_PARAMETER_VALUE,
			MCAP_RSP_INVALID_MDL,
			MCAP_RSP_MDL_BUSY,
			MCAP_RSP_INVALID_OPERATION,
			MCAP_RSP_UNSPECIFIED_ERROR, 
			MCAP_RSP_REQUEST_NOT_SUPPORTED]


class CSPCapabilitiesResponse( CSPResponse ):
	mask2 = ">BHHH"
	mask2_size = struct.calcsize(mask2)
	# CSP responses don't change length even in case of error

	def __init__(self, rspcode, btclockres, synclead, tmstampres,
			tmstampacc):
		CSPResponse.__init__(self, MCAP_MD_SYNC_CAP_RSP, rspcode)
		self.btclockres = btclockres # BT clock ticks
		self.synclead = synclead # delay, ms
		self.tmstampres = tmstampres # resolution, us
		self.tmstampacc = tmstampacc # accuracy, parts per million

	def encode(self):
		return CSPResponse.encode(self) + \
			struct.pack(self.mask2, self.btclockres, self.synclead,
				self.tmstampres, self.tmstampacc)

	@staticmethod
	def length(rspcode):
		return CSPResponse.length(rspcode) + CSPCapabilitiesResponse.mask2_size

	@staticmethod
	def decode(message, rspcode):
		if len(message) != CSPCapabilitiesResponse.length(rspcode):
			raise InvalidMessage("Invalid msg length")
		data, message = CSPCapabilitiesResponse._decode(message)
		data.extend(struct.unpack(CSPCapabilitiesResponse.mask2, message))
		return CSPCapabilitiesResponse(*data)


class CSPSetResponse( CSPResponse ):
	mask2 = ">IQH"
	mask2_size = struct.calcsize(mask2)
	# CSP responses don't change length even in case of error

	def __init__(self, rspcode, btclock, timestamp, tmstampacc):
		CSPResponse.__init__(self, MCAP_MD_SYNC_SET_RSP, rspcode)
		self.btclock = btclock
		self.timestamp = timestamp
		self.tmstampacc = tmstampacc # accuracy, us

	def encode(self):
		return CSPResponse.encode(self) + \
			struct.pack(self.mask2, self.btclock, self.timestamp,
				self.tmstampacc)
	
	@staticmethod
	def length(rspcode):
		return CSPResponse.length(rspcode) + CSPSetResponse.mask2_size

	@staticmethod
	def decode(message, rspcode):
		if len(message) != CSPSetResponse.length(rspcode):
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
		MCAP_MD_SYNC_INFO_IND: CSPInfoIndication,
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

		opcode = ord(message[0])
		rspcode = 0

		if opcode not in self.known_opcodes:
			raise InvalidMessage("Unknown opcode %d" % opcode)

		if opcode % 2 == 0:
			if len(message) < 2:
				raise InvalidMessage("Incomplete response")
			rspcode = ord(message[1])

		return opcode, rspcode

	def parse(self, message):
                opcode, rspcode = self.get_opcode(message)
		k = self.known_opcodes[opcode]
		o = k.decode(message, rspcode)
		return o


def testmsg(hexmsg):
	binmsg = [ chr(int(hexmsg[i:i+2], 16)) for i in range(0, len(hexmsg), 2) ]
	return "".join(binmsg)


def test():
	msg = CreateMDLRequest(0x01, 0x01, 0x0001)
	assert(msg.mdlid == 0x01)
	assert(msg.mdepid == 0x01)
	assert(msg.opcode == MCAP_MD_CREATE_MDL_REQ)

	msg = ReconnectMDLRequest(0x01)
	assert(msg.mdlid == 0x01)
	assert(msg.opcode == MCAP_MD_RECONNECT_MDL_REQ)

	msg = DeleteMDLRequest(0x02)
	assert(msg.mdlid == 0x02)
	assert(msg.opcode == MCAP_MD_DELETE_MDL_REQ)

	msg = AbortMDLRequest(0x03)
	assert(msg.mdlid == 0x03)
	assert(msg.opcode == MCAP_MD_ABORT_MDL_REQ)

	# TEST PARSER

	parser = MessageParser()
	
	# test CreateReq message parsing
	msg = testmsg("0100230ABC")
	msgObj = parser.parse(msg)
	assert(msgObj.opcode == MCAP_MD_CREATE_MDL_REQ)
	assert(msgObj.mdlid == 0x0023)
	assert(msgObj.mdepid == 0x0A)
	assert(msgObj.config == 0xBC)
	assert(msgObj.encode() == msg)
	
	
	# test ReconnectReq message parsing
	msg = testmsg("0300AB")
	msgObj = parser.parse(msg)
	assert(msgObj.opcode == MCAP_MD_RECONNECT_MDL_REQ)
	assert(msgObj.mdlid == 0x00AB)
	assert(msgObj.encode() == msg)
	
	
	# test AbortReq message parsing
	msg = testmsg("0500AB")
	msgObj = parser.parse(msg)
	assert(msgObj.opcode == MCAP_MD_ABORT_MDL_REQ)
	assert(msgObj.mdlid == 0x00AB)
	assert(msgObj.encode() == msg)
	
	
	# test DeleteReq message parsing
	msg = testmsg("0700CC")
	msgObj = parser.parse(msg)
	assert(msgObj.opcode == MCAP_MD_DELETE_MDL_REQ)
	assert(msgObj.mdlid == 0x00CC)
	assert(msgObj.encode() == msg)
	

	# test CreateRsp message parsing
	msg = testmsg("0200002307")
	msgObj = parser.parse(msg)
	assert(msgObj.opcode == MCAP_MD_CREATE_MDL_RSP)
	assert(msgObj.mdlid == 0x0023)
	assert(msgObj.rspcode == MCAP_RSP_SUCCESS)
	assert(msgObj.config == 0x07)
	assert(msgObj.encode() == msg)
	
	# test CreateRsp message parsing
	msg = testmsg("02050023")
	msgObj = parser.parse(msg)
	assert(msgObj.opcode == MCAP_MD_CREATE_MDL_RSP)
	assert(msgObj.mdlid == 0x0023)
	assert(msgObj.rspcode == MCAP_RSP_INVALID_MDL)
	assert(msgObj.config == 0x00)
	assert(msgObj.encode() == msg)
	
	
	# test ReconnectRsp message parsing
	msg = testmsg("040200AB")
	msgObj = parser.parse(msg)
	assert(msgObj.opcode == MCAP_MD_RECONNECT_MDL_RSP)
	assert(msgObj.mdlid == 0x00AB)
	assert(msgObj.rspcode == MCAP_RSP_INVALID_PARAMETER_VALUE)
	assert(msgObj.encode() == msg)
	
	
	# test AbortRsp message parsing
	msg = testmsg("0605FFFF")
	msgObj = parser.parse(msg)
	assert(msgObj.opcode == MCAP_MD_ABORT_MDL_RSP)
	assert(msgObj.mdlid == 0xFFFF)
	assert(msgObj.rspcode == MCAP_RSP_INVALID_MDL)
	assert(msgObj.encode() == msg)
	

	# test DeleteRsp message parsing
	msg = testmsg("080000CC")
	msgObj = parser.parse(msg)
	assert(msgObj.opcode == MCAP_MD_DELETE_MDL_RSP)
	assert(msgObj.mdlid == 0x00CC)
	assert(msgObj.rspcode == MCAP_RSP_SUCCESS)
	assert(msgObj.encode() == msg)


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
