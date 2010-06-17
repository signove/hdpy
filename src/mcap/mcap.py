#!/usr/bin/env ptyhon

from mcap_defs import *
from mcap_sock import *
import time

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


class MDL(object):

	def __init__(self, btaddr, mdlid = 0, mdepid = 0):
		self.btaddr = btaddr
		self.mdlid = mdlid
		self.mdepid = mdepid
		self.state = MCAP_MDL_STATE_CLOSED
		self.dc = None
		self.psm = None

	def open(self):
		self.state = MCAP_MDL_STATE_LISTENING
		socket, psm = create_data_listening_socket(self.btaddr, True, 512)
		self.dc = socket
		self.psm = psm		
		self.state = MCAP_MDL_STATE_ACTIVE
	
	def close(self):
		if self.state in (MCAP_MDL_STATE_LISTENING,
			          MCAP_MDL_STATE_ACTIVE):
			self.dc.shutdown(2)
			self.dc.close()
			self.dc = None
		self.state = MCAP_MDL_STATE_CLOSED

	def connect(self):
		if self.state == MCAP_MDL_STATE_LISTENING:
			socket = create_data_socket(self.btaddr, None, True, 512)
			self.dc = socket
			self.psm = 0
		self.state = MCAP_MDL_STATE_ACTIVE	

	def __eq__(self, mdl):
		return self.mdlid == mdl.mdlid

	def __cmp__(self, mdl):
		if ( self.mdlid < mdl.mdlid ):
			return -1
		elif ( self.__eq__(_mdl) ):
			return 0
		else:
			return 1


class MCL(object):

	def __init__(self, btaddr, role):
		self.btaddr = btaddr 
		self.remote = None
		self.state = MCAP_MCL_STATE_IDLE
		self.lastmdlid = MCAP_MDL_ID_INITIAL

		self.csp_base_time = time.time()
		self.csp_base_counter = 0

		self.cc = None
		self.psm = None

		self.mdl_list = []
		self.is_channel_open = False

		self.role = role

		self.index = 0

	def is_cc_open(self):
		return self.state != MCAP_MCL_STATE_IDLE

	def open(self):
		if not self.is_cc_open():
			server_socket, self.psm = create_control_listening_socket(self.btaddr)
			self.cc, address = server_socket.accept()
			self.cc.setblocking(True)
			self.state = MCAP_MCL_STATE_CONNECTED
		# FIXME annotate remote upon accept

	def close(self):
		if self.is_cc_open():
			self.delete_all_mdls() # delete all MDLS first
			self.cc.shutdown(2)
			self.cc.close()
			self.state = MCAP_MCL_STATE_IDLE
			self.remote = None

	def connect(self, btaddr):
		if not self.is_cc_open():
			self.cc = create_control_socket(self.btaddr)
			set_ertm(self.cc)
			self.psm = 0
			self.cc.connect(btaddr)
			self.cc.setblocking(True)
			self.state = MCAP_MCL_STATE_CONNECTED
			self.remote = btaddr

	def open_cc(self):
		if self.is_cc_open():
			return False

		try:
			self.open()
		except Exception as error:
			print 'ERROR: ' + str(error)
			return False

		return True

	def connect_cc(self, btaddr):
		if self.is_cc_open():
			return False

		try:
			self.connect(btaddr)
		except Exception as error:
			print 'ERROR: ' + str(error)
			return False

		return True

	def close_cc(self):
		if not self.is_cc_open():
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
		if self.is_cc_open():
			message = self.cc.recv(1024)
			return message
		else:
			return ''

	def write(self, message):
		if self.is_cc_open():
			try:
				self.cc.send(message)
			except Exception as error:
				print error

	def count_mdls(self):
		counter = 0 
		for value in self.mdl_list:
			if value.state != MCAP_MDL_STATE_DELETED:
				counter += 1		
		return counter

	def has_mdls(self):
		return self.count_mdls() > 0

	def contains_mdl(self, mdl):
		try:
			mdl_index = self.mdl_list.index(mdl)
		except ValueError:
			mdl_index = -1

		if (mdl_index < 0):
			return False
		else:
			item = self.mdl_list[mdl_index]
			return ( item.state != MCAP_MDL_STATE_DELETED )

	def add_mdl(self, mdl):
		self.mdl_list.append(mdl)

	def delete_mdl(self, mdl):
		try:
			mdl_index = self.mdl_list.index(_mdl)
		except ValueError:
			mdl_index = -1

		if mdl_index < 0:
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
			if mdl.state == MCAP_MDL_STATE_CLOSED:
				mdl.state = MCAP_MDL_STATE_DELETED
				delete_any = True
		return delete_any	
	
	def create_mdlid(self):
		mdlid = self.last_mdlid
		if mdlid > MCAP_MDL_ID_FINAL:
			return 0
		self.last_mdlid += 1
		return mdlid



