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

# Response Codes
MCAP_RSP_SUCESS				= 0x00
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

# General messages

class MDLRequestMessage:

	def __init__(self, _opcode, _mdlid):
		self.opcode = _opcode
		self.mdlid = _mdlid

class MDLResponseMessage:

	def __init__(self, _opcode, _rspcode, _mdlid):
		self.opcode = _opcode
		self.rspcode = _rspcode
		self.mdlid = _mdlid

	def is_valid_response(self, _rspcode):
		pass

# Specific request messages

class CreateMDLRequestMessage( MDLRequestMessage ):

	def __init__(self, _mdlid, _mdepid, _conf):
		MDLRequestMessage.__init__(self, MCAP_MD_CREATE_MDL_REQ, _mdlid)
		self.mdepid = _mdepid
		self.conf = _conf


class ReconnectMDLRequestMessage( MDLRequestMessage ):

	def __init__(self, _mdlid):
		MDLRequestMessage.__init__(self, MCAP_MD_RECONNECT_MDL_REQ, _mdlid)


class AbortMDLRequestMessage( MDLRequestMessage ):

	def __init__(self, _mdlid):
                MDLRequestMessage.__init__(self, MCAP_MD_ABORT_MDL_REQ, _mdlid)


class DeleteMDLRequestMessage( MDLRequestMessage ):

	def __init__(self, _mdlid):
                MDLRequestMessage.__init__(self, MCAP_MD_DELETE_MDL_REQ, _mdlid)


# Specific response messages

class CreateMDLResponseMessage( MDLResponseMessage ):

        def __init__(self, _rspcode, _mdlid, _params):
                MDLResponseMessage.__init__(self, MCAP_MD_CREATE_MDL_RSP, _rspcode, _mdlid)
                self.params = _params
	
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
                MDLResponseMessage.__init__(self, MCAP_MD_ABORT_MDL_RSP, _rspcode, _mdlid)

	@staticmethod
        def is_valid_response(_rspcode):
                return _rspcode in [MCAP_RSP_SUCESS, MCAP_RSP_INVALID_PARAMETER_VALUE,
                                    MCAP_RSP_INVALID_MDL, MCAP_RSP_MDL_BUSY,
				    MCAP_RSP_INVALID_OPERATION, MCAP_RSP_UNSPECIFIED_ERROR, 
				    MCAP_RSP_REQUEST_NOT_SUPPORTED]


