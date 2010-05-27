#!/usr/bin/env ptyhon

import mcap_defs

MCAP_MCL_ROLE_ACCEPTOR		= 'ACCEPTOR'
MCAP_MCL_ROLE_INITIATOR		= 'INITIATOR'  

MCAP_STATE_READY		= 'READY'
MCAP_STATE_WAITING		= 'WAITING'

MCAP_MCL_STATE_IDLE		= 'IDLE'
MCAP_MCL_STATE_CONNECTED	= 'CONNECTED'
MCAP_MCL_STATE_PENDING		= 'PENDING'
MCAP_MCL_STATE_ACTIVE		= 'ACTIVE'

class MDL:

	def __init__(self, _mdlid = 0, _mdepid = 0):
		self.mdlid = _mdlid
		self.mdepid = _mdepid

	def __eq__(self, _mdl):
		return (self.mdlid == _mdl.mdlid) and (self.mdepid == _mdl.mdepid)

	def __cmp__(self, _mdl):
		if ( self.mdlid < _mdl.mdlid ):
			return -1
		elif ( self.__eq__(_mdl) ):
			return 0
		else:
			return 1

class MCL:
	
	def __init__(self, _btaddr):
		self.btaddr = _btaddr
		self.state = MCAP_MCL_STATE_IDLE
		self.role = MCAP_MCL_ROLE_INITIATOR
		self.last_mdlid = mcap_defs.MCAP_MDL_ID_INITIAL
		self.remote = None
		self.mdl_list = []
		self.is_control_channel_open = False

	def has_mdls(self):
		return len(self.mdl_list) > 0

	def add_mdl(self, _mdl):
		self.mdl_list.append(_mdl)

	def delete_mdl(self, _mdl):
		self.mdl_list.remove(_mdl)
	
	def delete_all_mdls(self):
		del self.mdl_list[:]

	def create_mdlid():
		mdlid = self.last_mdlid
		if (mdlid > MCAP_MDL_ID_FINAL):
			return 0
		self.last_mdlid += 1
		return mdlid

	def open_control_channel(self):
		self.is_control_channel_open = True
		return True
	
	def close_control_channel(self):
		self.is_control_channel_open = False
		return True
		
