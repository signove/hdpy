#!/usr/bin/env python
# -*- coding: utf-8

#######################################################################
# Copyright 2010 Signove Corporation - All rights reserved.
# Contact: Signove Corporation (contact@signove.com)
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330,
# Boston, MA 02111-1307  USA
#
# If you have questions regarding the use of this file, please contact
# Signove at contact@signove.com.
#######################################################################

# This module is a prototype implementation of HDP profile
# conversion from a simple dictionary to/from the XML format
# that BlueZ understands.

import xml.dom.minidom
import string


class HDPRecordException(Exception):
	pass


def myuint(value):
	if type(value) is not int:
		try:
			value = string.atoi(value, 0)
		except (TypeError, ValueError):
			raise HDPRecordException("Invalid uint: %s", value)
	if value < 0:
		raise HDPRecordException("Value must be non-negative: %d" \
						% value)
	return value


def add_attr(doc, parent, attr, data):
	if attr is not None:
		child = doc.createElement("attribute")
		child.setAttribute("id", "0x%04x" % myuint(attr))
		parent.appendChild(child)
		parent = child

	if type(data) is list:
		child = doc.createElement("sequence")
		for item in data:
			add_attr(doc, child, None, item)
	else:
		element_type, value = data
		if element_type == 'uint8':
			value = "0x%02x" % myuint(value)
		elif element_type == 'uint16':
			value = "0x%04x" % myuint(value)
		elif element_type == 'uint32':
			value = "0x%08x" % myuint(value)
		elif element_type == 'uuid' and type(value) is int:
			value = "0x%04x" % value
		else:
			value = str(value)
		child = doc.createElement(element_type)
		child.setAttribute("value", value)

	parent.appendChild(child)


def gen_xml(service):
	if not service['features']:
		raise HDPRecordException("No HDP features")

	cpsm = service['mcap_control_psm']
	dpsm = service['mcap_data_psm']

	if cpsm < 0x1001 or cpsm > 0xffff:
		raise HDPRecordException("Control PSM invalid")
	if dpsm < 0x1001 or dpsm > 0xffff or dpsm == cpsm:
		raise HDPRecordException("Data PSM invalid")

	doc = xml.dom.minidom.Document()
	record = doc.createElement("record")
	doc.appendChild(record)

	roles = {}
	mcap_supported_procedures = 0x00

	for mcap_procedures in service.get('mcap_procedures', []):
		if mcap_procedures == 'csp':
			mcap_supported_procedures |= 0x08
		elif mcap_procedures == 'csp_master':
			mcap_supported_procedures |= 0x10
		elif mcap_procedures == 'reconnect_init':
			mcap_supported_procedures |= 0x02
		elif mcap_procedures == 'reconnect_accept':
			mcap_supported_procedures |= 0x04
		else:
			raise HDPRecordException("Unknown MCAP procedure: %s" \
					% mcap_procedures)

	data_spec = service.get('data_spec', 0x01) # 0x01 == IEEE 10267

	hdp_features = []
	mdeps = {}
	data_types = {}

	for feature in service['features']:
		mdep_id = feature['mdep_id']
		data_type = feature['data_type']
		description = feature.get('description', None)
		s_role = feature['role']

		if s_role == 'source':
			roles[0x1401] = True
			role = 0x00
		elif s_role == 'sink':
			roles[0x1402] = True
			role = 0x01
		else:
			raise HDPRecordException("Unknown role: %s" \
				% feature['role'])

		if role != mdeps.get(mdep_id, role):
			raise HDPRecordException("Reusing MDEP ID %d " \
				"for different role" % mdep_id)
		mdeps[mdep_id] = role

		if data_type in data_types:
			if role in data_types[data_type]:
				raise HDPRecordException("Redundant role/type" \
					" tuple: (%s, %d)" % \
					(s_role, data_type))
			data_types[data_type].append(role)
		else:
			data_types[data_type] = [ role ]

		feature_record = [ \
			('uint8', mdep_id),
			('uint16', data_type),
			('uint8', role),
			]
		if description:
			feature_record.append(('text', description))

		hdp_features.append(feature_record)

	if "handle" in service:
		add_attr(doc, record, 0x0000, ('uint32', service['handle']))

	roles_sequence = [('uuid', k) for k in roles.keys()]
	add_attr(doc, record, 0x0001, roles_sequence)

	add_attr(doc, record, 0x0004, 	# protocol descriptor list
		[
			[
				('uuid', 0x0100), # L2CAP
				('uint16', cpsm), # control channel
			], [
				('uuid', 0x001e), # MCAP control channel
				('uint16', 0x0100), # version
			],
		])

	add_attr(doc, record, 0x0006, # language/encoding
		[
			('uint16', 0x656e), # 'en' (ISO 639 lang. code)
			('uint16', 0x006a), # UTF-8 (IANA MIBE code)
			('uint16', 0x0100), # Natural language ID
		])

	add_attr(doc, record, 0x0009,
		[
			[
				('uuid', 0x1400), # HDP
				('uint16', 0x0100), # HDP version
			],
		])

	add_attr(doc, record, 0x000d, # additional protocols
		[
			[
				[
					('uuid', 0x0100), # L2CAP
					('uint16', dpsm), # data channel
				], [
					('uuid', 0x001f), # MCAP data channel
				],
			],
		])

	name = service.get('name', "")
	if name:
		add_attr(doc, record, 0x0100, ('text', name))

	description = service.get('description', "")
	if description:
		add_attr(doc, record, 0x0101, ('text', description))

	provider = service.get('provider', "")
	if provider:
		add_attr(doc, record, 0x0102, ('text', provider))

	add_attr(doc, record, 0x0200, hdp_features) # HDP supported features

	add_attr(doc, record, 0x0301, ('uint8', data_spec))
	add_attr(doc, record, 0x0302, ('uint8', mcap_supported_procedures))

	return doc.toprettyxml(encoding="UTF-8")


