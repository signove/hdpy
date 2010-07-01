# -*- coding: utf-8

################################################################
#
# Copyright (c) 2010 Signove. All rights reserved.
# See the COPYING file for licensing details.
#
# Autors: Elvis Pfützenreuter < epx at signove dot com >
#         Raul Herbster < raul dot herbster at signove dot com >
################################################################

#From IEEE Standard 11073-10404 page 62

assoc_resp_msg = (0xe3, 0x00, #APDU CHOICE Type(AareApdu)
                  0x00, 0x2c, #CHOICE.length = 44
                  0x00, 0x00, #result=accept
                  0x50, 0x79, #data-proto-id = 20601
                  0x00, 0x26, #data-proto-info length = 38
                  0x80, 0x00, 0x00, 0x00, #protocolVersion
                  0x80, 0x00, #encoding rules = MDER
                  0x80, 0x00, 0x00, 0x00, #nomenclatureVersion
                  0x00, 0x00, 0x00, 0x00, #functionalUnits, normal Association
                  0x80, 0x00, 0x00, 0x00, #systemType = sys-type-manager
                  0x00, 0x08, #system-id length = 8 and value (manufacturer- and device- specific) 
                  0x88, 0x77, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11,
                  0x00, 0x00, #Manager's response to config-id is always 0
                  0x00, 0x00, #Manager's response to data-req-mode-flags is always 0
                  0x00, 0x00, #data-req-init-agent-count and data-req-init-manager-count are always 0
                  0x00, 0x00, 0x00, 0x00) #optionList.count = 0 | optionList.length = 0

assoc_rel_resp = (0xe5, 0x00, #APDU CHOICE Type(RlreApdu)
                  0x00, 0x02, #CHOICE.length = 2
                  0x00, 0x00) #reason = normal

def parse_message(msg):
    global assoc_resp_msg
    global assoc_rel_resp

    resp = ()
    if int(msg[0]) == 0xe2:
        print 'Association request\n'
        resp = assoc_resp_msg
    elif int(msg[0])==0xe7:
        print 'Data received\n'
        resp = (0xe7, 0x00, #APDU CHOICE Type(PrstApdu)
                0x00, 0x12, #CHOICE.length = 18
                0x00, 0x10, #OCTET STRING.length = 16
                int(msg[6]), int(msg[7]), #invoke-id (mirrored from invocation) 
                0x02, 0x01, #CHOICE(Remote Operation Response | Confirmed Event Report)
                0x00, 0x0a, #CHOICE.length = 10
                0x00, 0x00, #obj-handle = 0 (MDS object)
                0x00, 0x00, 0x00, 0x00, #currentTime = 0
                0x0d, 0x1d, #event-type = MDC_NOTI_SCAN_REPORT_FIXED
                0x00, 0x00) #event-reply-info.length = 0
        
        weight = (16*16*int(msg[42]) + int(msg[43]))/10.0
        bmi = (16*16*int(msg[74]) + int(msg[75]))/10.0
        body_fat = (16*16*int(msg[90]) + int(msg[91]))/10.0
        meta = 16*16*int(msg[106]) + int(msg[107])
        body_age = 16*16*int(msg[134]) + int(msg[135])
        age = int(msg[59])
        vis_fat = int(msg[121])/10.0
        skeletal_muscle = None

        print '\nDate: %x%x, %x-%x' % (msg[60], msg[61], msg[62], msg[63])
        print 'Time: %x:%x:%x%x' % (msg[64], msg[65], msg[66], msg[67])
        print 'Body age: %d, real age %d,' % (body_age, age)
        print 'Weight: %g, BMI: %g, Body Fat: %g,' % (weight, bmi, body_fat)
        print 'Resting Metabolism: %d, Visceral Fat: %g\n' %  (meta, vis_fat)

    elif int(msg[0])==0xe4:
        print 'Association release request\n'
        resp = assoc_rel_resp

    return resp
