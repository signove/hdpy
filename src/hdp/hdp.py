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

import sys
from mcap.mcap_instance import MCAPInstance, InvalidOperation
from mcap.mcap_loop import watch_fd, IO_IN, schedule
from mcap.mcap_loop import timeout_call, timeout_cancel
from mcap.misc import BlueZ, DBG
from . import hdp_record
import random


class HealthError(Exception):
	"""HealthError exception
	"""
	pass


class HealthManager(object):
	"""This class provide ways to create an object of type 'HealthApplication',
	destroy an object of type 'HealthApplication', search for new BlueZ devices,
	and manage signals.
	"""
	def __init__(self):
		self.applications = []
		self.signal_handler = None
		pass

	def CreateApplication(self, config): # -> HealthApplication
		"""Returns the path of the new registered application. The agent
		parameter is the path of the object with the callbacks to
		notify events.
		@param config: A dictionary containing information to create a
		HealthApplication object. The keys of this dictionary are DataType,
		Role, Description and ChannelType.
		@type config: Dictionary. 
		"""
		application = HealthApplication(self, config)
		if not application:
			return None
		self.applications.append(application)
		return application

	def DestroyApplication(self, application):
		"""Closes the HDP application identified by the object path. Also
		application will be closed if the process that started it leaves
		the bus.
		@param application: Object patho for application.
		@type application: HealthApplication.
		"""
		application.stop()
		self.applications.remove(application)

	def UpdateDevices(self):
		"""Search for new BlueZ devices.
		"""
		BlueZ().search()

	def RegisterSignalHandler(self, signal_handler):
		"""Registers a signal handler.
		@param signal_handler: The signal handler must be a function that
		receives an object, an interface and data as parameters.
		@type signal_handler: function.
		"""
		self.signal_handler = signal_handler

	def signal(self, name, obj, interface, data):
		"""Calls the matching signal_handler.
		@param name: Signal name.
		@type name: String.
		@param obj: The object who sent the signal.
		@type obj: object.
		@param interface: The interface for the object who sent the signal.
		@type interface: String.
		@param data: Data sent from the Signal
		@type data: undefined.
		@return: what signal_handler returns.
		"""
		if not self.signal_handler:
			DBG(1, "Ignored signal due to lack of signal handler")
			return

		method = getattr(self.signal_handler, name, None)

		if not method:
			DBG(1, "Ignored signal: %s method not impl in handler" %
				name)
			return

		return method(obj, interface, data)


