#!/usr/bin/env ptyhon

from mcap_defs import *
from mcap_sock import *
import time


class InvalidOperation(Exception):
	pass


class ControlChannelListener(object):
	def __init__(self, adapter, observer):
		self.observer = observer
		socket, psm = create_data_listening_socket(adapter, True, 512)
		self.sk = socket
		self.psm = psm
		observer.watch_cc(self, self.sk, self.activity, self.error)

	def activity(self, *args):
		sk, address = self.sk.accept()
		self.observer.new_cc(self, sk, address)
		return True

	def error(self, *args):
		self.sk = None
		self.psm = 0
		self.observer.error_cc(self)

class DataChannelListener(object):
	def __init__(self, adapter, observer):
		socket, psm = create_control_listening_socket(adapter)
		self.observer = observer
		self.sk = socket
		self.psm = psm
		observer.watch_dc(self, self.sk, self.activity, self.error)

	def activity(self, *args):
		sk, address = self.sk.accept()
		self.observer.new_dc(self, sk, address)
		return True

	def error(self, *args):
		self.sk = None
		self.psm = 0
		self.observer.error_dc(self)


class MDL(object):

	def __init__(self, mcl, mdlid, mdepid):
		self.mcl = mcl
		self.mdlid = mdlid
		self.mdepid = mdepid
		self.sk = None
		self.state = MCAP_MDL_STATE_CLOSED

	def close(self):
		self.state = MCAP_MDL_STATE_CLOSED
		if self.sk:
			try:
				self.sk.shutdown(2)
				self.sk.close()
			except IOError:
				pass
			self.sk = None
			self.mcl.closed_mdl(self)

	def accept(self, sk):
		if self.state != MCAP_MDL_STATE_CLOSED:
			raise InvalidOperation("Trying to accept over a non-closed MDL")

		self.sk = sk
		self.state = MCAP_MDL_STATE_ACTIVE

	def connect(self):
		if self.state != MCAP_MDL_STATE_CLOSED:
			raise InvalidOperation("Trying to connect a non-closed MDL")

		socket = create_data_socket(self.mcl.adapter, None, True, 512)
		self.sk = socket
		self.sk.connect(self.mcl.remote_addr)
		self.state = MCAP_MDL_STATE_ACTIVE

		if not self.mcl.connected_mdl_socket(self):
			self.state = MCAP_MDL_STATE_CLOSED
			self.sk.close()
			self.sk = None

	def read(self):
		try:
			message = self.sk.recv(1024)
		except IOError:
			message = ''
		if not message:
			self.close()
		return message

	def write(self, message):
		try:
			l = self.sk.send(message)
		except IOError:
			l = 0
		ok = l > 0
		if not ok:
			self.close()
		return ok