def parse_uint(node):
	value = 0
	error = ""
	xvalue = node.attributes.get("value")

	if xvalue is None:
		error = "No value attribute"
	else:
		xvalue = xvalue.nodeValue
		try:
			value = string.atoi(xvalue, 0)
		except (ValueError, TypeError):
			error = "Invalid value"
		if value < 0:
			error = "Value < 0"

	return (value, error)


def parse_text(node):
	value = ""
	error = ""
	xvalue = node.attributes.get("value")

	if xvalue is None:
		error = "No value attribute"
	else:
		value = xvalue.nodeValue

	return (value, error)


def parse_uuid(node):
	return parse_text(node)


def parse_name(nodelist, service):
	if len(nodelist) != 1 or nodelist[0].tagName != 'text':
		service['error'] = "Bad name attr"
		return

	value, error = parse_text(nodelist[0])
	if error:
		service['error'] = "Bad name attr"
		return

	service['name'] = value


def parse_description(nodelist, service):
	if len(nodelist) != 1 or nodelist[0].tagName != 'text':
		service['error'] = "Bad description attr"
		return

	value, error = parse_text(nodelist[0])
	if error:
		service['error'] = "Bad description attr"
		return

	service['description'] = value


def parse_provider(nodelist, service):
	if len(nodelist) != 1 or nodelist[0].tagName != 'text':
		service['error'] = "Bad provider attr"
		return

	value, error = parse_text(nodelist[0])
	if error:
		service['error'] = "Bad provider attr"
		return

	service['provider'] = value


def parse_handle(nodelist, service):
	if len(nodelist) != 1 or nodelist[0].tagName != 'uint32':
		service['error'] = "Bad handle"
		return

	value, error = parse_uint(nodelist[0])
	if error:
		service['error'] = "Bad handle"
		return

	service['handle'] = value


def parse_data_spec(nodelist, service):
	if len(nodelist) != 1 or nodelist[0].tagName != 'uint8':
		service['error'] = "Bad data spec"
		return

	value, error = parse_uint(nodelist[0])
	if error:
		service['error'] = "Bad data spec"
		return

	service['data_spec'] = value

	if value != 0x01:
		service['error'] = "Unsupported data spec"