class HealthApplication(MCAPInstance):
	"""This is the application class which manages devices and channels. It
	inherits from MCAPInstance.
	"""
	def __init__(self, manager, config):
		err = self.process_config(config)
		if err:
			raise HealthError("Bad config: %s" % err)

		MCAPInstance.__init__(self, adapter="", listen=True)

		self.mdl_watch(False)

		self.manager = manager

		self.devices = [] # relationship 1:(0,1) with MCL
		self.channels = [] # relationship 1:1 with MDL
		self.stopped = False
		self.suspended = False

		self.publish()

		BlueZ().register_observer(self, self.remote_uuid)

	def device_created(self, addr):
		def closure_ok(records):
			self.device_created2(addr, records)

		def closure_nok(*args):
			# Ignore
			DBG(1, "SDP query failed")
			pass

		BlueZ().get_records(addr, self.remote_uuid,
			closure_ok, closure_nok)

	def device_created2(self, addr, records):
		'''
		Gets the SDP records for the discovered device
		and transverses them to extract individual devices
		'''

		new_devices = []

		for handle in records:
			hdprec = hdp_record.parse_xml(str(records[handle]))
			if not hdprec:
				continue
			for subrec in hdprec:
				for feature in subrec["features"]:
					srv = self.device_created3(addr,
							subrec, feature)
					new_devices.append(srv)

		self.remove_old_devices(addr, new_devices)


	def device_created3(self, addr, hdprec, feature):
		'''
		Gets a particular feature of an HDP record and
		makes a HealthDevice out of it
		'''

		feat_sink = (feature['role'] == 'sink')

		if feature['data_type'] != self.data_type or \
					feat_sink == self.sink:
			return

		cpsm = hdprec['mcap_control_psm']
		dpsm = hdprec['mcap_data_psm']
		mdepid = feature['mdep_id']

		preexists = self.match_device(addr, cpsm, dpsm, mdepid)
		if preexists:
			return preexists

		return self.create_device(addr, cpsm, dpsm, mdepid)

	def device_removed(self, addr):
		"""Called when a device is removed.
		@param addr: Address of device removed.
		@type addr: String.
		"""
		self.remove_old_devices(addr, [])
		DBG(2, "HDP: device removed %s" % addr)

	def device_found(self, addr):
		""" Called when a device is found. Can be extended by subclasses.
		@param addr: Address of device found.
		@type addr: String.
		"""
		def closure_ok(records):
			self.device_created2(addr, records)

		def closure_nok(*args):
			# Ignore
			pass

		BlueZ().get_records(addr, self.remote_uuid,
			closure_ok, closure_nok)

		DBG(3, "HDP: device found %s" % addr)

	def device_disappeared(self, addr):
		"""Called when a device disappears. Can be extended by subclasses.
		@param addr: Address of device disappeared.
		@type addr: String.
		"""
		DBG(3, "HDP: device disappeared %s" % addr)

	def bluetooth_dead(self):
		"""Called when the bluetooth is dead. Can be extended by subclasses
		"""
		DBG(1, "Obs: bt dead")
		self.suspend()

	def bluetooth_alive(self):
		"""Called when the bluetooth is alive. Can be extended by subclasses
		"""
		DBG(1, "Obs: bt alive")
		self.resume()

	def adapter_added(self, name):
		"""Called when an adapter is added. Can be extended by subclasses
		@param name: Name of adapter added.
		@type name: string.
		"""
		pass

	def adapter_removed(self, name):
		"""Called when an adapter is removed. Can be extended by subclasses
		@param name: Name of adapter removed.
		@type name: string.
		"""
		pass

	def process_config(self, config):
		"""Processes configuration dictionary.
		@param config: Configuration dictionary.
		@type config: Dictionary.
		"""
		self.sdp_record = {'features': []}
		self.sdp_handle = None

		auto_mdepid = 1
		is_auto_id = True

		role = config["Role"]

		if role not in ("Source", "Sink"):
			return "Role must be 'Source' or 'Sink'"

		self.sink = (role == "Sink" and 1 or 0)

		# If I am sink, I want to learn about sources (0x1401)
		# and vice-versa

		self.remote_uuid = self.sink and "1401" or "1402"

		if 'MDEPID' not in config:
			self.mdepid = 1
		else:
			self.mdepid = config['MDEPID']
			if self.mdepid <= 0:
				return "MDEP ID must be positive"

		self.data_type = config["DataType"]

		if self.data_type < 0 or self.data_type > 65535:
			return "Bad data type"

		self.description = ""

		if 'Description' in config:
			self.description = config["Description"][:240]

		self.sdp_record['features'].append({
			'mdep_id': self.mdepid,
			'role': role.lower(),
			'data_type': self.data_type,
			'description': self.description})

		return None

	def publish(self):
		"""Publish SDP.
		"""
		self.sdp_handle = None

		r = self.sdp_record
		r['mcap_control_psm'] = self.cpsm
                r['mcap_data_psm'] = self.dpsm
                r['name'] = 'HDPy'
                r['provider'] = 'HDPy'
                r['description'] = 'HDPy'

		procedures = []
		if self.reconn_enabled:
			procedures.append('reconnect_init')
			procedures.append('reconnect_accept')
		if self.csp_enabled:
			procedures.append('csp')
			procedures.append('csp_master')

                r['mcap_procedures'] = tuple(procedures)

		xml_record = hdp_record.gen_xml(self.sdp_record)
		self.sdp_handle = BlueZ().add_record("any", xml_record)

	def unpublish(self):
		"""Unpublish SDP
		"""
		if not self.sdp_handle:
			return
		try:
			BlueZ().remove_record("any", self.sdp_handle)
		except:
			pass
		self.sdp_handle = None

	def suspend(self):
		"""Reversible 'stopping'
		"""
		if self.suspended:
			return

		while self.devices:
			self.remove_device(self.devices[-1])

		self.unpublish()
		MCAPInstance.stop(self)
		self.suspended = True

	def resume(self):
		"""Resume operations
		"""
		if not self.suspended:
			return

		self.suspended = False
		MCAPInstance.start(self)
		self.publish()

	def stop(self):
		"""Irreversible stop
		"""
		self.suspend()

		self.stopped = True
		BlueZ().unregister_observer(self)

	def channel_by_mdl(self, mdl):
		"""Returns the channel referenced to a mdl.
		@param mdl: MDL object.
		@type mdl: MDL object.
		@return: A HealthChannel object.
		"""
		channel = self.got_channel_by_mdl(mdl)
		if not channel:
			DBG(1, "WARNING: No channel for the given MDL")
		return channel

	def got_channel_by_mdl(self, mdl):
		channel = None
		for candidate in self.channels:
			if candidate.mdl is mdl:
				channel = candidate
				break
		return channel

	def create_channel(self, mdl, acceptor):
		"""Creates a HealthChannel object.
		@param mdl: MDL object.
		@type mdl: MDL object.
		@param acceptor: Acceptor object.
		@type acceptor: Acceptor object.
		@return: A HealthChannel object.
		"""
		device = self.device_by_mcl(mdl.mcl)
		channel = HealthChannel(device, mdl, acceptor)
		self.add_channel(channel)
		return channel

	def add_channel(self, channel):
		"""Adds a channel to the channel list.
		@param channel: The channel to be added.
		@type channel: HealthChannel.
		"""
		if channel not in self.channels:
			self.channels.append(channel)

	def remove_channel(self, channel):
		"""Removes a channel from the channel list.
		@param channel: The channel to be removed.
		@type channel: HealthChannel.
		"""
		try:
			self.channels.remove(channel)
		except ValueError:
			DBG(0, "WARNING: Channel unknown, not removed")

	def device_by_mcl(self, mcl):
		"""Returns a HealthDevice based on a mcl referenced to it.
		@param mcl: MCL object.
		@type mcl: MCL object.
		@return: A HealthDevice object.
		"""
		device = None
		for candidate in self.devices:
			if candidate.mcl is mcl:
				device = candidate
				break
		if not device:
			# Case when we are acceptors of MCL
			device = self.create_device_by_mcl(mcl)
		return device

	def create_device_by_mcl(self, mcl):
		"""Creates and returns a HealthDevice based on a mcl object.
		@param mcl: MCL object.
		@type mcl: MCL object.
		@return: A HealthDevice object.
		"""
		device = HealthDevice(self, mcl.remote_addr,
					mcl.remote_addr_dc, 0)
		self.add_device(device)
		return device

	def create_device(self, bdaddr, cpsm, dpsm, mdepid):
		"""Creates a device based on its address, cpsm, dpsm and mdepid.
		@param bdaddr: Device address.
		@type bdaddr: String.
		@param cpsm: cpsm.
		@type cpsm: Integer.
		@param dpsm: dpsm.
		@type dpsm: Integer.
		@param mdepid: mdepid.
		@type mdepid: Integer.
		@return: A HealthDevice object.
		"""
		if self.match_device(bdaddr, cpsm, dpsm, mdepid):
			DBG(0, "Warning: creating and adding HealthDevice" \
				"with same characteristics as old one")

		control_addr = (bdaddr, cpsm)
		data_addr = (bdaddr, dpsm)
		device = HealthDevice(self, control_addr, data_addr, mdepid)
		self.add_device(device)
		DBG(3, "Creating discovered srv %s %d %d" % \
			(bdaddr, cpsm, mdepid))
		return device

	def match_device(self, bdaddr, cpsm, dpsm, mdepid):
		"""Returns a HealthDevice based on its address, cpsm, dpsm and mdepid.
		@param bdaddr: Device address.
		@type bdaddr: String.
		@param cpsm: cpsm.
		@type cpsm: Integer.
		@param dpsm: dpsm.
		@type dpsm: Integer.
		@param mdepid: mdepid.
		@type mdepid: Integer.
		@return: A HealthDevice object.
		"""
		for device in self.devices:
			if device.bdaddr() == bdaddr and \
					device.cpsm() == cpsm and \
					device.dpsm() == dpsm and \
					device.mdepid == mdepid:
				return device
		return None

	def remove_old_devices(self, bdaddr, new_devices):
		"""Removes old devices based on its address and based on a list of new
		devices.
		@param bdaddr: Device address.
		@type bdaddr: String.
		@param new_devices: A list of new devices.
		@type new_devices: List.
		"""
		for device in self.devices:
			if device.bdaddr() == bdaddr and \
					device not in new_devices:
				self.remove_device(device)

	def add_device(self, device):
		"""Add a device to a list.
		@param device: The device to be added to the device list.
		@type device: HealthDevice object.
		"""
		if device not in self.devices:
			self.devices.append(device)
			self.manager.signal("DeviceFound", self,
						"org.bluez", device)

	def remove_device(self, device):
		"""Remove a device from the device list.
		@param device: The device to be added to a list.
		@type device: HealthDevice object.
		"""
		try:
			device.kill()
			self.devices.remove(device)
			self.manager.signal("DeviceDisappeared", self,
				"org.bluez", device)
		except ValueError:
			DBG(0, "Warning: device %s unkown, not removed")

	def MCLConnected(self, mcl, err):
		"""Called when MCL connects.
		@param mcl: MCL object connected.
		@type mcl: MCL object.
		@param err: Error string.
		@type err: String.
		"""
		if self.stopped:
			return

		device = self.device_by_mcl(mcl)
		device.mcl_connected(mcl, err, False)

	def MCLDisconnected(self, mcl):
		"""Called when MCL disconnects.
		@param mcl: MCL object disconnected.
		@type mcl: MCL object.
		"""
		if self.stopped:
			return

		device = self.device_by_mcl(mcl)
		device.mcl_disconnected(mcl)

	def MCLReconnected(self, mcl, err):
		"""Called when MCL reconnects.
		@param mcl: MCL object reconnected.
		@type mcl: MCL object.
		@param err: Error string.
		@type err: String.
		"""
		if self.stopped:
			return

		device = self.device_by_mcl(mcl)
		device.mcl_connected(mcl, err, True)

	def MCLUncached(self, mcl):
		"""Called when MCL uncaches.
		@param mcl: MCL object uncached.
		@type mcl: MCL object.
		"""
		if self.stopped:
			return

		device = self.device_by_mcl(mcl)
		device.mcl_deleted(mcl)

	def MDLInquire(self, mdepid, config):
		"""Verifies if MDL is ok, if it is reliable. Returns a tuple containing
		ok and reliable booleans and configuration.
		"""
		if self.stopped:
			return

		ok = True

		if mdepid == 0:
			# echo channel
			config = config or 0x01
			reliable = (config == 0x01)
			return ok, reliable, config

		if mdepid != self.mdepid:
			DBG(1, "requested MDEP ID %d not in our list" % mdepid)
			ok = False

		if self.sink:
			if not config:
				DBG(1, "Remote side should have chosen config, nak")
				ok = False
		else:
			if config:
				DBG(1, "other side is Sink, but chose config %d" % config)
				ok = False

			# TODO this is an ugly solution to please PTS streaming test.
			#	Need to think in a better way to call upper levels.
			config = self.manager.signal("InquireConfig", self,
					"tmp", [mdepid, config, self.sink])
			if not config:
				DBG(1, "Application did not return config via InquireConfig")
				ok = False

		reliable = (config == 0x01)

		return ok, reliable, config

	def MDLReady(self, mcl, mdl, err):
		"""MDL is Ready, so connect MDL.
		"""
		if self.stopped:
			return

		if err:
			device = self.device_by_mcl(mcl)
			device.mdl_ready(mdl, err)
			return

		# Nothing to do except go ahead
		self.ConnectMDL(mdl)

	def MDLRequested(self, mcl, mdl, mdep_id, conf):
		DBG(1, "HDP: MDLRequested: conf %d" % conf)
		return (conf == 0x01)

	def MDLReconnected(self, mdl):
		# we are only interested in MDLConnected
		pass

	def MDLAborted(self, mcl, mdl):
		# we do not initiate AbortMDL() and 
		# we are only interested in MDLConnected
		pass

	def MDLConnected(self, mdl, err):
		"""Called when MDL is connected.
		@param mdl: MDL object connected.
		@type mdl: MDL object.
		@param err: Error string.
		@type err: String.
		"""
		if self.stopped:
			return

		device = self.device_by_mcl(mdl.mcl)
		channel = self.got_channel_by_mdl(mdl)
		reconn = channel is not None

		if err:
			device.mdl_connected(mdl, channel, reconn, err)
			return

		if mdl.mdepid == 0:
			return self.MDLConnectedEcho(mdl)

		if mdl.acceptor:
			if mdl.mdepid != self.mdepid:
				DBG(1, "MDLConnected: bad MDEP ID received")
				mdl.close()
				return

		if not reconn:
			channel = self.create_channel(mdl, mdl.acceptor)

		if mdl.acceptor:
			self.manager.signal("ChannelConnected", device,
				"org.bluez.HealthDevice", channel)

		device.mdl_connected(mdl, channel, reconn, err)

	def MDLConnectedEcho(self, mdl):
		ok = not not mdl.sk
		if ok:
			watch_fd(mdl.sk, self.echo_watch, mdl)

		if not mdl.acceptor:
			device = self.device_by_mcl(mdl.mcl)
			device.mdlecho_connected(mdl, ok)

	def echo_watch(self, sk, evt, mdl):
		data = ""
		if evt & IO_IN:
			try:
				data = sk.recv(65535)
			except IOError:
				data = ""

		if not mdl.acceptor:
			device = self.device_by_mcl(mdl.mcl)
			device.mdlecho_pong(mdl, data)
		else:
			if data:
				# send back the same data and close
				mdl.write(data)

		try:
			self.DeleteMDL(mdl)
		except InvalidOperation:
			pass

		return False

	def MDLDeleted(self, mdl):
		if self.stopped:
			return

		if mdl.mdepid == 0:
			return

		channel = self.got_channel_by_mdl(mdl)
		if channel:
			device = self.device_by_mcl(mdl.mcl)
			self.remove_channel(channel)
			self.manager.signal("ChannelDeleted", device,
				"org.bluez.HealthDevice", channel)

	def MDLClosed(self, mdl):
		# Application discovers this via fd closure
		pass

	### No public HealthApplication API


