#!/usr/bin/env python

import mcap_defs
import mcaptest
import mcap
import sys
import time

btaddr = sys.argv[1]

mcl = mcap.MCL(btaddr, mcap.MCAP_MCL_ROLE_ACCEPTOR)

mcap_session = mcap.MCAPImpl(mcl)

assert(mcap_session.mcl.state == mcap.MCAP_MCL_STATE_IDLE)

# wait until a connection is done
print "Waiting for connections on " + btaddr
mcap_session.init_session()

print "Connection on " + str(mcap_session.mcl.psm)

assert(mcap_session.mcl.state == mcap.MCAP_MCL_STATE_CONNECTED)

print "Start thread... "
if ( mcl.is_cc_open() ):
	mcap_session.start()
else:
	raise Exception ('ERROR: Cannot open control channel for acceptor')

mcap_session.join()

print "Thread closed..."

print 'TESTS OK' 
