#!/usr/bin/env ptyhon

import mcap_defs
import socket
import thread
import time
from threading import Thread, RLock

MCAP_MCL_ROLE_ACCEPTOR		= 'ACCEPTOR'
MCAP_MCL_ROLE_INITIATOR		= 'INITIATOR'  

MCAP_STATE_READY		= 'READY'
MCAP_STATE_WAITING		= 'WAITING'

MCAP_MCL_STATE_IDLE		= 'IDLE'
MCAP_MCL_STATE_CONNECTED	= 'CONNECTED'
MCAP_MCL_STATE_PENDING		= 'PENDING'
MCAP_MCL_STATE_ACTIVE		= 'ACTIVE'

MCAP_MDL_STATE_ACTIVE		= 'ACTIVE'
MCAP_MDL_STATE_DELETED		= 'DELETED'


class VirtualChannel( Thread ):

	def __init__(self, _local_channel):
		Thread.__init__(self)
		self.lock = thread.allocate_lock()

		self.host = _local_channel[0]
		self.port = _local_channel[1]
		self.num_conn = 1
		self.socket = None
		self.connection = None
		self.is_open = False
		self.is_connected = False

	def open(self):
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.socket.bind((self.host, self.port))
		self.socket.listen(self.num_conn)
		self.is_open = True
	
	def connect(self, remote_addr):
		if (self.is_open):
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect(remote_addr)
			self.connection = s
			self.is_connected = True

	def run(self):
		try:
			if (self.is_open):
				_connection, _conn_addr = self.socket.accept()
				self.is_connected = True
				self.connection = _connection
				self.conn_addr = _conn_addr
		except socket.error, msg:
			pass
		

	def close(self):
		try:
			self.lock.acquire()
			if (self.is_open):
				self.connection.shutdown(2)
				self.socket.shutdown(2)
				self.connection.close()
				self.socket.close()
				self.is_connected = False
				self.is_open = False
		except socket.error, msg:
			print msg
		finally:
			self.lock.release()

	def read(self):
		if (self.is_connected):
			message = self.connection.recv(1024)
			return int(message)
		return ''

	def write(self, data):
		if (self.is_connected):
			self.connection.send(str(data))


class MDL:

	def __init__(self, _mdlid = 0, _mdepid = 0):
		self.mdlid = _mdlid
		self.mdepid = _mdepid
		self.state = MCAP_MDL_STATE_ACTIVE

	def __eq__(self, _mdl):
		return self.mdlid == _mdl.mdlid

	def __cmp__(self, _mdl):
		if ( self.mdlid < _mdl.mdlid ):
			return -1
		elif ( self.__eq__(_mdl) ):
			return 0
		else:
			return 1

class MCL:
	
	def __init__(self, _addr):
		self.addr = _addr
		self.virtual_channel = None
		self.create_channel()
		
		self.initialize_mcl()

	def create_channel(self):
		self.virtual_channel = VirtualChannel(self.addr)

	def initialize_mcl(self):
		self.state = MCAP_MCL_STATE_IDLE
		self.role = MCAP_MCL_ROLE_INITIATOR
		self.last_mdlid = mcap_defs.MCAP_MDL_ID_INITIAL
		self.csp_base_time = time.time()
		self.csp_base_counter = 0
		self.remote = None
		self.mdl_list = []
		self.is_channel_open = False

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
			if (item.state == MCAP_MDL_STATE_DELETED):
				return False
			else:
				item.state = MCAP_MDL_STATE_DELETED
				return True
	
	def delete_all_mdls(self):
		for mdl in self.mdl_list:
			mdl.state = MCAP_MDL_STATE_DELETED

	def create_mdlid():
		mdlid = self.last_mdlid
		if (mdlid > MCAP_MDL_ID_FINAL):
			return 0
		self.last_mdlid += 1
		return mdlid

	def open_channel(self):
                if ( self.virtual_channel.is_open ):
                        return False

		try:
			self.virtual_channel.open()
		except socket.error:
			print 'ERROR ' + msg
			return False

		self.is_channel_open = True

		self.virtual_channel.start()

		return True
	
	def close_channel(self):
		if ( not self.virtual_channel.is_open ):
			return False

		try:
			self.virtual_channel.close()
		except socket.error, msg:
			print 'ERROR ' + msg
			return False

		self.is_channel_open = False

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


class MCAPImpl( Thread ):

	def __init__(self, _mcl):
		Thread.__init__(self)
		self.lock = RLock()
		self.messageParser = mcap_defs.MessageParser()
		self.state = MCAP_STATE_READY
		self.mcl = _mcl

	def init_session(self):
		if ( not self.mcl.is_channel_open ):
			success = self.mcl.open_channel()
			if (success):
				self.mcl.state = MCAP_MCL_STATE_CONNECTED

	def close_session(self):
		self.mcl.delete_all_mdls()
		success = self.mcl.close_channel()
		if (success):
			self.mcl.state = MCAP_MCL_STATE_IDLE

	def run(self):
		try:
			while (self.mcl.is_channel_open):
				message = self.mcl.virtual_channel.read()
				if (message != ''):
					# do whatever you want
					self.receive_message(message)
		except Exception as inst:
			pass

		print 'FINISH...' 

## SEND METHODS

	def send_mdl_error_response(self):
		errorResponse = mcap_defs.ErrorMDLResponseMessage()
		success = self.send_response(int(errorResponse.__repr__(),16))
		return success

	def send_message(self, _message):
		success = False

		opcode = self.messageParser.get_op_code(_message)		
		
		if ( self.messageParser.is_response_message(opcode) ):
			return self.send_response(_message)
		else:
			return self.send_request(_message)

	def send_request(self, _request):
		if (self.state == MCAP_STATE_WAITING):
			raise InvalidOperationError('Still waiting for response')
		else:
			opcode = self.messageParser.get_op_code(_request)

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
			self.mcl.virtual_channel.write(_message)
			return True
		except socket.error, msg:
			print msg
			return False
			
## RECEIVE METHODS

	def receive_message(self, _message):
                opcode = self.messageParser.get_op_code(_message)
		
		self.last_received = _message

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
		requestMessage = self.messageParser.parse_request_message(_request)
		
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
		success = self.send_response( int(createResponse.__repr__(),16) )

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
                success = self.send_response( int(reconnectResponse.__repr__(),16) )

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
                success = self.send_response( int(deleteResponse.__repr__(),16) )

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
                success = self.send_response( int(abortResponse.__repr__(),16) )

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

