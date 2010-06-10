#!/usr/bin/env ptyhon

import mcap_defs
import mcap_sock
import time
from bluetooth import *
import gobject
from struct import pack, unpack

MCAP_MCL_ROLE_ACCEPTOR		= 'ACCEPTOR'
MCAP_MCL_ROLE_INITIATOR		= 'INITIATOR'  

MCAP_STATE_READY		= 'READY'
MCAP_STATE_WAITING		= 'WAITING'

MCAP_MCL_STATE_IDLE		= 'IDLE'
MCAP_MCL_STATE_CONNECTED	= 'CONNECTED'
MCAP_MCL_STATE_PENDING		= 'PENDING'
MCAP_MCL_STATE_ACTIVE		= 'ACTIVE'

MCAP_MDL_STATE_CLOSED		= 'CLOSED'
MCAP_MDL_STATE_LISTENING	= 'LISTENING'
MCAP_MDL_STATE_ACTIVE		= 'ACTIVE'
MCAP_MDL_STATE_CLOSED		= 'CLOSED'
MCAP_MDL_STATE_DELETED		= 'DELETED'

MSG_FORMAT = 'L'

def pack_msg(msg):
	return pack(MSG_FORMAT, msg)

def unpack_msg(msg):
	return int(msg,16)

class MDL(object):

	def __init__(self, _btaddr, _mdlid = 0, _mdepid = 0):
		self.btaddr = _btaddr
		self.mdlid = _mdlid
		self.mdepid = _mdepid
		self.state = MCAP_MDL_STATE_CLOSED
		self.dc = None
		self.psm = None

	def open(self):
		self.state = MCAP_MDL_STATE_LISTENING
		socket, psm = mcap_sock.create_data_listening_socket(self.btaddr, True, 512)
		self.dc = socket
		self.psm = psm		
		self.state = MCAP_MDL_STATE_ACTIVE
	
	def close(self):
		if ( self.state == MCAP_MDL_STATE_LISTENING or
			self.state ==  MCAP_MDL_STATE_ACTIVE ):
			self.dc.shutdown(2)
			self.dc.close()
		self.state = MCAP_MDL_STATE_CLOSED

	def connect(self):
		if ( self.state == MCAP_MDL_STATE_LISTENING ):
			socket, psm = mcap_sock.create_data_socket(self.btaddr, True, 512)
			self.dc = socket
			self.psm = psm 
		self.state = MCAP_MDL_STATE_ACTIVE	

	def read(self):
		if (self.state == MCAP_MDL_STATE_ACTIVE):
			return self.dc.recv(512)
		else:
			return ''

	def write(self, _message):
		if (self.state == MCAP_MDL_STATE_ACTIVE):
			self.dc.send(_message)

	def __eq__(self, _mdl):
		return self.mdlid == _mdl.mdlid

	def __cmp__(self, _mdl):
		if ( self.mdlid < _mdl.mdlid ):
			return -1
		elif ( self.__eq__(_mdl) ):
			return 0
		else:
			return 1