class MCLStateMachine:

	def __init__(self, mcl):
		self.parser = MessageParser()
		self.state = MCAP_STATE_READY
		self.mcl = mcl

## SEND METHODS

	def send_mdl_error_response(self):
		errorResponse = ErrorMDLResponse()
		success = self.send_response(errorResponse)
		return success

	def send_raw_message(self, message):
		if (self.state == MCAP_STATE_WAITING):
                        raise InvalidOperation('Still waiting for response')
                else:
                        self.state = MCAP_STATE_WAITING
                        try:
                                # do whatever you want
                                self.mcl.write(message)
                                return True
                        except Exception as msg:
                                print "CANNOT WRITE: " + str(msg)
                                return False

	def send_message(self, message):
		if (message.opcode % 2) != 0:
			return self.send_request(message)
		else:
			return self.send_response(message)

	def send_request(self, request):
		if (self.state == MCAP_STATE_WAITING):
			raise InvalidOperation('Still waiting for response')
		else:
			opcode = request.opcode

			if opcode in (MCAP_MD_CREATE_MDL_REQ,
					MCAP_MD_RECONNECT_MDL_REQ):
				self.mcl.state = MCAP_MCL_STATE_PENDING
			
			self.state = MCAP_STATE_WAITING			
			return self.send_mcap_command(request)
	
	def send_response(self, response):
		success = self.send_mcap_command(response)
		return success

	def send_mcap_command(self, message):
		# convert __command to raw representation
		# use CC to send command
		self.last_sent = message
		try:
			# do whatever you want
			self.mcl.write(message.encode())
			return True
		except Exception as msg:
			print "CANNOT WRITE: " + str(msg)
			return False
			
## RECEIVE METHODS

	def receive_message(self, message):
		self.last_received = message

		try:
			opcode = self.parser.get_opcode(message)
		except InvalidMessage:
			return self.send_mdl_error_response()
	
		try:
			if (opcode % 2):
				return self.receive_request(message)
			else:
				return self.receive_response(message)
		except InvalidMessage:
			# FIXME shouldn't be harsher response if invalid msg?
			return self.send_mdl_error_response()
	
	def receive_request(self, request):
		# if a request is received when a response is expected, only process if 
		# it is received by the Acceptor; otherwise, just ignore
		if (self.state == MCAP_STATE_WAITING):
			if (self.mcl.role == MCAP_MCL_ROLE_INITIATOR):
				return False
			else:
				return self.process_request(request)
		else:
			return self.process_request(request)

	def receive_response(self, response):
		# if a response is received when no request is outstanding, just ignore
		if (self.state == MCAP_STATE_WAITING):
			return self.process_response(response)
		else:
			return False