def parse_mcap_procedures(nodelist, service):
	if len(nodelist) != 1 or nodelist[0].tagName != 'uint8':
		service['error'] = "Bad MCAP supported procs"
		return

	value, error = parse_uint(nodelist[0])
	if error:
		service['error'] = "Bad MCAP supported procs"
		return

	proc_list = []

	if value & 0x02:
		proc_list.append('reconnect_init')
	if value & 0x04:
		proc_list.append('reconnect_accept')
	if value & 0x08:
		proc_list.append('csp')
	if value & 0x10:
		proc_list.append('csp_master')

	service['mcap_procedures'] = tuple(proc_list)


def parse_pdl(nodelist, service):
	if len(nodelist) != 1 or nodelist[0].tagName != 'sequence':
		service['error'] = "Bad profile descriptor list (1)"
		return

	nodelist = nodelist[0].childNodes

	if len(nodelist) != 1 or nodelist[0].tagName != 'sequence':
		service['error'] = "Bad profile descriptor list (2)"
		return

	nodelist = nodelist[0].childNodes

	if len(nodelist) != 2 or \
		nodelist[0].tagName != 'uuid' or \
		nodelist[1].tagName != 'uint16':

		service['error'] = "Bad profile descriptor list (3)"
		return

	uuid, error = parse_uuid(nodelist[0])
	if error:
		service['error'] = "Bad profile descriptor list (4)"
		return

	version, error = parse_uint(nodelist[1])
	if error:
		service['error'] = "Bad profile descriptor list (5)"
		return

	if version != 0x0100:
		service['error'] = "Unsupported HDP version"
		return

	service['_version'] = version



def parse_roles(nodelist, service):
	if len(nodelist) != 1 or nodelist[0].tagName != 'sequence':
		service['error'] = "Bad role attribute"
		return

	nodelist = nodelist[0].childNodes
	if not len(nodelist):
		service['error'] = "No roles in attr"
		return

	roles = {}

	for node in nodelist:
		if node.tagName != "uuid":
			service['error'] = "Bad role item in attribute"
			return

		uuid, error = parse_uuid(node)
		if error:
			service['error'] = "Bad role item in attribute"
			return

		try:
			uuid = string.atoi(uuid, 0)
			if uuid == 0x1401:
				roles['source'] = True
			elif uuid == 0x1402:
				roles['sink'] = True

		except (ValueError, TypeError):
			service['error'] = "Bad UUID in role: %s" % uuid
			return

	service['_roles'] = roles
	if not roles:
		# This is not an HDP record, ignore
		service['_not_hdp'] = True


def parse_additional_protos(nodelist, service):
	if len(nodelist) != 1 or nodelist[0].tagName != 'sequence':
		service['error'] = "Bad additional protocol attribute"
		return

	nodelist = nodelist[0].childNodes
	if len(nodelist) != 1 or nodelist[0].tagName != 'sequence':
		service['error'] = "Bad additional protocol attribute"
		return

	nodelist = nodelist[0].childNodes

	if len(nodelist) != 2 or \
		nodelist[0].tagName != 'sequence' or \
		nodelist[1].tagName != 'sequence':

		service['error'] = "Bad additional protocol attribute"
		return

	if len(nodelist[0].childNodes) != 2 or \
		len(nodelist[1].childNodes) != 1 or \
		nodelist[0].childNodes[0].tagName != 'uuid' or \
		nodelist[0].childNodes[1].tagName != 'uint16' or \
		nodelist[1].childNodes[0].tagName != 'uuid':

		service['error'] = "Bad add protocol attribute"
		return

	proto, error1 = parse_uuid(nodelist[0].childNodes[0])
	dpsm, error2 = parse_uint(nodelist[0].childNodes[1])
	identifier, error3 = parse_uuid(nodelist[1].childNodes[0])

	error = error1 or error2 or error3
	if error:
		service['error'] = error
		return

	try:
		proto = string.atoi(proto, 0)
	except (TypeError, ValueError):
		proto = 0

	try:
		identifier = string.atoi(identifier, 0)
	except (TypeError, ValueError):
		identifier = 0

	if proto != 0x0100:
		service['error'] = "Expected LCAP in add protocol attr"
		return

	if identifier != 0x001f:
		service['error'] = "Expected MCAP data channel protocol attr"
		return

	service['mcap_data_psm'] = dpsm


