# -*- coding: utf-8

################################################################
#
# Copyright (c) 2010 Signove. All rights reserved.
# See the COPYING file for licensing details.
#
# Autors: Elvis Pfützenreuter < epx at signove dot com >
#         Raul Herbster < raul dot herbster at signove dot com >
################################################################

def s2b(msg):
	if msg is None:
		return None
	return [ord(x) for x in msg]

def b2s(msg):
	if msg is None:
		return None
	return "".join([chr(int(x)) for x in msg])

def test():
	s = chr(0xe2) + "ABCDE\0\1\2"
	b = [0xe2, 65, 66, 67, 68, 69, 0, 1, 2]
	assert(b == s2b(s))
	assert(s == b2s(b))
	assert(b == s2b(b2s(b)))
	assert(s == b2s(s2b(s)))
	assert("" == b2s(None))
	assert([] == s2b(None))
	print "Test ok"

if __name__ == '__main__':
	test()
