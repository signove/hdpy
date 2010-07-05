# -*- coding: utf-8

################################################################
#
# Copyright (c) 2010 Signove. All rights reserved.
# See the COPYING file for licensing details.
#
# Autors: Elvis Pfützenreuter < epx at signove dot com >
#         Raul Herbster < raul dot herbster at signove dot com >
################################################################

#!/usr/bin/env ptyhon

from mcap_defs import *
from mcap_sock import *
from mcap_loop import *
from mcap_csp import CSPStateMachine
import time


class ControlChannelListener(object):
	def __init__(self, adapter, observer):
		self.observer = observer
		socket, psm = create_control_listening_socket(adapter)
		self.sk = socket
		self.psm = psm
		watch_fd(self.sk, self.activity)

	def activity(self, sk, event):
		if io_err(event):
			self.sk = None
			self.psm = 0
			schedule(self.observer.error_cc, self)
			return False

		sk, address = self.sk.accept()
		schedule(self.observer.new_cc, self, sk, address)
		return True


class DataChannelListener(object):
	def __init__(self, adapter, observer):
		socket, psm = create_data_listening_socket(adapter)
		self.observer = observer
		self.sk = socket
		self.psm = psm
		watch_fd(self.sk, self.activity)

	def activity(self, sk, event):
		if io_err(event):
			self.sk = None
			self.psm = 0
			schedule(self.observer.error_dc, self)
			return False

		sk, address = self.sk.accept()
		schedule(self.observer.new_dc, self, sk, address)
		return True


class MDL(object):

	def __init__(self, mcl, mdlid, mdepid, config, reliable):
		self.mcl = mcl
		self.mdlid = mdlid
		self.mdepid = mdepid
		self.config = config
		self.sk = None
		self.state = MCAP_MDL_STATE_CLOSED
		self.reliable = reliable

	def close(self):
		if self.abort():
			self.state = MCAP_MDL_STATE_CLOSED
			self.mcl.closed_mdl(self)

	def abort(self):
		if not self.sk:
			return False

		sk, self.sk = self.sk, None
		try:
			# shutdown = connection closed even if fd
			# copied to another process
			sk.shutdown(2)
			sk.close()
		except IOError:
			pass

		return True

	def accept(self, sk):
		if self.state != MCAP_MDL_STATE_CLOSED:
			raise InvalidOperation("Trying to accept over a non-closed MDL")

		set_reliable(sk, self.reliable)
		sk.setblocking(True)
		self.sk = sk
		self.state = MCAP_MDL_STATE_ACTIVE

	def connect(self):
		if self.state != MCAP_MDL_STATE_CLOSED:
			raise InvalidOperation("Trying to connect a non-closed MDL")

		try:
			self.state = MCAP_MDL_STATE_WAITING
			sk = create_data_socket(self.mcl.adapter, None,
						self.reliable)
			set_reliable(sk, self.reliable)
			async_connect(sk, self.mcl.remote_addr_dc)

			watch_fd_connect(sk, self.connect_cb)

		except IOError:
			schedule(self.mcl.connected_mdl_socket, self, -3)

	def connect_cb(self, sk, event):
		if event == IO_OUT and connection_ok(sk):
			self.sk = sk
			self.state = MCAP_MDL_STATE_ACTIVE

			if not self.mcl.connected_mdl_socket(self, 0):
				self.abort()
		else:
			self.state = MCAP_MDL_STATE_CLOSED
			self.mcl.connected_mdl_socket(self, -2)

		return False

	def active(self):
		return self.state != MCAP_MDL_STATE_CLOSED

	def read(self):
		if not self.sk:
			return ""
		try:
			message = self.sk.recv(1024)
		except IOError:
			message = ''
		if not message:
			self.close()
		return message

	def write(self, message):
		if not self.sk:
			return False
		try:
			l = self.sk.send(message)
		except IOError:
			l = 0
		ok = l > 0
		if not ok:
			self.close()
		return ok