## PROCESS RESPONSE METHODS

	def process_response(self, response):
		responseMessage = self.parser.parse(response)

		self.state = MCAP_STATE_READY

		if responseMessage.opcode == MCAP_MD_CREATE_MDL_RSP:
			return self.process_create_response(responseMessage)
		elif responseMessage.opcode == MCAP_MD_RECONNECT_MDL_RSP:
			return self.process_reconnect_response(responseMessage)
		elif responseMessage.opcode == MCAP_MD_DELETE_MDL_RSP:
			return self.process_delete_response(responseMessage)
		elif responseMessage.opcode == MCAP_MD_ABORT_MDL_RSP:
			return self.process_abort_response(responseMessage)
		elif responseMessage.opcode == MCAP_ERROR_RSP:
			self.print_error_message(responseMessage.rspcode)

	def process_create_response(self, response):
		if response.rspcode == MCAP_RSP_SUCCESS:
			self.mcl.add_mdl( MDL(response.mdlid, 0) )
			self.mcl.state = MCAP_MCL_STATE_ACTIVE
		else:
			if self.mcl.has_mdls():
				self.mcl.state = MCAP_MCL_STATE_ACTIVE
			else:
				self.mcl.state = MCAP_MCL_STATE_CONNECTED
			self.print_error_message(response.rspcode)
			
		return True			
	
	def process_reconnect_response(self, response):
		return self.process_create_response(response)

	def process_delete_response(self, response):		
		if response.rspcode == MCAP_RSP_SUCCESS:

			mdlid = response.mdlid
			if mdlid == MCAP_MDL_ID_ALL:
				self.mcl.delete_all_mdls()
			else:
				self.mcl.delete_mdl( MDL(response.mdlid,0) )
			
			if not self.mcl.has_mdls():
				self.mcl.state = MCAP_MCL_STATE_CONNECTED
			else:
				self.mcl.state = MCAP_MCL_STATE_ACTIVE

		else:
			self.print_error_message(response.rspcode)

		return True
			
	def process_abort_response(self, response):	
		if response.rspcode == MCAP_RSP_SUCCESS:
			if not self.mcl.has_mdls():
				self.mcl.state = MCAP_MCL_STATE_CONNECTED
			else:
				self.mcl.state = MCAP_MCL_STATE_ACTIVE		
		else:
			self.print_error_message( response.rspcode )

		return True