class QueueItem(object):
	'''
	This is an auxiliary class that represents a queued
	operation.

	operation: function/method to be called when queue dispatches.
	Prototype is op(arg, queue_item)
	arg: a single argument for operation. May be a tuple if several
	arguments must be passed, but it is NOT expanded.
	cb_ok, cb_nok: callbacks to be notified on success or failure,
	respectively
	ident: some 'cargo' data that may be needed when async operation
	completes, so we can check if the completed operation
	matches with the queue item being processed.
	'''
	def __init__(self, operation, arg, cb_ok, cb_nok, ident):
		self.operation = operation
		self.arg = arg
		self.cb_ok = cb_ok
		self.cb_nok = cb_nok
		self.ident = ident

	def start(self):
		self.operation(self.arg, self)

	def ok(self, *args):
		if self.cb_ok:
			self.cb_ok(*args)
			self.cb_ok = None

	def nok(self, *args):
		if self.cb_nok:
			self.cb_nok(*args)
			self.cb_nok = None


class HealthDevice(object):
	'''
	The HealthDevice represents a single (endpoint,
	role, data_type) in the remote device.

	Each device is bound to a given HealthApplication object, so
	data_type and role are implicitly defined (being the remote device's
	role the opposite of our application's).

	The MDEP ID is also known by this class, if the remote device
	publishes a SDP record. If not, or if this device is created
	automatically when we are acceptors, MDEP ID is zero.
	'''

	# Current queue processing status
	# Note that LSB bit is 1 when something is mid-flight

	IDLE = 0	# state only allowed when queue is empty
	DISPATCH = 2	# ready for next command to be dispatched
	WAITING_MCL = 3 # waiting for MCL connection
	MCL_UP = 4	# waited MCL connection is up
	WAITING_MDL = 5 # waiting for MDL; used by _Echo() only
	MDL_UP = 6	# waited MDL connection is up
	IN_FLIGHT = 7	# finally doing what it was meant to do

	# Events

	CONNECTION = 1
	DISCONNECTION = 2
	DELETION = 3
	MDL_READY = 4
	MDL_CONNECTION = 5
	MDL_ECHO_CONNECTION = 6

	def __init__(self, app, addr_control, addr_data, mdepid):
		self.addr_control = addr_control
		self.addr_data = addr_data
		self.mdepid = mdepid
		self.app = app
		self.mcl = None
		self.queue = []
		self.queue_status = self.IDLE
		self.valid = True
		self.mdl_echo = None

	def bdaddr(self):
		return self.addr_control[0]

	def cpsm(self):
		return self.addr_control[1]

	def dpsm(self):
		return self.addr_data[1]

	def pending(self):
		if (self.queue_status == self.IDLE and self.queue) or \
		    (self.queue_status != self.IDLE and not self.queue):
			DBG(1, "Warning: Invalid queue state")

		if not self.queue or not (self.queue_status % 2):
			return None

		return self.queue[0]

	def mcl_connected(self, mcl, err, reconn):
		'''
		Called back by app when related MCL is connected
		'''
		self.mcl = mcl
		self.queue_event_process(self.CONNECTION, err)

	def mcl_disconnected(self, mcl):
		'''
		Called back by app when MCL is disconnected
		'''
		self.queue_event_process(self.DISCONNECTION, 0)

	def mcl_deleted(self, mcl):
		'''
		Called back by app when MCL is invalidated
		'''
		self.mcl = None
		self.queue_event_process(self.DELETION, 0)

	def mdl_ready(self, mdl, err):
		'''
		Called back by app when MDLReady triggers
		'''
		self.queue_event_process(self.MDL_READY, err)

	def mdl_connected(self, mdl, channel, reconn, err):
		'''
		Called back by app when MDLConnected triggers
		'''
		self.queue_event_process(self.MDL_CONNECTION, err,
			{"channel": channel, "reconn": reconn})

	def mdlecho_connected(self, mdl, ok):
		'''
		Called back when an Echo MDL initiated by us has connected
		'''
		self.queue_event_process(self.MDL_ECHO_CONNECTION, 0,
			{"mdl": mdl, "ok": ok})

	def mdlecho_pong(self, mdl, data):
		'''
		Called back when an Echo MDL returned data
		'''
		pending = self.pending()
		if not pending:
			return False

		if pending.operation == self.__Echo:
			self.mdl_echo = None
			if data == pending.ident:
				pending.ok()
			else:
				pending.nok(-99)
			self.queue_flush()

		return False

	def stop(self):
		'''
		Called back by app when it is being stopped
		'''
		self.queue = []
		self.queue_state = self.IDLE

	def kill(self):
		self.stop()
		if self.mcl:
			self.app.DeleteMCL(self.mcl)
		self.valid = False
		self.mcl = None
		self.app = None

	def queue_event_process(self, event, err, details={}):
		'''
		Handles queue in face of events
		'''
		DBG(3, "queue_event_process %d %d" % (event, err))

		if not self.queue or not event:
			return

		if err:
			self.queue_fail(err)
			return

		if event == self.CONNECTION:
			self.queue_mcl_conn_up()

		elif event == self.DISCONNECTION:
			self.queue_fail(-998)

		elif event == self.DELETION:
			self.queue_fail(-999)

		elif event == self.MDL_READY:
			pass

		elif event == self.MDL_CONNECTION:
			self.queue_mdl_conn_up(details["channel"],
						details["reconn"])

		elif event == self.MDL_ECHO_CONNECTION:
			self.queue_mdl_echo_conn_up(details["mdl"], \
							details["ok"])

	def queue_mcl_conn_up(self):
		'''
		Called when a connection is successful
		'''
		DBG(3, "queue_mcl_conn_up")

		if self.queue_status == self.WAITING_MCL:
			self.queue_status = self.MCL_UP

		self.queue_dispatch()

	def queue_mdl_conn_up(self, channel, reconn):
		DBG(3, "queue_mdl_conn_up %s %s" % (str(channel), str(reconn)))

		pending = self.pending()
		if not pending:
			return

		op = pending.operation

		if (not reconn) and (op == self.__CreateChannel):
			DBG(3, "\tRequested channel created")
			mdlid = channel.mdl.mdlid
			if pending.ident == mdlid:
				pending.ok(channel)
				self.queue_flush()
			else:
				DBG(1, "queue_mdl_conn_up bad ID %d" % mdlid)

		if reconn and (op == self.__ReconnectChannel):
			if channel is pending.ident:
				pending.ok()
				self.queue_flush()
			else:
				DBG(1, "queue_mdl_conn_up reconn diff chan")

	def queue_mdl_echo_conn_up(self, mdl, ok):
		DBG(3, "queue_mdl_echo_conn_up")

		if self.queue_status == self.WAITING_MDL:
			self.queue_status = self.MDL_UP

		self.mdl_echo = mdl
		self.queue_dispatch()

	def queue_fail(self, err):
		DBG(3, "queue_fail")

		pending = self.pending()
		if pending:
			pending.nok(err)
			self.queue_flush()
		else:
			self.queue_dispatch()

	def queue_flush(self):
		DBG(3, "queue_flush")

		del self.queue[0]
		self.queue_status = self.DISPATCH
		self.queue_priv = None
		self.queue_dispatch()

	def queue_dispatch(self):
		DBG(3, "queue_dispatch")

		if not self.queue:
			self.queue_status = self.IDLE
			return False

		if self.queue_status == self.IDLE:
			# Fix queue status
			self.queue_status = self.DISPATCH

		if self.pending():
			# waiting for something to happen
			return False

		if not self.mcl or not self.mcl.active():
			# we can't do nothing if MCL is not up
			self.queue_status = self.WAITING_MCL
			self.mcl = self.app.CreateMCL(self.addr_control,
						self.dpsm())
			return False

		if not self.mcl.clear_to_send():
			# some other MCL operation in flight, might have been
			# initiated by remote, we wait a bit and try again
			timeout_call(1000, self.queue_dispatch)
			return False

		if self.queue[0].operation == self.__Echo and not self.mdl_echo:
			# for Echo, we need the echo MDL up, too
			self.queue_status = self.WAITING_MDL
			mdlid = self.app.CreateMDLID(self.mcl)
			self.app.CreateMDL(self.mcl, mdlid, 0, 1, True)
			return False

		DBG(3, "queue: executing")
		self.queue_status = self.IN_FLIGHT
		self.queue[0].start()

		return False

	def enqueue(self, op, arg, reply, error, ident=None):
		qitem = QueueItem(op, arg, reply, error, ident)
		self.queue.append(qitem)
		self.queue_dispatch()

	def _Echo(self, reply_handler, error_handler):
		self.enqueue(self.__Echo, None, reply_handler, error_handler)

	def __Echo(self, dummy, queueop):
		length = random.randint(1, 48)
		data = [ chr(random.randint(0, 255)) for x in range(0, length) ]
		data = "".join(data)
		queueop.ident = data

		if not self.mdl_echo.write(data):
			# if socket is invalid, would never return feedback
			# so we schedule a clearly invalid "response"
			schedule(0, self.mdlecho_pong, mdl, "")

	def _CreateChannel(self, conf, reply_handler, error_handler):
		reliable = (conf == 0x01)
		self.enqueue(self.__CreateChannel, (conf, reliable),
				reply_handler, error_handler)

	def __CreateChannel(self, args, queueop):
		conf, reliable = args
		mdlid = self.app.CreateMDLID(self.mcl)
		queueop.ident = mdlid
		self.app.CreateMDL(self.mcl, mdlid, self.mdepid, conf, reliable)

	def _DeleteChannel(self, channel):
		self.enqueue(self.__DeleteChannel, channel, None, None)

	def __DeleteChannel(self, channel, queueop):
		self.app.DeleteMDL(channel.mdl)

	def _ReconnectChannel(self, channel, reply_handler, error_handler):
		self.enqueue(self.__ReconnectChannel, channel,
				reply_handler, error_handler)

	def __ReconnectChannel(self, channel, queueop):
		mdl = channel.mdl
		queueop.ident = channel
		self.app.ReconnectMDL(mdl)

	def CloseMCL(self):
		self.app.CloseMCL(self.mcl)

	# Public API

	def Echo(self, reply_handler, error_handler):
		"""Sends an echo petition to the remote service.
		@param reply_handler: A function to handle the reply.
		@type reply_handler: function.
		@param error_handler: A function to handle errors.
		@type error_handler: function.
		"""
		self._Echo(reply_handler, error_handler)

	def CreateChannel(self, app, conf, reply_handler, error_handler):
		"""Creates a new data channel with the indicated config to the
		remote Service. The configuration 'conf' should indicate the channel
		quality of service using one of this values "Reliable", "Streaming" or
		"Any".
		@param app: Application.
		@type app: Object.
		@param conf: Configuration to create a channel.
		@type conf: Integer.
		@param reply_handler: A function to handle the reply.
		@type reply_handler: function.
		@param error_handler: A function to handle errors.
		@type error_handler: function.
		"""

		if app and (app is not self.app):
			raise HealthError("Creating channel with a different" +
					"application is not supported")

		try:
			conf = {"Reliable": 1, "Streaming": 2, "Any": 0}[conf]
		except KeyError:
			raise HealthError("Invalid channel config")

		self._CreateChannel(conf, reply_handler, error_handler)

	def DestroyChannel(self, channel):
		"""Destroys (deletes) a given data channel.
		@param channel: Data channel to destroy.
		@type channel: Object.
		@return: True if the channel is destroyed.
		"""
		if channel.device is not self:
			raise HealthError("Channel does not belong to this device")

		if channel.valid:
			channel.valid = False
			self._DeleteChannel(channel)

		return True


class HealthChannel(object):
	def __init__(self, device, mdl, acceptor):
		self.device = device
		self.mdl = mdl
		self.acceptor = acceptor
		self.valid = True

	def GetProperties(self):
		if not self.valid:
			raise HealthError("Data channel deleted")
		data_type = self.mdl.reliable and "Reliable" or "Streaming"
		return {"Type": data_type, "Device": self.device}

	def Acquire(self, reply_handler, error_handler):
		if not self.valid:
			raise HealthError("Data channel deleted")

		if self.mdl.active():
			schedule(reply_handler, self.mdl.sk)
			return

		# Pass this closure as reply handler
		def reconnected():
			reply_handler(self.mdl.sk)

		self.device._ReconnectChannel(self, reconnected,
							error_handler)

	def Release(self):
		self.mdl.close()

	def stop(self):
		self.Release()


# FIXME capture all "normal" InvalidOperation exceptions
