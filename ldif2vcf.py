#!/usr/bin/python
# -*- coding: utf-8 -*-

# This little script is mostly useful as an example of how to do
# this kind of convertion and only suited for my company as it uses
# custom schemas.

import os
import re
import sys
import optparse
from ldif import ParseLDIF
from sjutils.utils import paginate

VERSION = "0.1.0"

def format_picture(pic_data, pic_type):
    """ Convert @pic_data to base64 and align properly with VCard prefix.

    pic_type: one of JPEG or PNG
    """
    pic_b64 = ''.join(pic_data.encode('base64').strip().split('\n'))
    prefix = "PHOTO;ENCODING=b;TYPE=%s:" % pic_type
    pic_lines = []
    pic_lines += [' %s' % ''.join(list(line)) for line in paginate(pic_b64[75-len(prefix):], 74)]
    picture = prefix + pic_b64[0:75-len(prefix)] + '\n'
    picture += '\n'.join(pic_lines) + '\n'
    return picture

def ldif2vcf(ldif_path, company):
    """ Crazy main function """

    with open(ldif_path) as ldif_fd:
        records = ParseLDIF(ldif_fd)

    for _, record in records:
        skip = False

        # Not a real user
        for attribute in ('sn', 'mail', ):
            if attribute not in record:
                skip = True
                break
        
        if skip:
            continue

        record['company'] = company or "None"

        for attribute in ('sn', 'givenName', ):
            attr_split = record[attribute][0].split('-')
            record[attribute] = '-'.join([attr.capitalize() for attr in attr_split])

        # Rewrite gecos as it is badly formatted 
        record['gecos'] = record['givenName'] + ' ' + record['sn']
        
        vcf_item = """BEGIN:VCARD
VERSION:3.0
ORG:%(company)s
FN:%(gecos)s
N:%(sn)s;%(givenName)s
""" % record

        vcf_item += "EMAIL;TYPE=INTERNET,WORK,PREF:%s\n" % record['mail'][0]

        for phones, pkind in {'businessPhone': 'WORK', 'personalPhone': 'HOME', }.iteritems():
            if phones in record:
                for phone in record[phones]:
                    phone = phone.strip()
                    if not re.match('^[+0-9]+$', phone):
                        phone = phone.decode('base64').strip()
                        if not re.match('^[+0-9]+$', phone):
                            # Skip broken phones
                            continue
                    
                    if phone.startswith('+336'):
                        vcf_item += "TEL;TYPE=CELL,%s:%s\n" % (pkind, phone)
                    else:
                        vcf_item += "TEL;TYPE=VOICE,%s:%s\n" % (pkind, phone)

        if 'userPicture' in record:
            if record['userPicture'][0].startswith('\xff\xd8\xff\xe0\x00\x10JFIF'):
                vcf_item += format_picture(record['userPicture'][0], 'JPEG')
            elif record['userPicture'][0].startswith('\x89PNG\r\n'):
                vcf_item += format_picture(record['userPicture'][0], 'PNG')
        
        # FIXME: handle someday ? What about X.509 certificates ?
        #if 'gpgKey' in record:
        #    vcf_item += "KEY;TYPE=PGP:%s\n" % record['gpgKey'][0].strip()
        
        # FIXME: generate a unique revision id ?
        # vcf_item += """REV:

        vcf_item += "END:VCARD\n"

        print vcf_item
        
if __name__ == '__main__':

    PARSER = optparse.OptionParser(version="%prog " + VERSION,
        usage = "%prog [options] FILE",
        option_list=[
            optparse.Option("-c", "--company", dest="company", help="Company contacts should belong to",  metavar="COMPANY", default=None),
        ])

    (POPTIONS, ARGS) = PARSER.parse_args()
    
    if len(ARGS) != 1:
        PARSER.print_help()
        sys.exit(os.EX_USAGE)

    ldif2vcf(ARGS[0], POPTIONS.company)
    sys.exit(os.EX_OK)