def parse_proto(nodelist, service):
	if len(nodelist) != 1 or nodelist[0].tagName != 'sequence':
		service['error'] = "Bad protocol attribute"
		return

	nodelist = nodelist[0].childNodes

	if len(nodelist) != 2 or \
		nodelist[0].tagName != 'sequence' or \
		nodelist[1].tagName != 'sequence':

		service['error'] = "Bad protocol attribute (1)"
		return

	if len(nodelist[0].childNodes) != 2 or \
		len(nodelist[1].childNodes) != 2 or \
		nodelist[0].childNodes[0].tagName != 'uuid' or \
		nodelist[0].childNodes[1].tagName != 'uint16' or \
		nodelist[1].childNodes[0].tagName != 'uuid' or \
		nodelist[0].childNodes[1].tagName != 'uint16':

		service['error'] = "Bad protocol attribute (2)"
		return

	proto, error1 = parse_uuid(nodelist[0].childNodes[0])
	cpsm, error2 = parse_uint(nodelist[0].childNodes[1])
	identifier, error3 = parse_uuid(nodelist[1].childNodes[0])
	version, error4 = parse_uint(nodelist[1].childNodes[1])

	error = error1 or error2 or error3 or error4
	if error:
		service['error'] = error
		return

	try:
		proto = string.atoi(proto, 0)
	except (TypeError, ValueError):
		proto = 0

	try:
		identifier = string.atoi(identifier, 0)
	except (TypeError, ValueError):
		identifier = 0

	if proto != 0x0100:
		service['error'] = "Expected LCAP in add protocol attr"
		return

	if identifier != 0x001e:
		service['error'] = "Expected MCAP control attr"
		return

	if version != 0x0100:
		service['error'] = "Unsupported MCAP version"
		return

	service['mcap_control_psm'] = cpsm


def parse_features(nodelist, service):
	if len(nodelist) != 1 or nodelist[0].tagName != 'sequence':
		service['error'] = "Bad feature attr"
		return

	if len(nodelist) < 1:
		service['error'] = "No features in attr"
		return

	features = []

	for feature in nodelist[0].childNodes:
		featurenode = feature.childNodes

		if len(featurenode) < 3 or len(featurenode) > 4:
			service['error'] = "Invalid feature"
			return

		mdep_id, error1 = parse_uint(featurenode[0])
		data_type, error2 = parse_uint(featurenode[1])
		role, error3 = parse_uint(featurenode[2])

		if len(featurenode) == 4:
			description, error4 = parse_text(featurenode[3])
		else:
			description = None
			error4 = ""

		error = error1 or error2 or error3 or error4
		if error:
			service['error'] = error
			return

		if role > 0x01:
			service['error'] = "Unknown role value %d" % role
			return

		role = {0x00: 'source', 0x01: 'sink'}[role]

		feature = {'mdep_id': mdep_id, 'data_type': data_type,
				'role': role}

		if description is not None:
			feature['description'] = description

		features.append(feature)

	service['features'] = features


attr_handlers = {
		0x0000: parse_handle,
		0x0001: parse_roles,
		0x0004: parse_proto,
		0x0009: parse_pdl,
		0x000d: parse_additional_protos,
		0x0200: parse_features,
		0x0100: parse_name,
		0x0301: parse_data_spec,
		0x0302: parse_mcap_procedures,
		0x0101: parse_description,
		0x0102: parse_provider,
		}


