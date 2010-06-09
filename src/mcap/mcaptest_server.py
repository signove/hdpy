#!/usr/bin/env python

import mcap_defs
import mcaptest
import mcap
import sys
import time
import gobject

btaddr = sys.argv[1]

mcl = mcap.MCL(btaddr, mcap.MCAP_MCL_ROLE_ACCEPTOR)

mcap_session = mcap.MCAPSession(mcl)

assert(mcl.state == mcap.MCAP_MCL_STATE_IDLE)

# wait until a connection is done
print "Waiting for connections on " + btaddr
mcl.open_cc()

print "Connected!"
mcap_session.start_session()
assert(mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)

print "Start main loop... "
if ( mcl.is_cc_open() ):
	gobject.MainLoop().run()
else:
	raise Exception ('ERROR: Cannot open control channel for acceptor')

print "Finished!"

print 'TESTS OK' 
