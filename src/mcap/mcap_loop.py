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

import glib

IO_IN = glib.IO_IN
IO_OUT = glib.IO_OUT
IO_ERR = glib.IO_ERR
IO_HUP = glib.IO_HUP
IO_NVAL = glib.IO_NVAL

def io_in(n):
	return n & IO_IN

def io_out(n):
	return n & IO_OUT

def io_err(n):
	return n & IO_ERR or n & IO_HUP or n & IO_NVAL

def watch_fd(sk, cb, *args):
	return glib.io_add_watch(sk, IO_IN | IO_ERR | IO_HUP | IO_NVAL,
					cb, *args)

def watch_fd_connect(sk, cb, *args):
	return glib.io_add_watch(sk, IO_OUT | IO_ERR | IO_HUP | IO_NVAL,
					cb, *args)

def watch_fd_err(sk, cb, *args):
	return glib.io_add_watch(sk, IO_ERR | IO_HUP | IO_NVAL,
					cb, *args)

def watch_cancel(handle):
	return glib.source_remove(handle)

def timeout_call(to, cb, *args):
	return glib.timeout_add(to, cb, *args)

def timeout_cancel(handle):
	return glib.source_remove(handle)

def idle_call(cb, *args):
	return glib.idle_add(cb, *args)

sync_events = False

# Enable this if you want to debug events synchonously
# sync_events = True

def schedule(cb, *args):
	if sync_events:
		cb(*args)
		return
	def closure():
		cb(*args)
		return False
	return idle_call(closure)