def parse_xml_record_inner(node, forgive_handle):
	service = {}
	service['handle'] = None
	service['features'] = None
	service['mcap_control_psm'] = None
	service['handle'] = None
	service['mcap_data_psm'] = None
	service['mcap_procedures'] = None
	service['data_spec'] = None
	service['name'] = ""
	service['description'] = ""
	service['provider'] = ""
	service['error'] = ""
	service['_roles'] = None
	service['_version'] = None
	service['_not_hdp'] = False

	for child in node.childNodes:
		if child.tagName != "attribute":
			continue

		attr_id = child.attributes.get("id")

		if attr_id is None:
			service['error'] = "Attribute without ID"
			return service

		attr_id = attr_id.nodeValue

		try:
			attr_id = string.atoi(attr_id, 0)
		except (TypeError, ValueError):
			service['error'] = "Bad attribute ID"

		if attr_id in attr_handlers:
			if not child.hasChildNodes:
				service['error'] = "Empty attribute: %04x" \
							% attr_id
				return service

			attr_handlers[attr_id](child.childNodes, service)

			if service['error']:
				return service
			if service['_not_hdp']:
				return None

	for k in service.keys():
		if service[k] is None and (k != 'handle' or not forgive_handle):
			service['error'] = "%s attribute not specified" % k
			return service

	mdeps = {}

	for feature in service['features']:
		role = feature['role']
		mdep_id = feature['mdep_id']

		if role not in service['_roles']:
			# service['error'] = "Role '%s' in features but " \
			# 			"not in roles" % role
			# return service
			#
			# PTS presents a SDP record with this 'defect'.
			# We can just ignore the features w/o respective roles
			continue

		if mdep_id in mdeps:
			if mdeps[mdep_id] != role:
				service['error'] = "MDEP ID %d in both " \
							"roles" % mdep_id
				return service

		mdeps[mdep_id] = role

	for k in service.keys():
		if k[0] == '_':
			del service[k]

	if forgive_handle and service['handle'] is None:
		del service['handle']

	if not service['error']:
		del service['error']

	return service


def parse_xml_record(node, forgive_handle, raise_bad_record):
	service = parse_xml_record_inner(node, forgive_handle)

	if service and 'error' in service and raise_bad_record:
		raise HDPRecordException("Error in record: %s" % \
						service['error'])

	return service


def remove_text_nodes(node):
	text_nodes = []

	for child in node.childNodes:
		if child.nodeType == child.TEXT_NODE:
			# mark for deletion
			text_nodes.append(child)
		else:
			remove_text_nodes(child)

	for child in text_nodes:
		child.parentNode.removeChild(child)


def parse_xml(xmlstring, forgive_handle=False, filter_xml_exception=True,
		raise_bad_record=True):
	try:
		doc = xml.dom.minidom.parseString(xmlstring)
	except:
		if filter_xml_exception:
			raise HDPRecordException("Malformed XML")
		else:
			raise

	remove_text_nodes(doc)

	services = []

	for record in doc.getElementsByTagName('record'):
		service = parse_xml_record(record, forgive_handle,
						raise_bad_record)
		if service:
			services.append(service)

	return services


def test():
	sample = open("../../scripts/record_oximeter.xml").read()
	record1 = parse_xml(sample)[0]
	record2 = parse_xml(gen_xml(record1))[0]
	# NOTE dependent on actual contents of xml file
	assert(record1 == record2)
	assert(record1['name'] == 'Nonin Oximeter')
	assert(record1['handle'] == 0x00010030)
	assert(record1['mcap_control_psm'] == 0x1001)
	assert(record1['mcap_data_psm'] == 0x1003)
	assert(len(record1['features']) == 1)
	assert('csp' in record1['mcap_procedures'])
	assert('reconnect_init' not in record1['mcap_procedures'])
	assert(record1['features'][0]['data_type'] == 0x1004)
	assert(record1['features'][0]['role'] == ('source'))

	feature1 = {'mdep_id': 0x01, 'role': 'source',
			'data_type': 0x1004, 'description': "Fake oximeter"}
	feature2 = {'mdep_id': 0x01, 'role': 'source', 'data_type': 0x4005}
	feature3 = {'mdep_id': 0x02, 'role': 'sink', 'data_type': 0x4006}
	feature4 = {'mdep_id': 0x04, 'role': 'sink', 'data_type': 0x4007}
	features = [feature1, feature2, feature3, feature4]
	hdp = {}
	hdp['mcap_control_psm'] = 0x1001
	hdp['features'] = features
	hdp['mcap_data_psm'] = 0x1003
	# NOTE default is 0x01, specified just to satisfy assertion below
	hdp['data_spec'] = 0x01
	hdp['name'] = "Fake oximeter"
	hdp['description'] = "A fake HDP record"
	hdp['provider'] = "Epx Inc."
	# NOTE order is important to satisfy assertion below
	hdp['mcap_procedures'] = ('reconnect_init', 'reconnect_accept', \
					'csp', 'csp_master')
	hdp2 = parse_xml(gen_xml(hdp), True)[0]

	assert(hdp['features'] == hdp2['features'])
	assert(hdp == hdp2)
	print "Ok"

if __name__ == '__main__':
	test()
