#!/usr/bin/env python

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

class InvalidMessageError( Exception ):

	def __init__(self, value):
		self.value = value

	def __str__(self):
		return repr(self.value)

class InvalidOperationError( Exception ) :

	def __init__(self, value):
                self.value = value

        def __str__(self):
                return repr(self.value)

# General messages

class MDLRequestMessage:

	def __init__(self, _opcode, _mdlid):
		self.opcode = _opcode
		self.mdlid = _mdlid

	def __repr__(self):
		return "0x%02X%04X" % (self.opcode,self.mdlid)  

class MDLResponseMessage:

	def __init__(self, _opcode, _rspcode, _mdlid):
		self.opcode = _opcode
		self.rspcode = _rspcode
		self.mdlid = _mdlid

	def __repr__(self):
		return "0x%02X%02X%04X" % (self.opcode,self.rspcode,self.mdlid)

class CSPRequestMessage:

	def __init__(self, _opcode):
		self.opcode = _opcode

	def __repr__(self):
		return "0x%02x" % (self.opcode)  

class CSPResponseMessage:

	def __init__(self, _opcode, _rspcode):
		self.opcode = _opcode
		self.rspcode = _rspcode

	def __repr__(self):
		return "0x%02X%02X" % (self.opcode, self.rspcode)

# Specific request messages

class CreateMDLRequestMessage( MDLRequestMessage ):

	def __init__(self, _mdlid, _mdepid, _conf):
		MDLRequestMessage.__init__(self, MCAP_MD_CREATE_MDL_REQ, _mdlid)
		self.mdepid = _mdepid
		self.conf = _conf

	def __repr__(self):
		return "0x%02X%04X%02X%02X" % (self.opcode,self.mdlid,self.mdepid,self.conf)


class ReconnectMDLRequestMessage( MDLRequestMessage ):

	def __init__(self, _mdlid):
		MDLRequestMessage.__init__(self, MCAP_MD_RECONNECT_MDL_REQ, _mdlid)


class AbortMDLRequestMessage( MDLRequestMessage ):

	def __init__(self, _mdlid):
                MDLRequestMessage.__init__(self, MCAP_MD_ABORT_MDL_REQ, _mdlid)


class DeleteMDLRequestMessage( MDLRequestMessage ):

	def __init__(self, _mdlid):
                MDLRequestMessage.__init__(self, MCAP_MD_DELETE_MDL_REQ, _mdlid)


class CSPCapabilitiesRequestMessage( CSPRequestMessage ):

	def __init__(self, _reqaccuracy):
		CSPRequestMessage.__init__(self, MCAP_MD_SYNC_CAP_REQ)
		self.reqaccuracy = _reqaccuracy

	def __repr__(self):
		return "0x%02X %d" % (self.opcode, self.reqaccuracy)


class CSPSetRequestMessage( CSPRequestMessage ):

	def __init__(self, _update, _btclock, _timestamp):
		CSPRequestMessage.__init__(self, MCAP_MD_SYNC_SET_REQ)
		self.btclock = _btclock
		self.timestamp = _timestamp

	def __repr__(self):
		return "0x%02X %d %d" % (self.opcode, self.btclock,
			self.timestamp)


class CSPSyncInfoIndication( CSPRequestMessage ):

	def __init__(self, _update, _btclock, _timestamp, _accuracy):
		CSPRequestMessage.__init__(self, MCAP_MD_SYNC_INFO_IND)
		self.btclock = _btclock
		self.timestamp = _timestamp
		self.accuracy = _accuracy # us

	def __repr__(self):
		return "0x%02X %d %d %d" % (self.opcode, self.btclock,
			self.timestamp, self.accuracy)


# Specific response messages


class ErrorMDLResponseMessage( MDLResponseMessage ):

        def __init__(self):
                MDLResponseMessage.__init__(self, MCAP_ERROR_RSP, MCAP_RSP_INVALID_OP_CODE, 0x0000)

