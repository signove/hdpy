#!/usr/bin/env ptyhon

import mcaptest_defs

MCAP_ROLE_ACCEPTOR		= 'ACCEPTOR'
MCAP_ROLE_INITIATOR		= 'INITIATOR'  

MCAP_STATE_READY		= 'READY'
MCAP_STATE_WAITING		= 'WAITING'

MCAP_MCL_STATE_IDLE		= 'IDLE'
MCAP_MCL_STATE_CONNECTED	= 'CONNECTED'
MCAP_MCL_STATE_PENDIND		= 'PENDING'
MCAP_MCL_STATE_ACTIVE		= 'ACTIVE'

class MCL:
	
	def __init__(self, _id):
		self.id = _id
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
		self.messageParser = mcaptest_defs.MessageParser()
		self.state = MCAP_MCL_STATE_IDLE
		self.mcl = _mcl

	def init_session(self):
		if ( not self.mcl.is_control_channel_open ):
			success = self.mcl.open_control_channel()
			if (success):
				self.state = MCAP_MCL_STATE_CONNECTED

	def close_session(self):
		self.mcl.delete_all_mdls()
		success = self.mcl.close_control_channel()
		if (success):
			self.state = MCAP_MCL_STATE_IDLE

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
		return sucess

	def send_mcap_command(self, _command):
		# convert __command to raw representation
		# use CC to send command
		pass
			
	def receive_message(self, _message):
                opcode = _message.get_op_code()

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
                
		success = process_request(_request)
		if (success):
			self.state == MCAP_STATE_READY
		return success

        def receive_response(self, _response):
		success = False
		# if a response is received when no request is outstanding, just ignore
                if (self.state == MCAP_STATE_WAITING):
                        success = process_response(_response)
			if (success):
                		self.state = MCAP_STATE_READY
			
		return success

	def process_response(self, _response):
		try:
			responseMessage = self.messageParser.parse_response_message(_response)
		except InvalidMessageError as error:
			return self.send_mdl_error_response()

		if ( responseMessage.rspcode == MCAP_RSP_SUCCESS ):

			# if received a create or reconnect operation
			if ( responseMessage.opcode == MCAP_MD_CREATE_MDL_RSP or
				responseMessage.opcode == MCAP_MD_RECONNECT_MDL_RSP ):
				self.state = MCAP_MCL_STATE_ACTIVE	

			elif ( responseMessage.opcode == MCAP_MD_DELETE_MDL_RSP ):
				mdlid = responseMessage.mdlid
				if ( mdlid == MCAP_MDL_ID_ALL ):
					self.mcl.delete_all_mdls()
				else:
					self.mcl.delete_mdl(responseMesage.mdlid)
				
				if ( not self.mcl.has_mdls() ):
					self.state = MCAP_MCL_STATE_CONNECTED
				
			elif ( responseMessage.opcode == MCAP_MD_ABORT_MDL_RSP ):
				if ( not self.mcl.has_mdls() ):
					self.state = MCAP_MCL_STATE_CONNECTED
			
			return True

		else:
			self.print_error_message( responseMessage.rspcode )
			return False


	def process_request(self, _request):
		try:
			requestMessage = self.messageParser.parse_request_message(_request)
		except InvalidMessageError as error:
                        return self.send_mdl_error_response()

		isOpcodeSupported = self.is_opcode_req_supported( resquestMessage.opcode ) 
		if ( isOpcodeSupported ):
			if ( requestMessage.opcode == MCAP_MCL_MD_CREATE_REQ ):
				print "Received CREATE_REQ" 		
			elif ( requestMessage.opcode == MCAP_MCL_MD_RECONNECT_REQ ):
				print "Received RECONNECT_REQ"
			elif ( requestMessage.opcode == MCAP_MCL_MD_DELETE_REQ ):
				print "Received DELETE_REQ"
			elif ( requestMessage.opcode == MCAP_MCL_MD_ABORT_REQ ):
				print "Received ABORT_REQ"
		else:
			opcodeRsp = requestMessage.opcode + 1
			requestNotSupportedRsp = MDLResponseMessage( opcodeRsp, MCAP_RSP_REQUEST_NOT_SUPPORTED, 0x0000 )
			return self.send_response( requestNotSupportedRsp )

	def print_error_message(self, _error_rsp_code):
		if ( _error_rsp_code ==  MCAP_RSP_INVALID_OP_CODE ):
			print "Invalid Op Code"
		elif ( _error_rsp_code ==  MCAP_RSP_INVALID_PARAMETER_VALUE ):
			print "Invalid Parameter Value"
		elif ( _error_rsp_code ==  MCAP_RSP_INVALID_MDEP ):
			print "Invalid MDEP"
		elif ( _error_rsp_code ==  MCAP_RSP_MDEP_BUSY ):
			print "MDEP Busy"
		elif ( _error_rsp_code ==  MCAP_RSP_INVALID_MDL ):
			print "Invalid MDL"
		elif ( _error_rsp_code ==  MCAP_RSP_MDL_BUSY ):
			print "MDL Busy"
		elif ( _error_rsp_code ==  MCAP_RSP_INVALID_OPERATION ):
			print "Invalid Operation"
		elif ( _error_rsp_code ==  MCAP_RSP_RESOURCE_UNAVAILABLE ):
			print "Resource Unavailable"
		elif ( _error_rsp_code ==  MCAP_RSP_INVALID_UNSPECIFIED_ERROR ):
			print "Unspecified Error"
		elif ( _error_rsp_code ==  MCAP_RSP_REQUEST_NOT_SUPPORTED ):
			print "Request Not Supported"
		elif ( _error_rsp_code ==  MCAP_RSP_CONFIGURATION_REJECTED ):
			print "Configuration Rejected"

	def is_opcode_req_supported(self, _opcode):
		return _opcode in [MCAP_MD_CREATE_MDL_REQ, MCAP_MD_RECONNECT_MDL_REQ,
                                   MCAP_MD_ABORT_MDL_REQ, MCAP_MD_DELETE_MDL_REQ]

