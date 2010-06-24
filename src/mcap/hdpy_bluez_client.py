#!/usr/bin/env python

from mcap_instance import MCAPInstance
from mcap_defs import *
#import time
import sys
import glib

loop = glib.MainLoop()

class MyInstance(MCAPInstance):

    def __init__(self, adapter, listener):
        MCAPInstance.__init__(self, adapter, listener)
        self.counter = 0
#        self.ping_counter = 50
        self.send_script = []
        self.sent = []
        self.received = []

    def bye(self):
        if self.counter >= len(self.send_script):
            print 'TESTS OK'
        else:
            print 'DID NOT COMPLETE ALL TESTS'
        glib.MainLoop.quit(loop)

    def take_initiative(self, mcl, mdl=None):
        if self.counter >= len(self.send_script):
            self.bye()
        else:
            print '############ runing %d/%d' % (self.counter + 1, len(self.send_script))
            to = 1000
            print "############ counter", self.counter
            if self.counter == 4:
                to = 2000
            glib.timeout_add(to, self.take_initiative_cb, mcl, mdl)

    def take_initiative_cb(self, mcl, mdl, *args):
        action = self.send_script[self.counter]
        method = action[0]
        if method in [MyInstance.DeleteMDL, MyInstance.ConnectMDL,
                MyInstance.ReconnectMDL]:
            method(self, mdl)
        elif method in [MyInstance.SendOnce, MyInstance.SendAndWait]:
            if mdl:
                method(self, mdl, *action[1:])
        else:
            method(self, mcl, *action[1:])

        # It is important to return False.
        return False

    def SendOnce(self, mdl, data):
        self.Send(mdl, data)
        self.check_asserts(self, mdl.mcl)
        self.counter += 1
        self.take_initiative(mdl.mcl, mdl)

    def SendAndWait(self, mdl, data):
        self.Send(mdl, data)

    def check_asserts(self, mcap, mcl):
        pass

    def MDLReady_post(self, mdl):
        self.ConnectMDL(mdl)

#    def ping(self, mdl):
#        self.ping_counter -= 1
#        if self.ping_counter < 0:
#            self.CloseMDL(mdl)
#            return False
#
#        if not mdl.active():
#            return False
#        mdl.write("hdpy ping ")
#        return True

    ### Overriden callback methods

    def Recv(self, mdl, data):
        print "MDL received from %s, the data: %s" % (id(mdl), data)
        assert(self.received[self.counter] == data)
        self.counter += 1
        self.take_initiative(mdl.mcl, mdl)
#        return True

    def MCLConnected(self, mcl):
        print "MCL has connected"
        self.take_initiative(mcl)

    def MCLDisconnected(self, mcl):
        print "MCL has disconnected"
        self.bye()

    def MCLReconnected(self, mcl):
        print "MCLReconnected not overridden"

    def MCLUncached(self, mcl):
        print "MCLUncached not overridden"

    def MDLReady(self, mcl, mdl):
#        if mdl.mdlid == 0x27:
#            print "MDL ready but not connecting"
#            self.take_initiative(mdl.mcl)
#        else:
        print "MDL ready, connecting"
        glib.timeout_add(0, self.MDLReady_post, mdl)

    def MDLRequested(self, mcl, mdl, mdep_id, conf):
        ''' Followed by MDLAborted or MDLConnected '''
        print "MDLRequested not overridden"

    def MDLAborted(self, mcl, mdl):
        print "MDLAborted not overridden"

    def MDLConnected(self, mdl):
        print "MDL connected"
#        glib.timeout_add(1500, self.ping, mdl)
        self.take_initiative(mdl.mcl, mdl)

    def MDLDeleted(self, mdl):
        print "MDLDeleted not overridden"

    def MDLClosed(self, mdl):
        print "MDL closed"

    def MDLReconnected(self, mdl):
        print "MDLReconnected not overridden"

    def RecvDump(self, mcl, message):
        print "Received raw msg", repr(message)
        expected_msg = testmsg(self.received[self.counter])
        assert(message == expected_msg)
        self.check_asserts(self, mcl)
        self.counter += 1
        if message[0:2] != "\x02\x00":
            self.take_initiative(mcl)
        else:
            # delay until we open MDL
            pass
        return True

    def SendDump(self, mcl, message):
        print "Sent", repr(message)
        expected_msg = testmsg(self.sent[self.counter])
        assert(message == expected_msg)
        return True

def run_test(send_script, sent, received, check_asserts):
    try:
        remote_addr = sys.argv[1], int(sys.argv[2])
        dpsm = int(sys.argv[3])
    except:
        remote_addr = '00:1B:10:02:BF:3B', 4113
        dpsm = 4115
    instance = MyInstance('00:00:00:00:00:00', False)
    instance.send_script = send_script
    instance.sent = sent
    instance.received = received
    if (check_asserts):
        instance.check_asserts = check_asserts
    print 'Connecting...'
    instance.CreateMCL(remote_addr, dpsm)
    loop.run()