class MCL(object):

	def __init__(self, observer, adapter, role, remote_addr, dpsm):
		self.observer = observer
		self.adapter = adapter 
		self.role = role
		self.remote_addr = remote_addr
		self.remote_addr_dc = (remote_addr[0], dpsm)
		self.invalidated = False

		self.state = MCAP_MCL_STATE_IDLE
		self.last_mdlid = MCAP_MDL_ID_INITIAL

		self.sk = None

		self.mdl_list = {}
		self.is_channel_open = False

		self.index = 0

		self.sm = MCLStateMachine(self)

	def accept(self, sk):
		self.sk = sk
		set_reliable(sk, True)
		sk.setblocking(True)
		self.state = MCAP_MCL_STATE_CONNECTED
		watch_fd(sk, self.activity)

	def close(self):
		if self.sk:
			self.close_all_mdls()
			try:
				self.sk.shutdown(2)
				self.sk.close()
			except IOError:
				pass
			self.sk = None
			schedule(self.observer.closed_mcl, self)

		self.state = MCAP_MCL_STATE_IDLE
		self.sm.stop()
		self.sm = MCLStateMachine(self)
		self.state = MCAP_MCL_STATE_IDLE

	def connect(self):
		if self.state != MCAP_MCL_STATE_IDLE:
			raise InvalidOperation("State is not idle" \
					"(already open/connected")

		try:
			self.state = MCAP_MCL_STATE_WAITING
			sk = create_control_socket(self.adapter)
			async_connect(sk, self.remote_addr)
			watch_fd_connect(sk, self.connect_cb)
		except IOError:
			schedule(self.observer.mclconnected_mcl, self, -1)

	def connect_cb(self, sk, evt):
		if evt == IO_OUT and connection_ok(sk):
			self.sk = sk
			sk.setblocking(True)
			self.state = MCAP_MCL_STATE_CONNECTED
			watch_fd(sk, self.activity)
			schedule(self.observer.mclconnected_mcl, self, 0)
		else:
			self.state = MCAP_MCL_STATE_IDLE
			schedule(self.observer.mclconnected_mcl, self, -2)

		return False

	def activity(self, sk, event):
		if io_err(event):
			self.close()
			return False

		message = self.read()
		if not message:
			self.close()
			return False

		self.sm.receive_message(message)
		schedule(self.observer.activity_mcl, self, True, message)
		return True

	def read(self):
		if not self.sk:
			print "Trying to read data in disconnected state"
			return ''
		try:
			message = self.sk.recv(1024)
		except IOError:
			message = ''
		return message

	def write(self, message):
		if not self.sk:
			print "Trying to send data in disconnected state"
			return False
		try:
			l = self.sk.send(message)
			schedule(self.observer.activity_mcl, self, False, message)
		except IOError:
			l = 0
		ok = l > 0
		if not ok:
			self.close()
		return ok

	def count_mdls(self):
		return len(self.mdl_list)

	def has_mdls(self):
		return not not self.mdl_list

	def get_mdl(self, mdlid):
		try:
			mdl = self.mdl_list[mdlid]
		except KeyError:
			mdl = None
		return mdl

	def contains_mdl(self, mdlid):
		return mdlid in self.mdl_list

	def add_mdl(self, mdl, reconn):
		if mdl.mdlid in self.mdl_list:
			if reconn:
				print "Bug: MDL %d: MDLID %d already in list" \
					% (id(mdl), mdl.mdlid)
		self.mdl_list[mdl.mdlid] = mdl

	def delete_mdl(self, mdlid):
		mdl = self.get_mdl(mdlid)
		if mdl:
			del self.mdl_list[mdlid]
			mdl.close()
			# change state so if someone holds a reference to
			# this MDL, will see that it has been deleted
			mdl.state = MCAP_MDL_STATE_DELETED
		return mdl is not None
	
	def close_all_mdls(self):
		for mdlid, mdl in self.mdl_list.items():
			mdl.close()

	def delete_all_mdls(self):
		for mdlid in self.mdl_list.keys():
			self.delete_mdl(mdlid)
	
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

	def connected_mdl_socket(self, mdl, err):
		return self.sm.connected_mdl_socket(mdl, err)

	def closed_mdl(self, mdl):
		return self.sm.closed_mdl(mdl)

	def get_timestamp(self):
		return self.sm.get_timestamp()

	def get_btclock(self):
		return self.sm.get_btclock()

class MCLStateMachine:

	def __init__(self, mcl):
		self.parser = MessageParser()
		self.request_in_flight = 0
		self.mcl = mcl
		self.csp = CSPStateMachine(self, self.mcl)
		self.pending_active_mdl = None
		self.pending_passive_mdl = None

