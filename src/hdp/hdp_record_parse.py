#!/usr/bin/env python

import hdp_record
import sys

if len(sys.argv) > 1:
	xml = open(sys.argv[1]).read()
else:
	xml = sys.stdin.read()

print hdp_record.parse_xml(xml)
