#!/usr/bin/env python

import hdp_record

feature1 = {'mdep_id': 0x01, 'role': 'source',
		'data_type': 0x1004, 'description': "Fake oximeter"}
feature2 = {'mdep_id': 0x01, 'role': 'source', 'data_type': 0x4005}
feature3 = {'mdep_id': 0x02, 'role': 'sink', 'data_type': 0x4006}
feature4 = {'mdep_id': 0x04, 'role': 'sink', 'data_type': 0x4007}
# features = [feature1, feature2, feature3, feature4]
features = [feature1]
hdp = {'features': features}
hdp['mcap_control_psm'] = 0x1001
hdp['mcap_data_psm'] = 0x1003
hdp['name'] = "Fake oximeter"
hdp['description'] = "A fake HDP record"
hdp['provider'] = "Epx Inc."
hdp['mcap_procedures'] = ('csp', 'csp_master', 'reconnect_init', \
				'reconnect_accept')
print hdp_record.gen_xml(hdp)