## PROCESS REQUEST METHODS

	def process_request(self, request):
		try:
			request = self.parser.parse(request)
			if request.opcode == MCAP_MD_CREATE_MDL_REQ:
				return self.process_create_request(request)
			elif request.opcode == MCAP_MD_RECONNECT_MDL_REQ:
				return self.process_reconnect_request(request)
			elif request.opcode == MCAP_MD_DELETE_MDL_REQ:
				return self.process_delete_request(request)
			elif request.opcode == MCAP_MD_ABORT_MDL_REQ:
				return self.process_abort_request(request)
			else:
				raise Exception("Should not happen")

		except InvalidMessage:
			# FIXME: damaged messages should have a harsher response
			opcodeRsp = request.opcode + 1
			rsp = MDLResponse(opcodeRsp, MCAP_RSP_REQUEST_NOT_SUPPORTED, 0x0000)
			return self.send_response(rsp)

	def process_create_request(self, request):
		rspcode = MCAP_RSP_SUCCESS

	#	if not request.has_valid_length():
	#		rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE
		if not self.is_valid_mdlid(request.mdlid, False):
			rspcode = MCAP_RSP_INVALID_MDL
		elif not self.support_more_mdls():
			rspcode = MCAP_RSP_MDL_BUSY
		elif not self.is_valid_mdepid(request.mdepid):
			rspcode = MCAP_RSP_INVALID_MDEP
		elif not self.support_more_mdeps():
			rspcode = MCAP_RSP_MDEP_BUSY
		elif self.state == MCAP_MCL_STATE_PENDING:
			rspcode = MCAP_RSP_INVALID_OPERATION
		elif not self.is_valid_configuration(request.conf):
			rspcode = MCAP_RSP_CONFIGURATION_REJECTED

		# TODO - not sure about which value we should return - see page 26
		rsp_params = 0x00
		if rspcode != MCAP_RSP_CONFIGURATION_REJECTED:
			rsp_params = request.conf
		
		createResponse = CreateMDLResponse(rspcode, request.mdlid, rsp_params)
		success = self.send_response(createResponse)

		if success and (rspcode == MCAP_RSP_SUCCESS):
			self.mcl.add_mdl(MDL(request.mdlid,0))
			self.mcl.state = MCAP_MCL_STATE_ACTIVE
		
		return success

	def process_reconnect_request(self, request):
		rspcode = MCAP_RSP_SUCCESS

		#       if ( not request.has_valid_length() )
		#               rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE
		if not self.is_valid_mdlid(request.mdlid, False):
			rspcode = MCAP_RSP_INVALID_MDL
		elif not self.support_more_mdls():
			rspcode = MCAP_RSP_MDL_BUSY
		elif not self.support_more_mdeps():
			rspcode = MCAP_RSP_MDEP_BUSY
		elif self.state == MCAP_MCL_STATE_PENDING:
			rspcode = MCAP_RSP_INVALID_OPERATION

		reconnectResponse = ReconnectMDLResponse(rspcode, request.mdlid)
		success = self.send_response(reconnectResponse)

		if success and (rspcode == MCAP_RSP_SUCCESS):
			self.mcl.add_mdl( MDL(request.mdlid,0) )
			self.mcl.state = MCAP_MCL_STATE_ACTIVE

		return success

	def process_delete_request(self, request):
		rspcode = MCAP_RSP_SUCCESS

		#       if ( not request.has_valid_length() )
		#               rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE
		if (not self.is_valid_mdlid(request.mdlid, True)) or \
			(not self.contains_mdl_id(request.mdlid)):
			rspcode = MCAP_RSP_INVALID_MDL
		elif not self.support_more_mdls():
			rspcode = MCAP_RSP_MDL_BUSY
		elif self.state == MCAP_MCL_STATE_PENDING:
			rspcode = MCAP_RSP_INVALID_OPERATION

		deleteResponse = DeleteMDLResponse(rspcode, request.mdlid)
		success = self.send_response(deleteResponse)

		if success and (rspcode == MCAP_RSP_SUCCESS):
			if request.mdlid == MCAP_MDL_ID_ALL:
				self.mcl.delete_all_mdls()
			else:
				self.mcl.delete_mdl( MDL(request.mdlid, 0) )

			if not self.mcl.has_mdls():
				self.mcl.state = MCAP_MCL_STATE_CONNECTED	

	def process_abort_request(self, request):
		rspcode = MCAP_RSP_SUCCESS

		#       if not request.has_valid_length()
		#               rspcode = MCAP_RSP_INVALID_PARAMETER_VALUE
		if not self.is_valid_mdlid(request.mdlid, False):
			rspcode = MCAP_RSP_INVALID_MDL
		elif self.state != MCAP_MCL_STATE_PENDING:
			rspcode = MCAP_RSP_INVALID_OPERATION
		
		abortResponse = AbortMDLResponse(rspcode, request.mdlid)
		success = self.send_response(abortResponse)

		if success and ( rspcode == MCAP_RSP_SUCCESS ):
			if self.mcl.has_mdls():
				self.mcl.state = MCAP_MCL_STATE_ACTIVE
			else:
				self.mcl.state = MCAP_MCL_STATE_CONNECTED

## UTILITY METHODS

	def contains_mdl_id(self, mdlid):
		if (mdlid == MCAP_MDL_ID_ALL):
			return True
		
		return self.mcl.contains_mdl( MDL(mdlid, 0) )

	def is_valid_mdlid(self, mdlid, accept_all):
		# has 16 bits
		if (mdlid & 0x0000) != 0:
			return False					
	
		if (mdlid == MCAP_MDL_ID_ALL) and accept_all:
			return True

		if mdlid < MCAP_MDL_ID_INITIAL or mdlid > MCAP_MDL_ID_FINAL:
			return False

		return True

	def support_more_mdls(self):
		return True

	def is_valid_mdepid(self, mdepid):
		# has 8 bits
		if (mdepid & 0x00) != 0:
			return False

		if mdepid < MCAP_MDEP_ID_INITIAL or mdepid > MCAP_MDEP_ID_FINAL:
			return False

		return True

	def support_more_mdeps(self):
		return True

	def is_valid_configuration(self, config):
		return True

	def print_error_message(self, error_rsp_code):
		if error_rsp_code in error_rsp_messages:
			print error_rsp_messages[error_rsp_code]
		else:
			print "Unknown error rsp code %d" % error_rsp_code
