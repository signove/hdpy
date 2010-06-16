#!/usr/bin/env python

from mcap_defs import *

# MD_CREATE_MDL

def generate_create_mdl_req_message(mdlid, mdepid, conf):
	return CreateMDLRequestMessage(mdlid, mdepid, conf)

def generate_create_mdl_rsp_message(rspcode, mdlid, params):
	return CreateMDLResponseMessage(rspcode, mdlid, params)

# MD_RECONNECT_MDL

def generate_reconnect_mdl_req_message(mdlid):
	return ReconnectMDLRequestMessage(mdlid)

def generate_reconnect_mdl_rsp_message(rspcode, mdlid):
	return ReconnectMDLResponseMessage(rspcode, mdlid)

# MD_ABORT_MDL

def generate_abort_mdl_req_message(mdlid):
	return AbortMDLRequestMessage(mdlid)

def generate_abort_mdl_rsp_message(rspcode, mdlid):
	return AbortMDLResponseMessage(rspcode, mdlid)

# MD_DELETE_MDL

def generate_delete_mdl_req_message(mdlid):
	return DeleteMDLRequestMessage(mdlid)

def generate_delete_mdl_rsp_message(rspcode, mdlid):
	return DeleteMDLResponseMessage(rspcode, mdlid)

# ERROR

def generate_error_rsp_message(rspcode, mdlid):
	return ErrorMDLResponseMessage(rspcode, mdlid)

# Parser

def parse_message(_message):
	return MessageParser.parse_message(_message)

def usage():
	print "mcaptest - MCAP testing\n Usage:\n"
        print "\tmcaptest <mode> [options] [bdaddr]\n"
        print "Modes:\n"