class CreateMDLResponseMessage( MDLResponseMessage ):

        def __init__(self, _rspcode, _mdlid, _params):
                MDLResponseMessage.__init__(self, MCAP_MD_CREATE_MDL_RSP, _rspcode, _mdlid)
                self.params = _params
	
	def __repr__(self):
		return "0x%02X%02X%04X%02X" % (self.opcode,self.rspcode,self.mdlid,self.params)

	@staticmethod
	def is_valid_response(_rspcode):
		return _rspcode in [MCAP_RSP_SUCESS, MCAP_RSP_INVALID_PARAMETER_VALUE,
                                    MCAP_RSP_INVALID_MDEP, MCAP_RSP_MDEP_BUSY,
                                    MCAP_RSP_INVALID_MDL, MCAP_RSP_MDL_BUSY,
                                    MCAP_RSP_INVALID_OPERATION, MCAP_RSP_RESOURCE_UNAVAILABLE,
                                    MCAP_RSP_UNSPECIFIED_ERROR, MCAP_RSP_REQUEST_NOT_SUPPORTED,
                                    MCAP_RSP_CONFIGURATION_REJECTED]


class ReconnectMDLResponseMessage( MDLResponseMessage ):

        def __init__(self, _rspcode, _mdlid):
                MDLResponseMessage.__init__(self, MCAP_MD_RECONNECT_MDL_RSP, _rspcode, _mdlid)

	@staticmethod
        def is_valid_response(_rspcode):
                return _rspcode in [MCAP_RSP_SUCESS, MCAP_RSP_INVALID_PARAMETER_VALUE,
                                    MCAP_RSP_MDEP_BUSY, MCAP_RSP_INVALID_MDL,
                                    MCAP_RSP_MDL_BUSY, MCAP_RSP_INVALID_OPERATION,
                                    MCAP_RSP_RESOURCE_UNAVAILABLE, MCAP_RSP_UNSPECIFIED_ERROR, 
                                    MCAP_RSP_REQUEST_NOT_SUPPORTED]

class AbortMDLResponseMessage( MDLResponseMessage ):

        def __init__(self, _rspcode, _mdlid):
                MDLResponseMessage.__init__(self, MCAP_MD_ABORT_MDL_RSP, _rspcode, _mdlid)

	@staticmethod
        def is_valid_response(_rspcode):
                return _rspcode in [MCAP_RSP_SUCESS, MCAP_RSP_INVALID_PARAMETER_VALUE,
                                    MCAP_RSP_INVALID_MDL, MCAP_RSP_INVALID_OPERATION,
                                    MCAP_RSP_UNSPECIFIED_ERROR, MCAP_RSP_REQUEST_NOT_SUPPORTED]

class DeleteMDLResponseMessage( MDLResponseMessage ):

        def __init__(self, _rspcode, _mdlid):
                MDLResponseMessage.__init__(self, MCAP_MD_DELETE_MDL_RSP, _rspcode, _mdlid)

	@staticmethod
        def is_valid_response(_rspcode):
                return _rspcode in [MCAP_RSP_SUCESS, MCAP_RSP_INVALID_PARAMETER_VALUE,
                                    MCAP_RSP_INVALID_MDL, MCAP_RSP_MDL_BUSY,
				    MCAP_RSP_INVALID_OPERATION, MCAP_RSP_UNSPECIFIED_ERROR, 
				    MCAP_RSP_REQUEST_NOT_SUPPORTED]


class CSPCapabilitiesResponseMessage( CSPResponseMessage ):

	def __init__(self, _rspcode, _btclockres, _synclead, _tmstampres,
			_tmstampacc):
		CSPResponseMessage.__init__(self, MCAP_MD_SYNC_CAP_REQ, _rspcode)
		self.btclockres = _btclockres # BT clock ticks
		self.synclead = _synclead # delay, ms
		self.tmstampres = _tmstampres # resolution, us
		self.tmstampacc = _tmstampacc # accuracy, parts per million

	def __repr__(self):
		return "0x%02X%02X %d %d %d %d" % (self.opcode, self.rspcode,
			self.btclockres, self.synclead, self.tmstampres,
			self.tmstampacc)


class CSPSetResponseMessage( CSPResponseMessage ):

	def __init__(self, _rspcode, _btclock, _timestamp, _tmstampacc):
		CSPResponseMessage.__init__(self, MCAP_MD_SYNC_SET_REQ, _rspcode)
		self.btclock = _btclock
		self.timestamp = _timestamp
		self.tmstampacc = _tmstampacc # accuracy, us

	def __repr__(self):
		return "0x%02X 0x%02X %d %d %d" % (self.opcode, self.rspcode,
			self.btclock, self.timestamp, self.tmstampacc)

	