class MCL(object):

	def __init__(self, _btaddr, _role):
		self.btaddr = _btaddr 
		self.state = MCAP_MCL_STATE_IDLE
		self.last_mdlid = mcap_defs.MCAP_MDL_ID_INITIAL

		self.csp_base_time = time.time()
		self.csp_base_counter = 0

		self.cc = None
		self.psm = None

		self.mdl_list = []
		self.is_channel_open = False

		self.role = _role

		self.index = 0

	def is_cc_open(self):
		return self.state != MCAP_MCL_STATE_IDLE

	def open(self):
		if ( not self.is_cc_open() ):
			server_socket, self.psm = mcap_sock.create_control_listening_socket(self.btaddr)
			self.cc, address = server_socket.accept()
			self.cc.setblocking(True)
			self.state = MCAP_MCL_STATE_CONNECTED

	def close(self):
		if ( self.is_cc_open() ):
			self.delete_all_mdls() # delete all MDLS first
			self.cc.shutdown(2)
			self.cc.close()
			self.state = MCAP_MCL_STATE_IDLE

	def connect(self, btaddr):
		if ( not self.is_cc_open() ):
			self.cc = BluetoothSocket(proto=L2CAP)
			mcap_sock.set_ertm(self.cc)
			self.psm = btaddr[1]
			self.cc.connect((btaddr[0], self.psm))
			self.cc.setblocking(True)
			self.state = MCAP_MCL_STATE_CONNECTED

	def open_cc(self):
		if ( self.is_cc_open() ):
			return False

		try:
			self.open()
		except Exception as error:
			print 'ERROR: ' + str(error)
			return False

		return True

	def connect_cc(self, btaddr):
		if ( self.is_cc_open() ):
			return False

		try:
			self.connect(btaddr)
		except Exception as error:
			print 'ERROR: ' + str(error)
			return False

		return True

	def close_cc(self):
		if ( not self.is_cc_open() ):
			return False

		try:
			self.close()
		except Exception as msg:
			print 'ERROR: ' + str(msg)
			return False

		return True

	def get_csp_timestamp(self):
		now = time.time()
		offset = now - self.csp_base_time
		offset = int(1000000 * offset) # convert to microseconds
		return self.csp_base_counter + offset

	def set_csp_timestamp(self, counter):
		# Reset counter to value provided by CSP-Master
		self.csp_base_time = time.time()
		self.csp_base_counter = counter

	def read(self):
		if ( self.is_cc_open() ):
			# return as string
			_message = self.cc.recv(1024)
			return _message
		else:
			return ''

	def write(self, _message):
		if ( self.is_cc_open() ):
			try:
			# receive as string
				self.cc.send(_message)
			except Exception as error:
				print error

	def count_mdls(self):
		counter = 0 
		for value in self.mdl_list:
			if ( value.state != MCAP_MDL_STATE_DELETED ):
				counter += 1		
		return counter

	def has_mdls(self):
		return self.count_mdls() > 0

	def contains_mdl(self, _mdl):
		try:
			mdl_index = self.mdl_list.index(_mdl)
		except ValueError:
			mdl_index = -1

		if (mdl_index < 0):
			return False
		else:
			item = self.mdl_list[mdl_index]
			return ( item.state != MCAP_MDL_STATE_DELETED )

	def add_mdl(self, _mdl):
		self.mdl_list.append(_mdl)

	def delete_mdl(self, _mdl):
		try:
			mdl_index = self.mdl_list.index(_mdl)
		except ValueError:
			mdl_index = -1

		if (mdl_index < 0):
			return False
		else:
			item = self.mdl_list[mdl_index]
			item.close()
			if (item.state == MCAP_MDL_STATE_CLOSED):
				item.state = MCAP_MDL_STATE_DELETED
				return True
			else:
				return False
	
	def delete_all_mdls(self):
		delete_any = False
		for mdl in self.mdl_list:
			mdl.close()
			if (mdl.state == MCAP_MDL_STATE_CLOSED):
				mdl.state = MCAP_MDL_STATE_DELETED
				delete_any = True
		return delete_any	
	
	def create_mdlid(self):
		mdlid = self.last_mdlid
		if (mdlid > MCAP_MDL_ID_FINAL):
			return 0
		self.last_mdlid += 1
		return mdlid

class MCLStateMachine:

	def __init__(self, _mcl):
		self.messageParser = mcap_defs.MessageParser()
		self.state = MCAP_STATE_READY
		self.mcl = _mcl