class MCAPImpl:

	def __init__(self, _mcl):
		self.messageParser = mcap_defs.MessageParser()
		self.state = MCAP_STATE_READY
		self.mcl = _mcl

	def init_session(self):
		if ( not self.mcl.is_control_channel_open ):
			success = self.mcl.open_control_channel()
			if (success):
				self.mcl.state = MCAP_MCL_STATE_CONNECTED

	def close_session(self):
		self.mcl.delete_all_mdls()
		success = self.mcl.close_control_channel()
		if (success):
			self.state.mcl = MCAP_MCL_STATE_IDLE

	def send_error_mdl_response(self):
		errorResponse = ErrorMDLResponseMessage()
		success = self.send_message(errorResponse)
		return success

	def send_message(self, _message):
		success = False

		opcode = self.messageParser.get_op_code(_message)		
		messagePkg = self.messageParser.parse_message(_message)
		if ( self.messageParser.is_request_message(opcode) ):
			return self.send_request(messagePkg)
		elif ( self.messageParser.is_response_message(opcode) ):
			return self.send_response(messagePkg)
		else:
			raise InvalidOperationError('Invalid sent message')

	def send_request(self, _request):
		if (self.state == MCAP_STATE_WAITING):
			raise InvalidOperationError('Still waiting for response')
		else:
			if ( (_request.opcode == mcap_defs.MCAP_MD_CREATE_MDL_REQ) or
                                        (_request.opcode == mcap_defs.MCAP_MD_RECONNECT_MDL_REQ) ):
                        	self.mcl.state = MCAP_MCL_STATE_PENDING
			self.state = MCAP_STATE_WAITING		
	
			return self.send_mcap_command(_request)
	
	def send_response(self, _response):
		success = self.send_mcap_command(_response)
		return success

	def send_mcap_command(self, _message):
		# convert __command to raw representation
		# use CC to send command
		print _message
		package = int(_message.__repr__(),16)
		self.last_sent = package
		self.remote.receive_message( package )
		return True
			
	def receive_message(self, _message):
                opcode = self.messageParser.get_op_code(_message)

		self.last_received = _message
                if ( self.messageParser.is_request_message(opcode) ):
                        return self.receive_request(_message)
                elif ( self.messageParser.is_response_message(opcode) ):
                        return self.receive_response(_message)
                else:
                        raise InvalidOperationError('Invalid received message')


	def receive_request(self, _request):
		# if a request is received when a response is expected, only process if 
		# it is received by the Acceptor; otherwise, just ignore
		if (self.state == MCAP_STATE_WAITING):
                        if (self.mcl.role == MCAP_MCL_ROLE_INITIATOR):
				return False
			else:
				return self.process_request(_request)
		else:
                	return self.process_request(_request)

        def receive_response(self, _response):
		# if a response is received when no request is outstanding, just ignore
                if (self.state == MCAP_STATE_WAITING):
                        return self.process_response(_response)
		else:
			return False

	def process_response(self, _response):
		responseMessage = self.messageParser.parse_response_message(_response)

		self.state = MCAP_STATE_READY

		if ( responseMessage.opcode == mcap_defs.MCAP_MD_CREATE_MDL_RSP ):
			return self.process_create_response(responseMessage)
                elif ( responseMessage.opcode == mcap_defs.MCAP_MD_RECONNECT_MDL_RSP ):
                        return self.process_reconnect_response(responseMessage)
                elif ( responseMessage.opcode == mcap_defs.MCAP_MD_DELETE_MDL_RSP ):
                        return self.process_delete_response(responseMessage)
                elif ( responseMessage.opcode == mcap_defs.MCAP_MD_ABORT_MDL_RSP ):
                        return self.process_abort_response(responseMessage)

	def process_create_response(self, _response):
		
		if ( _response.rspcode == mcap_defs.MCAP_RSP_SUCCESS ):
			self.mcl.add_mdl( MDL(_response.mdlid, 0) )
			self.mcl.state = MCAP_MCL_STATE_ACTIVE
		else:
			if ( self.mcl.has_mdls() ):
				self.mcl.state = MCAP_MCL_STATE_ACTIVE
			else:
				self.mcl.state = MCAP_MCL_STATE_CONNECTED
			self.print_error_message(_response.rspcode)
			
		return True			
	
	def process_reconnect_response(self, _response):
		return self.process_create_response(_response)

	def process_delete_response(self, _response):		
		if ( _response.rspcode == mcap_defs.MCAP_RSP_SUCCESS ):

			mdlid = responseMessage.mdlid
			if ( mdlid == MCAP_MDL_ID_ALL ):
				self.mcl.delete_all_mdls()
			else:
				self.mcl.delete_mdl(_response.mdlid)
			
			if ( not self.mcl.has_mdls() ):
				self.mcl.state = MCAP_MCL_STATE_CONNECTED
			else:
				self.mcl.state = MCAP_MCL_STATE_ACTIVATE

		return True
			
	def process_abort_response(self, _response):	
		if ( _response.rspcode == mcap_defs.MCAP_RSP_SUCCESS ):
			if ( not self.mcl.has_mdls() ):
				self.mcl.state = MCAP_MCL_STATE_CONNECTED
			else:
				self.mcl.state = MCAP_MCL_STATE_ACTIVATE		
		else:
			self.print_error_message( _response.rspcode )

		return True

	def process_request(self, _request):
		requestMessage = None
		try:
			requestMessage = self.messageParser.parse_request_message(_request)
		except InvalidMessageError as error:
                        return self.send_mdl_error_response()
		
		opcode = self.messageParser.get_op_code(_request)
		
		isOpcodeSupported = self.is_opcode_req_supported( requestMessage.opcode ) 
		if ( isOpcodeSupported ):
			if ( requestMessage.opcode == mcap_defs.MCAP_MD_CREATE_MDL_REQ ):
				return self.process_create_request(requestMessage)
			elif ( requestMessage.opcode == mcap_defs.MCAP_MD_RECONNECT_MDL_REQ ):
				return self.process_reconnect_request(requestMessage)
			elif ( requestMessage.opcode == mcap_defs.MCAP_MD_DELETE_MDL_REQ ):
				return self.process_delete_request(requestMessage)
			elif ( requestMessage.opcode == mcap_defs.MCAP_MD_ABORT_MDL_REQ ):
				return self.process_abort_request(requestMessage)
		else:
			opcodeRsp = requestMessage.opcode + 1
			requestNotSupportedRsp = mcap_def.MDLResponseMessage( opcodeRsp, MCAP_RSP_REQUEST_NOT_SUPPORTED, 0x0000 )
			return self.send_response( requestNotSupportedRsp )

	def process_create_request(self, _request):
		rspcode = mcap_defs.MCAP_RSP_SUCCESS

	#	if ( not _request.has_valid_length() )
	#		rspcode = mcap_defs.MCAP_RSP_INVALID_PARAMETER_VALUE
		if ( not self.is_valid_mdlid(_request.mdlid) ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_MDL
		elif ( not self.support_more_mdls() ):
			rspcode = mcap_defs.MCAP_RSP_MDL_BUSY
		elif ( not self.is_valid_mdepid(_request.mdepid) ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_MDEP
		elif ( not self.support_more_mdeps() ):
			rspcode = mcap_defs.MCAP_RSP_MDEP_BUSY
		elif ( self.state == MCAP_MCL_STATE_PENDING ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_OPERATION
		elif ( not self.is_valid_configuration(_request.conf) ):
			rspcode = mcap_defs.MCAP_RSP_CONFIGURATION_REJECTED

		# TODO - not sure about which value we should return - see page 26
		rsp_params = 0x00
		if ( rspcode != mcap_defs.MCAP_RSP_CONFIGURATION_REJECTED ):
			rsp_params = _request.conf

		createResponse = mcap_defs.CreateMDLResponseMessage(rspcode, _request.mdlid, rsp_params)
		success = self.send_response( createResponse )

		if ( success and (rspcode == mcap_defs.MCAP_RSP_SUCCESS ) ):
			self.mcl.add_mdl(_request.mdlid)
			self.mcl.state = MCAP_MCL_STATE_ACTIVE
		
		return success
			

	def process_reconnect_request(self, _request):
		rspcode = mcap_defs.MCAP_RSP_SUCCESS

        #       if ( not _request.has_valid_length() )
        #               rspcode = mcap_defs.MCAP_RSP_INVALID_PARAMETER_VALUE
                if ( not self.is_valid_mdlid(_request.mdlid) ):
                        rspcode = mcap_defs.MCAP_RSP_INVALID_MDL
                elif ( not self.support_more_mdls() ):
                        rspcode = mcap_defs.MCAP_RSP_MDL_BUSY
                elif ( not self.support_more_mdeps() ):
                        rspcode = mcap_defs.MCAP_RSP_MDEP_BUSY
		elif ( self.state == MCAP_MCL_STATE_PENDING ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_OPERATION

                reconnectResponse = mcap_defs.ReconnectMDLResponseMessage(rspcode, _request.mdlid)
                success = self.send_response( reconnectResponse )

                if ( success and (rspcode == mcap_defs.MCAP_RSP_SUCCESS ) ):
                        self.mcl.add_mdl(_request.mdlid)
                        self.mcl.state = MCAP_MCL_STATE_ACTIVE

                return success


	def process_delete_request(self, _request):
                rspcode = mcap_defs.MCAP_RSP_SUCCESS

        #       if ( not _request.has_valid_length() )
        #               rspcode = mcap_defs.MCAP_RSP_INVALID_PARAMETER_VALUE
                if ( not self.is_valid_mdlid(_request.mdlid) ):
                        rspcode = mcap_defs.MCAP_RSP_INVALID_MDL
                elif ( not self.support_more_mdls() ):
                        rspcode = mcap_defs.MCAP_RSP_MDL_BUSY
		elif ( self.state == MCAP_MCL_STATE_PENDING ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_OPERATION

                deleteResponse = mcap_defs.DeleteMDLResponseMessage(rspcode, _request.mdlid)
                success = self.send_response( deleteResponse )

		if ( success and (rspcode == mcap_defs.MCAP_RSP_SUCCESS) ):
			if ( _request.mdlid == mcap_defs.MCAP_MDL_ID_ALL ):
				self.mcl.delete_all_mdls()
			else:
				self.mcl.delete_mdl(_request.mdlid)

			if ( not self.mcl.has_mdls() ):
				self.mcl.state = MCAP_MCL_STATE_CONNECTED	


	def process_abort_request(self, _request):
                rspcode = mcap_defs.MCAP_RSP_SUCCESS

        #       if ( not _request.has_valid_length() )
        #               rspcode = mcap_defs.MCAP_RSP_INVALID_PARAMETER_VALUE
                if ( not self.is_valid_mdlid(_request.mdlid) ):
                        rspcode = mcap_defs.MCAP_RSP_INVALID_MDL
		elif ( self.state != MCAP_MCL_STATE_PENDING ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_OPERATION
		
                abortResponse = mcap_defs.AbortMDLResponseMessage(rspcode, _request.mdlid)
                success = self.send_response( abortResponse )

		if ( success and ( rspcode == mcap_defs.MCAP_RSP_SUCCESS ) ):
			if ( self.mcl.has_mdls() ):
				self.mcl.state = MCAP_MCL_STATE_ACTIVE
			else:
				self.mcl.state = MCAP_MCL_STATE_CONNECTED

	def is_valid_mdlid(self, _mdlid):
		# has 16 bits
		if ( (_mdlid & 0x0000) != 0 ):
			return False					
	
		if ( _mdlid == mcap_defs.MCAP_MDL_ID_ALL):
			return True

		if (_mdlid < mcap_defs.MCAP_MDL_ID_INITIAL or _mdlid > mcap_defs.MCAP_MDL_ID_FINAL):
			return False

		return True

	def support_more_mdls(self):
		return True

	def is_valid_mdepid(self, _mdepid):
		# has 8 bits
                if ( (_mdepid & 0x00) != 0 ):
                        return False

                if (_mdepid < mcap_defs.MCAP_MDEP_ID_INITIAL or _mdepid > mcap_defs.MCAP_MDEP_ID_FINAL):
                        return False

                return True


	def support_more_mdeps(self):
		return True

	def is_valid_configuration(self, _config):
		return True

	def print_error_message(self, _error_rsp_code):
		if ( _error_rsp_code ==  mcap_defs.MCAP_RSP_INVALID_OP_CODE ):
			print "Invalid Op Code"
		elif ( _error_rsp_code ==  mcap_defs.MCAP_RSP_INVALID_PARAMETER_VALUE ):
			print "Invalid Parameter Value"
		elif ( _error_rsp_code ==  mcap_defs.MCAP_RSP_INVALID_MDEP ):
			print "Invalid MDEP"
		elif ( _error_rsp_code ==  mcap_defs.MCAP_RSP_MDEP_BUSY ):
			print "MDEP Busy"
		elif ( _error_rsp_code ==  mcap_defs.MCAP_RSP_INVALID_MDL ):
			print "Invalid MDL"
		elif ( _error_rsp_code ==  mcap_defs.MCAP_RSP_MDL_BUSY ):
			print "MDL Busy"
		elif ( _error_rsp_code ==  mcap_defs.MCAP_RSP_INVALID_OPERATION ):
			print "Invalid Operation"
		elif ( _error_rsp_code ==  mcap_defs.MCAP_RSP_RESOURCE_UNAVAILABLE ):
			print "Resource Unavailable"
		elif ( _error_rsp_code ==  mcap_defs.MCAP_RSP_INVALID_UNSPECIFIED_ERROR ):
			print "Unspecified Error"
		elif ( _error_rsp_code ==  mcap_defs.MCAP_RSP_REQUEST_NOT_SUPPORTED ):
			print "Request Not Supported"
		elif ( _error_rsp_code ==  mcap_defs.MCAP_RSP_CONFIGURATION_REJECTED ):
			print "Configuration Rejected"

	def is_opcode_req_supported(self, _opcode):
		return _opcode in [mcap_defs.MCAP_MD_CREATE_MDL_REQ, mcap_defs.MCAP_MD_RECONNECT_MDL_REQ,
                                   mcap_defs.MCAP_MD_ABORT_MDL_REQ, mcap_defs.MCAP_MD_DELETE_MDL_REQ]