class MCL(object):

	def __init__(self, observer, adapter, role, remote_addr):
		self.observer = observer
		self.adapter = adapter 
		self.role = role
		self.remote_addr = remote_addr
		self.invalidated = False

		self.state = MCAP_MCL_STATE_IDLE
		self.last_mdlid = MCAP_MDL_ID_INITIAL

		self.csp_base_time = time.time()
		self.csp_base_counter = 0

		self.sk = None

		self.mdl_list = []
		self.is_channel_open = False

		self.index = 0

		self.sm = MCLStateMachine(self)

	def accept(self, sk):
		self.sk = sk
		self.state = MCAP_MCL_STATE_CONNECTED
		self.observer.watch_mcl(self, sk, self.activity, self.error)

	def close(self):
		if self.sk:
			self.close_all_mdls()
			try:
				self.sk.shutdown(2)
				self.sk.close()
			except IOError:
				pass
			self.sk = None
			self.observer.closed_mcl(self)

		self.state = MCAP_MCL_STATE_IDLE
		self.sm = MCLStateMachine(self)

	def connect(self):
		if self.state != MCAP_MCL_STATE_IDLE:
			raise InvalidOperation("State is not idle (already open/connected")

		sk = create_control_socket(self.adapter)
		sk.connect(self.remote_addr)

		self.sk = sk
		self.state = MCAP_MCL_STATE_CONNECTED
		self.observer.watch_mcl(self, sk, self.activity, self.error)

	def activity(self, *args):
		message = self.read()
		if message:
			self.sm.receive_message(message)
			self.observer.activity_mcl(self, True, message)
		else:
			self.close()
		return True

	def error(self, *args):
		self.close()
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
		try:
			message = self.sk.recv(1024)
		except IOError:
			message = ''
		return message

	def write(self, message):
		try:
			l = self.sk.send(message)
			self.observer.activity_mcl(self, False, message)
		except IOError:
			l = 0
		ok = l > 0
		if not ok:
			self.close()
		return ok

	def count_mdls(self):
		return len(self.mdl_list)

	def has_mdls(self):
		return self.count_mdls() > 0

	def get_mdl(mdlid):
		found = None
		i = -1
		for pos, mdl in enumerate(self.mdl_list):
			if mdl.mdlid == mdlid:
				i = pos
				found = mdl
				break
		return found, i

	def contains_mdl(self, mdlid):
		mdl, i = self.get_mdl(mdlid)
		return mdl is not None

	def add_mdl(self, mdl):
		self.mdl_list.append(mdl)

	def delete_mdl(self, mdlid):
		mdl, i = self.get_mdl(mdlid)
		if mdl:
			mdl.close()
			# change state so if someone holds a reference to
			# this MDL, will see that it has been deleted
			mdl.state = MCAP_MDL_STATE_DELETED
			del self.mdl_list[i]
		return mdl is not None
	
	def close_all_mdls(self):
		for mdl in self.mdl_list:
			mdl.close()

	def delete_all_mdls(self):
		while self.mdl_list:
			self.delete_mdl(self.mdl_list[0].mdlid)
	
	def create_mdlid(self):
		mdlid = self.last_mdlid
		if mdlid > MCAP_MDL_ID_FINAL:
			return 0
		self.last_mdlid += 1
		return mdlid

	def send_request(self, msg):
		self.sm.send_request(msg)

	def incoming_mdl_socket(self, sk):
		self.sm.incoming_mdl_socket(sk)

	def connected_mdl_socket(self, mdl):
		return self.sm.connected_mdl_socket(mdl)

	def closed_mdl(self, mdl):
		return self.sm.closed_mdl(mdl)


class MCLStateMachine:

	def __init__(self, mcl):
		self.parser = MessageParser()
		self.request_in_flight = 0
		self.mcl = mcl
		self.pending_active_mdl = None
		self.pending_passive_mdl = None

## SEND METHODS

	def send_mdl_error_response(self):
		errorResponse = ErrorMDLResponse()
		success = self.send_response(errorResponse)
		return success

	def send_raw_message(self, message):
		if self.request_in_flight:
                        raise InvalidOperation('Still waiting for response')

		self.request_in_flight = ord(message[0])
		ok = self.mcl.write(message)
		if not ok:
			print "CANNOT WRITE: " + str(msg)
		return ok

	def send_message(self, message):
		if (message.opcode % 2) != 0:
			return self.send_request(message)
		else:
			return self.send_response(message)

	def send_request(self, request):
		if self.request_in_flight:
			raise InvalidOperation('Still waiting for response')

		opcode = request.opcode
		self.request_in_flight = opcode
		return self.send_mcap_command(request)
	
	def send_response(self, response):
		success = self.send_mcap_command(response)
		return success

	def send_mcap_command(self, message):
		self.last_sent = message
		return self.mcl.write(message.encode())
			
## RECEIVE METHODS

	def receive_message(self, message):
		self.last_received = message

		try:
			opcode = self.parser.get_opcode(message)
			if (opcode % 2):
				return self.receive_request(message)
			else:
				return self.receive_response(message)
		except InvalidMessage:
			return self.send_mdl_error_response()
	
	def receive_request(self, request):
		# if a request is received when a response is expected, only process if 
		# it is received by the Acceptor; otherwise, just ignore
		if self.request_in_flight:
			if (self.mcl.role == MCAP_MCL_ROLE_INITIATOR):
				return False
			else:
				return self.process_request(request)
		else:
			return self.process_request(request)

	def receive_response(self, response):
		# if a response is received when no request is outstanding, just ignore
		if self.request_in_flight:
			return self.process_response(response)
		else:
			return False