## SEND METHODS

	def send_mdl_error_response(self):
		errorResponse = mcap_defs.ErrorMDLResponseMessage()
		success = self.send_response(errorResponse)
		return success

	def send_raw_message(self, _message):
		if (self.state == MCAP_STATE_WAITING):
                        raise mcap_defs.InvalidOperationError('Still waiting for response')
                else:
                        self.state = MCAP_STATE_WAITING
                        try:
                                # do whatever you want
                                self.mcl.write(_message)
                                return True
                        except Exception as msg:
                                print "CANNOT WRITE: " + str(msg)
                                return False

	def send_message(self, _message):
		if ( self.messageParser.is_response_message(_message.opcode) ):
			return self.send_response(_message)
		else:
			return self.send_request(_message)

	def send_request(self, _request):
		if (self.state == MCAP_STATE_WAITING):
			raise mcap_defs.InvalidOperationError('Still waiting for response')
		else:
			opcode = _request.opcode

			if ( (opcode == mcap_defs.MCAP_MD_CREATE_MDL_REQ) or
                                        (opcode == mcap_defs.MCAP_MD_RECONNECT_MDL_REQ) ):
				self.mcl.state = MCAP_MCL_STATE_PENDING
			
			self.state = MCAP_STATE_WAITING			
			return self.send_mcap_command(_request)
	
	def send_response(self, _response):
		success = self.send_mcap_command(_response)
		return success

	def send_mcap_command(self, _message):
		# convert __command to raw representation
		# use CC to send command
		self.last_sent = _message
		try:
			# do whatever you want
			self.mcl.write(_message.__repr__())
			return True
		except Exception as msg:
			print "CANNOT WRITE: " + str(msg)
			return False
			
## RECEIVE METHODS

	def receive_message(self, _message):
		message_value = unpack_msg(_message) # convert to number

		opcode = self.messageParser.get_op_code(message_value)
	
		self.last_received = message_value

		if ( self.messageParser.is_request_message(opcode) ):
			return self.receive_request(_message)
		elif ( self.messageParser.is_response_message(opcode) ):
			return self.receive_response(_message)
		else:
			return self.send_mdl_error_response()
	
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

## PROCESS RESPONSE METHODS

	def process_response(self, _response):
		response_value = unpack_msg(_response) # convert to number 
		responseMessage = self.messageParser.parse_response_message(response_value)

		self.state = MCAP_STATE_READY

		if ( responseMessage.opcode == mcap_defs.MCAP_MD_CREATE_MDL_RSP ):
			return self.process_create_response(responseMessage)
		elif ( responseMessage.opcode == mcap_defs.MCAP_MD_RECONNECT_MDL_RSP ):
			return self.process_reconnect_response(responseMessage)
		elif ( responseMessage.opcode == mcap_defs.MCAP_MD_DELETE_MDL_RSP ):
			return self.process_delete_response(responseMessage)
		elif ( responseMessage.opcode == mcap_defs.MCAP_MD_ABORT_MDL_RSP ):
			return self.process_abort_response(responseMessage)
		elif ( responseMessage.opcode == mcap_defs.MCAP_ERROR_RSP ):
			self.print_error_message( responseMessage.rspcode )

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

			mdlid = _response.mdlid
			if ( mdlid == mcap_defs.MCAP_MDL_ID_ALL ):
				self.mcl.delete_all_mdls()
			else:
				self.mcl.delete_mdl( MDL(_response.mdlid,0) )
			
			if ( not self.mcl.has_mdls() ):
				self.mcl.state = MCAP_MCL_STATE_CONNECTED
			else:
				self.mcl.state = MCAP_MCL_STATE_ACTIVE

		else:
			self.print_error_message(_response.rspcode)

		return True
			
	def process_abort_response(self, _response):	
		if ( _response.rspcode == mcap_defs.MCAP_RSP_SUCCESS ):
			if ( not self.mcl.has_mdls() ):
				self.mcl.state = MCAP_MCL_STATE_CONNECTED
			else:
				self.mcl.state = MCAP_MCL_STATE_ACTIVE		
		else:
			self.print_error_message( _response.rspcode )

		return True