## SEND METHODS

	def send_raw_message(self, message):
		'''
		For testing purposes only: sends an arbitrary stream of bytes
		via MCL control channel
		'''
		if self.request_in_flight:
                        raise InvalidOperation('Still waiting for response')

		self.request_in_flight = ord(message[0])
		# Hack to keep a copy of last request
		try:
			request = None
			if self.request_in_flight % 2:
				request = self.parser.parse(message)
				self.last_request = request
		except InvalidMessage:
			self.last_request = None

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
		if self.mcl.state in (MCAP_MCL_STATE_IDLE,
					MCAP_MCL_STATE_WAITING):
			raise InvalidOperation('MCL in idle state')

		if self.request_in_flight:
			raise InvalidOperation('Still waiting for response')

		opcode = request.opcode

		if self.csp.is_mine(opcode):
			# not our problem
			return self.csp.send_request(request)

		if self.mcl.state == MCAP_MCL_STATE_PENDING and \
			type(request) is not AbortMDLRequest:

			raise InvalidOperation('MCL in PENDING state')

		self.request_in_flight = opcode
		self.last_request = request
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
			opcode, rspcode = self.parser.get_opcode(message)
			if self.csp.is_mine(opcode):
				# shunt processing to CSP-specific machine
				return self.csp.receive_message(opcode, message)
				
			if (opcode % 2):
				return self.receive_request(opcode, message)
			else:
				return self.receive_response(opcode, message)
		except InvalidMessage:
			# we assume that higher-level errors are caught by
			# receive_request/response methods
			errorResponse = ErrorMDLResponse()
			return self.send_response(errorResponse)
	
	def receive_request(self, opcode, request):
		# if a request is received when a response is expected, only process if 
		# it is received by the Acceptor; otherwise, just ignore
		if self.request_in_flight:
			if (self.mcl.role == MCAP_MCL_ROLE_INITIATOR):
				return False
			else:
				return self.process_request(opcode, request)
		else:
			return self.process_request(opcode, request)

	def receive_response(self, opcode, response):
		# if a response is received when no request is outstanding, just ignore
		if self.request_in_flight:
			return self.process_response(opcode, response)
		else:
			return False