## PROCESS RESPONSE METHODS

	def process_response(self, response):
		expected = self.request_in_flight + 1
		if not self.request_in_flight:
			expected = -1
		self.request_in_flight = 0

		responseMessage = self.parser.parse(response)

		if not expected or responseMessage.opcode != expected:
			print "Expected response for %d, got %d" % \
				(expected, responseMessage.opcode)
			return

		self.pending_active_mdl = None
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

	def process_create_response(self, response, reconn=False):
		if response.rspcode == MCAP_RSP_SUCCESS:
			mdl = MDL(self.mcl, response.mdlid, 0)
			self.pending_active_mdl = mdl
			self.reconn = reconn
			self.mcl.add_mdl(mdl)
			self.mcl.state = MCAP_MCL_STATE_PENDING
			self.mcl.observer.mdlgranted_mcl(self.mcl, mdl)
		else:
			if self.mcl.has_mdls():
				self.mcl.state = MCAP_MCL_STATE_ACTIVE
			else:
				self.mcl.state = MCAP_MCL_STATE_CONNECTED
			self.print_error_message(response.rspcode)
			
		return True			
	
	def process_reconnect_response(self, response, True):
		return self.process_create_response(response)

	def process_delete_response(self, response):		
		if response.rspcode == MCAP_RSP_SUCCESS:

			mdlid = response.mdlid
			if mdlid == MCAP_MDL_ID_ALL:
				for mdl in self.mcl.mdl_list:
					self.mcl.observer.mdldeleted_mcl(mdl)
				self.mcl.delete_all_mdls()
			else:
				if self.contains_mdlid(response.mdlid):
					mdl = self.mcl.get_mdl(response.mdlid)
					self.mcl.observer.mdldeleted_mcl(mdl)

				self.mcl.delete_mdl(response.mdlid)
			

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

			if self.contains_mdlid(response.mdlid):
				mdl = self.mcl.get_mdl(response.mdlid)
				self.mcl.observer.mdlaborted_mcl(mdl)
		else:
			self.print_error_message( response.rspcode )

		return True

	def incoming_mdl_socket(self, sk):
		# Called by DPSM listener
		mdl = self.pending_passive_mdl
		self.pending_passive_mdl = None
		ok = self.mcl.state == MCAP_MCL_STATE_PENDING
		ok = ok and not not mdl

		if ok:
			self.mcl.state = MCAP_MCL_STATE_ACTIVE
			mdl.accept(sk)
			self.mcl.observer.watch_mdl_errors(mdl, sk,
				self.mdl_socket_error)
			self.mcl.observer.mdlconnected_mcl(mdl, self.reconn)
		else:
			sk.close()

		return ok

	def connected_mdl_socket(self, mdl):
		# Called by MDL object itself
		ok = self.mcl.state == MCAP_MCL_STATE_PENDING
		ok = ok and self.pending_active_mdl == mdl
		self.pending_active_mdl = None

		if ok:
			self.mcl.state = MCAP_MCL_STATE_ACTIVE
			self.mcl.observer.watch_mdl_errors(mdl, mdl.sk,
				self.mdl_socket_error)
			self.mcl.observer.mdlconnected_mcl(mdl, self.reconn)
		else:
			mdl.close()

		return ok

	def mdl_socket_error(self, mdl, *args):
		mdl.close()

	def closed_mdl(self, mdl):
		''' called back by MDL itself '''
		self.mcl.observer.mdlclosed_mcl(mdl)


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
				raise InvalidOperation("Should not happen")

		except InvalidMessage:
			opcodeRsp = request.opcode + 1
			rsp = MDLResponse(opcodeRsp, MCAP_RSP_INVALID_PARAMETER_VALUE, 0x0000)
			return self.send_response(rsp)

	def process_create_request(self, request):
		rspcode = MCAP_RSP_SUCCESS

		if not self.is_valid_mdlid(request.mdlid, False):
			rspcode = MCAP_RSP_INVALID_MDL
		elif not self.support_more_mdls():
			rspcode = MCAP_RSP_MDL_BUSY
		elif not self.is_valid_mdepid(request.mdepid):
			rspcode = MCAP_RSP_INVALID_MDEP
		elif not self.support_more_mdeps():
			rspcode = MCAP_RSP_MDEP_BUSY
		elif self.mcl.state == MCAP_MCL_STATE_PENDING:
			print "Pending MDL connection"
			rspcode = MCAP_RSP_INVALID_OPERATION
		elif not self.is_valid_configuration(request.conf):
			rspcode = MCAP_RSP_CONFIGURATION_REJECTED

		config = 0x00
		if rspcode == MCAP_RSP_SUCCESS:
			config = request.conf
		
		createResponse = CreateMDLResponse(rspcode, request.mdlid, config)
		success = self.send_response(createResponse)

		if success and (rspcode == MCAP_RSP_SUCCESS):
			mdl = MDL(self.mcl, request.mdlid, 0)
			self.pending_passive_mdl = mdl
			self.reconn = False
			self.mcl.add_mdl(mdl)
			self.mcl.state = MCAP_MCL_STATE_PENDING
			self.mcl.observer.mdlrequested_mcl(self.mcl, mdl,
				request.mdepid, config)
		
		return success

	def process_reconnect_request(self, request):
		rspcode = MCAP_RSP_SUCCESS

		if not self.is_valid_mdlid(request.mdlid, False):
			rspcode = MCAP_RSP_INVALID_MDL
		elif not self.support_more_mdls():
			rspcode = MCAP_RSP_MDL_BUSY
		elif not self.support_more_mdeps():
			rspcode = MCAP_RSP_MDEP_BUSY
		elif self.mcl.state == MCAP_MCL_STATE_PENDING:
			print "Pending MDL connection"
			rspcode = MCAP_RSP_INVALID_OPERATION

		reconnectResponse = ReconnectMDLResponse(rspcode, request.mdlid)
		success = self.send_response(reconnectResponse)

		if success and (rspcode == MCAP_RSP_SUCCESS):
			mdl = MDL(self.mcl, request.mdlid, 0)
			self.pending_passive_mdl = mdl
			self.reconn = True
			self.mcl.add_mdl(mdl)
			self.mcl.state = MCAP_MCL_STATE_PENDING
			self.mcl.observer.mdlreconn_mcl(mdl)

		return success

	def process_delete_request(self, request):
		rspcode = MCAP_RSP_SUCCESS

		if (not self.is_valid_mdlid(request.mdlid, True)) or \
			(not self.contains_mdlid(request.mdlid)):
			rspcode = MCAP_RSP_INVALID_MDL

		elif not self.support_more_mdls():
			rspcode = MCAP_RSP_MDL_BUSY

		elif self.mcl.state == MCAP_MCL_STATE_PENDING:
			print "Pending MDL connection"
			rspcode = MCAP_RSP_INVALID_OPERATION

		deleteResponse = DeleteMDLResponse(rspcode, request.mdlid)
		success = self.send_response(deleteResponse)

		if success and (rspcode == MCAP_RSP_SUCCESS):
			self.pending_passive_mdl = None
			if request.mdlid == MCAP_MDL_ID_ALL:
				for mdl in self.mcl.mcl_list:
					self.mcl.observer.mdldeleted_mcl(mdl)
				self.mcl.delete_all_mdls()
			else:
				mdl = self.mcl.get_mdl(request.mdlid)
				self.mcl.observer.mdldeleted_mcl(mdl)
				self.mcl.delete_mdl(request.mdlid)

			if not self.mcl.has_mdls():
				self.mcl.state = MCAP_MCL_STATE_CONNECTED	

	def process_abort_request(self, request):
		rspcode = MCAP_RSP_SUCCESS

		if not self.is_valid_mdlid(request.mdlid, False):
			rspcode = MCAP_RSP_INVALID_MDL
		
		abortResponse = AbortMDLResponse(rspcode, request.mdlid)
		success = self.send_response(abortResponse)

		if success and ( rspcode == MCAP_RSP_SUCCESS ):
			self.pending_passive_mdl = None
			if self.mcl.has_mdls():
				self.mcl.state = MCAP_MCL_STATE_ACTIVE
			else:
				self.mcl.state = MCAP_MCL_STATE_CONNECTED
			mdl = self.mcl.get_mdl(request.mdlid)
			self.mcl.observer.mdlaborted_mcl(mdl)

## UTILITY METHODS

	def contains_mdlid(self, mdlid):
		if (mdlid == MCAP_MDL_ID_ALL):
			return True
		
		return self.mcl.contains_mdl(mdlid)

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


# FIXME update test scripts
# FIXME test3
# FIXME test against bluez

# FIXME pre-existent MDL in case of active reconnect?
# FIXME pre-existent MDL in case of passive reconnect? x 2
# FIXME MDL crossing protection
# FIXME is_valid_configuration should be call back upper layer to question
# FIXME MDL streaming or ertm channel?
# FIXME error feedback (for requests we had made)
# FIXME MDL mdep id attribution?