class MessageParser:

	def __init__(self):
		pass

	def get_op_code(self, _message):
		temp = _message

                # MCAP request/response packages do not have a fix lenght. 
                # Op codes are on most significant byte
                while(temp > 0):
                        op_code = temp & 0xFF
                        temp >>= 8

		# check if is ERROR_RSP - special case
		# it stops at RSP_CODE, which, in ERROR_RSP is always 0x01
		if ( op_code == 0x01 ):
			if ( ( _message & 0xFFFFFFFF) == 0x00010000 ):
				return MCAP_ERROR_RSP 

                return op_code

	def is_request_message(self, _opcode):
		return _opcode in [MCAP_MD_CREATE_MDL_REQ, MCAP_MD_RECONNECT_MDL_REQ,
				   MCAP_MD_ABORT_MDL_REQ, MCAP_MD_DELETE_MDL_REQ,
				   MCAP_MD_SYNC_CAP_REQ, MCAP_MD_SYNC_SET_REQ,
				   MCAP_MD_SYNC_INFO_IND]
	
	def is_response_message(self, _opcode):
		return _opcode in [MCAP_ERROR_RSP, MCAP_MD_CREATE_MDL_RSP,
				   MCAP_MD_RECONNECT_MDL_RSP, 
				   MCAP_MD_ABORT_MDL_RSP,
				   MCAP_MD_DELETE_MDL_RSP,
				   MCAP_MD_SYNC_CAP_RSP,
				   MCAP_MD_SYNC_SET_RSP]


	def parse_request_message(self, _message):
		opcode = self.get_op_code(_message)

		if opcode == MCAP_MD_CREATE_MDL_REQ:
			return self.parse_create_request_message(_message)
		elif opcode == MCAP_MD_SYNC_CAP_REQ:
			return self.parse_csp_capabilites_request(_message)
		elif opcode == MCAP_MD_SYNC_SET_REQ:
			return self.parse_csp_set_request(_message)
		elif opcode == MCAP_MD_SYNC_INFO_IND:
			return self.parse_csp_info_indication(_message)
		else:
			return self.parse_non_create_request_message(_message)

	def parse_response_message(self, _message):
                opcode = self.get_op_code(_message)

                if opcode == MCAP_MD_CREATE_MDL_RSP:
                        return self.parse_create_response_message(_message)
		elif opcode == MCAP_MD_SYNC_CAP_RSP:
			return self.parse_csp_capabilites_response(_message)
		elif opcode == MCAP_MD_SYNC_SET_RSP:
			return self.parse_csp_set_response(_message)
                else:
                        return self.parse_non_create_response_message(_message)


	def parse_create_request_message(self, _message):
		configuration = _message & 0xFF
		mdepid = (_message >> 8) & 0xFF 
		mdlid =  (_message >> 16) & 0xFFFF
		return CreateMDLRequestMessage(mdlid, mdepid, configuration)
		
	def parse_non_create_request_message(self, _message):
		mdlid = _message & 0xFFFF
		op_code = (_message >> 16) & 0xFF
		return MDLRequestMessage(op_code, mdlid)

	def parse_create_response_message(self, _message):
		rsp_vars = _message & 0xFF
		mdlid = (_message >> 8) & 0xFFFF
		rsp_code = (_message >> 24) & 0xFF
		return CreateMDLResponseMessage(rsp_code, mdlid, rsp_vars)
				
	def parse_non_create_response_message(self, _message):
		mdlid = _message & 0xFFFF
		rsp_code = (_message >> 16) & 0xFF
		op_code = (_message >> 24) & 0xFF
		return MDLResponseMessage(op_code, rsp_code, mdlid)

	def parse_message(self, _message):
                opcode = self.get_op_code(_message)

                if self.is_request_message(opcode):
                        return self.parse_request_message(_message)
                elif self.is_response_message(opcode):
                        return self.parse_response_message(_message)
                else:
                        return None