## PROCESS RESPONSE METHODS

	def process_response(self, opcode, response):
		expected = self.request_in_flight + 1
		if not self.request_in_flight:
			expected = -1
		self.request_in_flight = 0

		responseMessage = self.parser.parse(response)

		if not expected or opcode != expected:
			print "Expected response for %d, got %d" % \
				(expected, opcode)
			return

		self.pending_active_mdl = None
		# TODO make this look more like a state machine
		if opcode == MCAP_MD_CREATE_MDL_RSP:
			return self.process_create_response(responseMessage)
		elif opcode == MCAP_MD_RECONNECT_MDL_RSP:
			return self.process_reconnect_response(responseMessage)
		elif opcode == MCAP_MD_DELETE_MDL_RSP:
			return self.process_delete_response(responseMessage)
		elif opcode == MCAP_MD_ABORT_MDL_RSP:
			return self.process_abort_response(responseMessage)
		elif opcode == MCAP_ERROR_RSP:
			self.print_error_message(responseMessage.rspcode)
		else:
			raise InvalidOperation("Should not happen")

	def process_create_response(self, response, reconn=False):
		if response.rspcode == MCAP_RSP_SUCCESS:
			mdlid = response.mdlid
			if reconn:
				mdl = self.mcl.get_mdl(response.mdlid)
				if not mdl:
					print "Reconn resp to unknown MDLID"
					schedule(self.mcl.observer.mdlgranted_mcl,
						self.mcl, None, -1)
					return
			else:
				config = response.config
				reliable = True
				# TODO: submit response config to upper layers
				# TODO: get reliable/streaming from upper layers

				if self.last_request.mdlid != mdlid:
					print "Conn resp of different MDLID"
					schedule(self.mcl.observer.mdlgranted_mcl,
						self.mcl, None, -2)
					return

				if config and config != \
					self.last_request.config:
					print "Conn resp of different config"
					schedule(self.mcl.observer.mdlgranted_mcl,
						self.mcl, None, -3)
					return
				
				mdl = self.mcl.get_mdl(response.mdlid)
				if mdl:
					self.mcl.delete_mdl(mdl)
					schedule(self.mcl.observer.mdldeleted_mcl, mdl)

				mdl = MDL(self.mcl, mdlid,
					self.last_request.mdepid, config,
					reliable)

				self.mcl.add_mdl(mdl, reconn)

			self.pending_active_mdl = mdl
			self.reconn = reconn
			self.mcl.state = MCAP_MCL_STATE_PENDING

			schedule(self.mcl.observer.mdlgranted_mcl, self.mcl, mdl, 0)
		else:
			if self.mcl.has_mdls():
				self.mcl.state = MCAP_MCL_STATE_ACTIVE
			else:
				self.mcl.state = MCAP_MCL_STATE_CONNECTED

			self.print_error_message(response.rspcode)

			# notify application about the error
			schedule(self.mcl.observer.mdlgranted_mcl, self.mcl,
				None, response.rspcode)
			
		return True			
	
	def process_reconnect_response(self, response):
		return self.process_create_response(response, True)

	def process_delete_response(self, response):		
		if response.rspcode == MCAP_RSP_SUCCESS:

			mdlid = response.mdlid
			if self.is_mdlid_all(mdlid):
				for mdlid, mdl in self.mcl.mdl_list.items():
					schedule(self.mcl.observer.mdldeleted_mcl, mdl)
				self.mcl.delete_all_mdls()
			else:
				if self.contains_mdlid(response.mdlid):
					mdl = self.mcl.get_mdl(response.mdlid)
					schedule(self.mcl.observer.mdldeleted_mcl, mdl)

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
				schedule(self.mcl.observer.mdlaborted_mcl, self.mcl, mdl)
		else:
			self.print_error_message( response.rspcode )

		return True

	def mdl_crossing(self):
		psv = self.pending_passive_mdl
		act = self.pending_active_mdl

		return psv is not None and act is not None and \
			psv.mdlid == act.mdlid

	def incoming_mdl_socket(self, sk):
		# Called by DPSM listener
	
		ok = self.mcl.state == MCAP_MCL_STATE_PENDING \
			and self.pending_passive_mdl \
			and not self.mdl_crossing()

		mdl = self.pending_passive_mdl
		self.pending_passive_mdl = None

		if ok:
			self.mcl.state = MCAP_MCL_STATE_ACTIVE
			mdl.accept(sk)
			watch_fd_err(sk, self.mdl_socket_error, mdl)
			schedule(self.mcl.observer.mdlconnected_mcl,
				mdl, self.reconn, 0)
		else:
			# TODO refuse, not close
			sk.close()

		return ok

	def connected_mdl_socket(self, mdl, err):
		# Called by MDL object itself
		if err:
			self.pending_active_mdl = None
			schedule(self.mcl.observer.mdlconnected_mcl, mdl,
				self.reconn, err)
			return False

		ok = self.mcl.state == MCAP_MCL_STATE_PENDING
		ok = ok and self.pending_active_mdl.mdlid == mdl.mdlid
		self.pending_active_mdl = None

		if ok:
			self.mcl.state = MCAP_MCL_STATE_ACTIVE
			watch_fd_err(mdl.sk, self.mdl_socket_error, mdl)
			schedule(self.mcl.observer.mdlconnected_mcl, mdl,
				self.reconn, 0)
		else:
			schedule(self.mcl.observer.mdlconnected_mcl, mdl,
				self.reconn, -1)

		# MDL is responsible by closing socket if not ok
		return ok

	def mdl_socket_error(self, sk, event, mdl):
		mdl.close()
		return False

	def closed_mdl(self, mdl):
		''' called back by MDL itself '''
		schedule(self.mcl.observer.mdlclosed_mcl, mdl)


