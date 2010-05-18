#!/usr/bin/env python

import hdp_record

sample = open("record_sample1.xml").read()
record1 = hdp_record.parse_xml(sample)[0]
record2 = hdp_record.parse_xml(hdp_record.gen_xml(record1))[0]
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
hdp2 = hdp_record.parse_xml(hdp_record.gen_xml(hdp), True)[0]

assert(hdp['features'] == hdp2['features'])
assert(hdp == hdp2)
print "Ok"
