#!/usr/bin/env ptyhon

import mcap_defs

MCAP_ROLE_ACCEPTOR		= 'ACCEPTOR'
MCAP_ROLE_INITIATOR		= 'INITIATOR'  

MCAP_STATE_READY		= 'READY'
MCAP_STATE_WAITING		= 'WAITING'

MCAP_MCL_STATE_IDLE		= 'IDLE'
MCAP_MCL_STATE_CONNECTED	= 'CONNECTED'
MCAP_MCL_STATE_PENDING		= 'PENDING'
MCAP_MCL_STATE_ACTIVE		= 'ACTIVE'

class MCL:
	
	def __init__(self, _id):
		self.id = _id
		self.state = MCAP_MCL_STATE_IDLE
		self.mdl_list = []
		self.last_mdlid = 0x0001
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

	def send_create_mdl_request(self):
		mdlid = self.mcl.create_mdlid()
		createRequest = CreateMDLRequestMessage(mdlid, mdepid, configuration)
		response = self.send_message(createRequest)
		return response

	def send_reconnection_mdl_request(self, _mdlid):
		reconnectRequest = ReconnectMDLRequestMessage(_mdlid)
		response = self.send_message(reconnectRequest)
		return response

	def send_abort_mdl_request(self, _mdlid):
                abortRequest = AbortMDLRequestMessage(_mdlid)
                response = self.send_message(abortRequest)
		return response

        def send_delete_mdl_request(self, mdlid):
                deleteRequest = DeleteMDLRequestMessage(_mdlid)
                response = self.send_message(deletetRequest)
		return response

	def send_error_mdl_response(self):
		errorResponse = ErrorMDLResponseMessage()
		success = self.send_message(errorResponse)
		return success

	def send_message(self, _message):
		opcode = _message.get_op_code()
		
		if ( self.messageParser.is_request_message(opcode) ):
			return self.send_request(_message)
		elif ( self.messageParser.is_response_message(opcode) ):
			return self.send_response(_message)
		else:
			raise InvalidOperationError('Invalid sent message')

	def send_request(self, _request):
		success = False

		if (self.state == MCAP_STATE_WAITING):
			raise InvalidOperationError('Still waiting for response')
		else:
			success = self.send_mcap_command(_request)

		if ( success ):
			self.state == MCAP_STATE_WAITING

		return success
	
	def send_response(self, _response):
		success = self.send_mcap_command(_response)
		return success

	def send_mcap_command(self, _command):
		# convert __command to raw representation
		# use CC to send command
		print _command
		return True
			
	def receive_message(self, _message):
                opcode = self.messageParser.get_op_code(_message)

                if ( self.messageParser.is_request_message(opcode) ):
                        return self.receive_request(_message)
                elif ( self.messageParser.is_response_message(opcode) ):
                        return self.reveive_response(_message)
                else:
                        raise InvalidOperationError('Invalid received message')


	def receive_request(self, _request):
		# if a request is received when a response is expected, only process if 
		# it is received by the Acceptor; otherwise, just ignore
                if (self.state == MCAP_STATE_WAITING):
                        if (self.mcl.role == MCAP_MCL_ROLE_INITIATOR):
				return False
                
		success = self.process_request(_request)
		if (success):
			self.state == MCAP_STATE_READY
		return success

        def receive_response(self, _response):
		success = False
		# if a response is received when no request is outstanding, just ignore
                if (self.state == MCAP_STATE_WAITING):
                        success = self.process_response(_response)
			if (success):
                		self.state = MCAP_STATE_READY
			
		return success

	def process_response(self, _response):
		responseMessage = None
		try:
			responseMessage = self.messageParser.parse_response_message(_response)
		except InvalidMessageError as error:
			return self.send_mdl_error_response()

		if ( responseMessage.rspcode == MCAP_RSP_SUCCESS ):

			# if received a create or reconnect operation
			if ( responseMessage.opcode == MCAP_MD_CREATE_MDL_RSP or
				responseMessage.opcode == MCAP_MD_RECONNECT_MDL_RSP ):
				self.mcl.state = MCAP_MCL_STATE_ACTIVE	

			elif ( responseMessage.opcode == MCAP_MD_DELETE_MDL_RSP ):
				mdlid = responseMessage.mdlid
				if ( mdlid == MCAP_MDL_ID_ALL ):
					self.mcl.delete_all_mdls()
				else:
					self.mcl.delete_mdl(responseMesage.mdlid)
				
				if ( not self.mcl.has_mdls() ):
					self.mcl.state = MCAP_MCL_STATE_CONNECTED
				
			elif ( responseMessage.opcode == MCAP_MD_ABORT_MDL_RSP ):
				if ( not self.mcl.has_mdls() ):
					self.mcl.state = MCAP_MCL_STATE_CONNECTED
			
			return True

		else:
			self.print_error_message( responseMessage.rspcode )
			return False


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

		rsp_params = 0x00
		if ( rspcode == mcap_defs.MCAP_RSP_SUCCESS ):
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
                        self.mcl.state = MCAP_MCL_STATE_PENDING

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
                return self.send_response( deleteResponse )


	def process_abort_request(self, _request):
                rspcode = mcap_defs.MCAP_RSP_SUCCESS

        #       if ( not _request.has_valid_length() )
        #               rspcode = mcap_defs.MCAP_RSP_INVALID_PARAMETER_VALUE
                if ( not self.is_valid_mdlid(_request.mdlid) ):
                        rspcode = mcap_defs.MCAP_RSP_INVALID_MDL
		elif ( self.state != MCAP_MCL_STATE_PENDING ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_OPERATION
		
                abortResponse = mcap_defs.AbortMDLResponseMessage(rspcode, _request.mdlid)
                return self.send_response( abortResponse )

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