## PROCESS REQUEST METHODS

	def process_request(self, opcode, request):
		try:
			# TODO improve this, making it more like a state machine
			request = self.parser.parse(request)
			if opcode == MCAP_MD_CREATE_MDL_REQ:
				return self.process_create_request(request)
			elif opcode == MCAP_MD_RECONNECT_MDL_REQ:
				return self.process_reconnect_request(request)
			elif opcode == MCAP_MD_DELETE_MDL_REQ:
				return self.process_delete_request(request)
			elif opcode == MCAP_MD_ABORT_MDL_REQ:
				return self.process_abort_request(request)
			else:
				raise InvalidOperation("Should not happen")

		except InvalidMessage:
			opcodeRsp = opcode + 1
			rsp = MDLResponse(opcodeRsp,
					MCAP_RSP_INVALID_PARAMETER_VALUE,
					0x0000)
			return self.send_response(rsp)

	def process_create_request(self, request, reconn=False):
		rspcode = MCAP_RSP_SUCCESS
		mdlid = request.mdlid
		config = 0x00
		mdl = None
		reliable = True

		if not self.is_valid_mdlid(request.mdlid, False):
			rspcode = MCAP_RSP_INVALID_MDL

		elif self.mcl.state == MCAP_MCL_STATE_PENDING:
			print "Pending MDL connection",
			rspcode = MCAP_RSP_INVALID_OPERATION
		else:
			if reconn:
				mdl = self.mcl.get_mdl(mdlid)
				if mdl:
					reliable = mdl.reliable
				else:
					rspcode = MCAP_RSP_INVALID_MDL
			else:
				if not self.support_more_mdls():
					rspcode = MCAP_RSP_MDL_BUSY
				elif not self.is_valid_mdepid(request.mdepid):
					rspcode = MCAP_RSP_INVALID_MDEP
				elif not self.support_more_mdeps():
					rspcode = MCAP_RSP_MDEP_BUSY
				else:
					ok, reliable = \
						self.inquire_mdep(request.mdepid,
								request.config)
					if not ok:
						rspcode = MCAP_RSP_CONFIGURATION_REJECTED
	
				if rspcode == MCAP_RSP_SUCCESS:
					config = request.config
		
		if rspcode != MCAP_RSP_SUCCESS:
			self.print_error_message(rspcode)
		
		if reconn:
			response = ReconnectMDLResponse(rspcode, mdlid)
		else:
			response = CreateMDLResponse(rspcode, mdlid, config)

		success = self.send_response(response)

		if success and (rspcode == MCAP_RSP_SUCCESS):
			if not reconn:
				mdl = self.mcl.get_mdl(mdlid)
				if mdl:
					self.mcl.delete_mdl(mdl)
					schedule(self.mcl.observer.mdldeleted_mcl, mdl)

				mdl = MDL(self.mcl, mdlid,
					request.mdepid, request.config,
					reliable)

				self.mcl.add_mdl(mdl, reconn)

			self.pending_passive_mdl = mdl
			self.reconn = reconn

			self.mcl.state = MCAP_MCL_STATE_PENDING
			if reconn:
				schedule(self.mcl.observer.mdlreconn_mcl,
					self.mcl, mdl)
			else:
				schedule(self.mcl.observer.mdlrequested_mcl,
					self.mcl, mdl, request.mdepid, config)
		
		return success

	def process_reconnect_request(self, request):
		return self.process_create_request(request, True)

	def process_delete_request(self, request):
		rspcode = MCAP_RSP_SUCCESS
		mdlid = request.mdlid

		if not self.is_valid_mdlid(mdlid, True):
			rspcode = MCAP_RSP_INVALID_MDL

		elif not self.is_mdlid_all(mdlid) and \
		   not self.contains_mdlid(mdlid):
			rspcode = MCAP_RSP_INVALID_MDL

		elif not self.support_more_mdls():
			rspcode = MCAP_RSP_MDL_BUSY

		elif self.mcl.state == MCAP_MCL_STATE_PENDING:
			print "Pending MDL connection"
			rspcode = MCAP_RSP_INVALID_OPERATION

		deleteResponse = DeleteMDLResponse(rspcode, mdlid)
		success = self.send_response(deleteResponse)

		if success and (rspcode == MCAP_RSP_SUCCESS):
			self.pending_passive_mdl = None
			if self.is_mdlid_all(mdlid):
				for mdlid, mdl in self.mcl.mdl_list.items():
					schedule(self.mcl.observer.mdldeleted_mcl,
						mdl)
				self.mcl.delete_all_mdls()
			else:
				mdl = self.mcl.get_mdl(mdlid)
				schedule(self.mcl.observer.mdldeleted_mcl, mdl)
				self.mcl.delete_mdl(mdlid)

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
			schedule(self.mcl.observer.mdlaborted_mcl, self.mcl, mdl)

## UTILITY METHODS

	def contains_mdlid(self, mdlid):
		return self.mcl.contains_mdl(mdlid)

	def is_mdlid_all(self, mdlid):
		return mdlid == MCAP_MDL_ID_ALL

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

	def inquire_mdep(self, mdepid, config):
		return True, True

	def print_error_message(self, error_rsp_code):
		if error_rsp_code in error_rsp_messages:
			print error_rsp_messages[error_rsp_code]
		else:
			print "Unknown error rsp code %d" % error_rsp_code

	def get_timestamp(self):
		return self.csp.get_timestamp()

	def get_btclock(self):
		return self.csp.get_btclock()

	def stop(self):
		self.csp.stop()

# FIXME inquire_mdep should call upper layer
# FIXME MDL streaming or ertm channel? <-- via inquire_mdep

# TODO Refuse untimely MDL connection using BT_DEFER_SETUP
#	get addr via L2CAP_OPTIONS to decide upon acceptance
#	definitive accept using poll OUT ; if !OUT, read 1 byte

# TODO async writes (here and at instance)
# TODO optional request security level
# TODO PENDING state timeout (MCAP spec should tell what to do in this case)
