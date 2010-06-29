#!/usr/bin/env python
# -*- coding: utf-8

################################################################
#
# Copyright (c) 2010 Signove. All rights reserved.
# See the COPYING file for licensing details.
#
# Autors: Elvis Pfützenreuter < epx at signove dot com >
#         Raul Herbster < raul dot herbster at signove dot com >
################################################################

import hdp_record
import sys

if len(sys.argv) > 1:
	xml = open(sys.argv[1]).read()
else:
	xml = sys.stdin.read()

print hdp_record.parse_xml(xml)