## PROCESS REQUEST METHODS

	def process_request(self, _request):
		request_value = unpack_msg(_request) # convert to number
		requestMessage = self.messageParser.parse_request_message(request_value)
		
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
		if ( not self.is_valid_mdlid(_request.mdlid, False) ):
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
		success = self.send_response(createResponse)

		if ( success and (rspcode == mcap_defs.MCAP_RSP_SUCCESS ) ):
			self.mcl.add_mdl( MDL(_request.mdlid,0) )
			self.mcl.state = MCAP_MCL_STATE_ACTIVE
		
		return success

	def process_reconnect_request(self, _request):
		rspcode = mcap_defs.MCAP_RSP_SUCCESS

		#       if ( not _request.has_valid_length() )
		#               rspcode = mcap_defs.MCAP_RSP_INVALID_PARAMETER_VALUE
		if ( not self.is_valid_mdlid(_request.mdlid, False) ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_MDL
		elif ( not self.support_more_mdls() ):
			rspcode = mcap_defs.MCAP_RSP_MDL_BUSY
		elif ( not self.support_more_mdeps() ):
			rspcode = mcap_defs.MCAP_RSP_MDEP_BUSY
		elif ( self.state == MCAP_MCL_STATE_PENDING ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_OPERATION

		reconnectResponse = mcap_defs.ReconnectMDLResponseMessage(rspcode, _request.mdlid)
		success = self.send_response(reconnectResponse)

		if ( success and (rspcode == mcap_defs.MCAP_RSP_SUCCESS ) ):
			self.mcl.add_mdl( MDL(_request.mdlid,0) )
			self.mcl.state = MCAP_MCL_STATE_ACTIVE

		return success

	def process_delete_request(self, _request):
		rspcode = mcap_defs.MCAP_RSP_SUCCESS

		#       if ( not _request.has_valid_length() )
		#               rspcode = mcap_defs.MCAP_RSP_INVALID_PARAMETER_VALUE
		if ( (not self.is_valid_mdlid(_request.mdlid, True)) or 
			( not self.contains_mdl_id(_request.mdlid) ) ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_MDL
		elif ( not self.support_more_mdls() ):
			rspcode = mcap_defs.MCAP_RSP_MDL_BUSY
		elif ( self.state == MCAP_MCL_STATE_PENDING ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_OPERATION

		deleteResponse = mcap_defs.DeleteMDLResponseMessage(rspcode, _request.mdlid)
		success = self.send_response(deleteResponse)

		if ( success and (rspcode == mcap_defs.MCAP_RSP_SUCCESS) ):
			if ( _request.mdlid == mcap_defs.MCAP_MDL_ID_ALL ):
				self.mcl.delete_all_mdls()
			else:
				self.mcl.delete_mdl( MDL(_request.mdlid, 0) )

			if ( not self.mcl.has_mdls() ):
				self.mcl.state = MCAP_MCL_STATE_CONNECTED	

	def process_abort_request(self, _request):
		rspcode = mcap_defs.MCAP_RSP_SUCCESS

		#       if ( not _request.has_valid_length() )
		#               rspcode = mcap_defs.MCAP_RSP_INVALID_PARAMETER_VALUE
		if ( not self.is_valid_mdlid(_request.mdlid, False) ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_MDL
		elif ( self.state != MCAP_MCL_STATE_PENDING ):
			rspcode = mcap_defs.MCAP_RSP_INVALID_OPERATION
		
		abortResponse = mcap_defs.AbortMDLResponseMessage(rspcode, _request.mdlid)
		success = self.send_response(abortResponse)

		if ( success and ( rspcode == mcap_defs.MCAP_RSP_SUCCESS ) ):
			if ( self.mcl.has_mdls() ):
				self.mcl.state = MCAP_MCL_STATE_ACTIVE
			else:
				self.mcl.state = MCAP_MCL_STATE_CONNECTED

## UTILITY METHODS

	def contains_mdl_id(self, _mdlid):
		if (_mdlid == mcap_defs.MCAP_MDL_ID_ALL):
			return True
		
		return self.mcl.contains_mdl( MDL(_mdlid, 0) )

	def is_valid_mdlid(self, _mdlid, _accept_all):
		# has 16 bits
		if ( (_mdlid & 0x0000) != 0 ):
			return False					
	
		if ( (_mdlid == mcap_defs.MCAP_MDL_ID_ALL) and _accept_all):
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
