#!/usr/bin/env python

#-----------------------------------------------------------------------
# testregapi.py
# Author: Bob Dondero
#-----------------------------------------------------------------------

import sys
import json
import argparse
import pprint
import urllib.request

#-----------------------------------------------------------------------

MAX_LINE_LENGTH = 72
UNDERLINE = '-' * MAX_LINE_LENGTH

#-----------------------------------------------------------------------

def parse_args():

    parser = argparse.ArgumentParser(
        description='Test the ability of the reg application to '
            + 'handle requests for JSON documents')

    parser.add_argument(
        'serverURL', metavar='serverURL', type=str,
        help='the URL of the reg application')

    args = parser.parse_args()

    return args.serverURL

#-----------------------------------------------------------------------

def print_flush(message):

    print(message)
    sys.stdout.flush()

#-----------------------------------------------------------------------

def pp_flush(data):

    pp = pprint.PrettyPrinter(width=MAX_LINE_LENGTH, sort_dicts=True)
    pp.pprint(data)
    sys.stdout.flush()

#-----------------------------------------------------------------------

def run_test(serverurl, request):

    print_flush(UNDERLINE)
    print_flush(request)
    print_flush(UNDERLINE)

    try:
        with urllib.request.urlopen(serverurl + request) as flo:
            response = flo.read()
            json_doc = response.decode('utf-8')
            response = json.loads(json_doc)
        pp_flush(response)

    except Exception as ex:
        print(sys.argv[0] + ': ' + str(ex), file=sys.stderr)

#-----------------------------------------------------------------------

def main():

    serverurl = parse_args()

    run_test(serverurl, '/regoverviews?dept=cos')
    run_test(serverurl,
        '/regoverviews?dept=COS&coursenum=2&area=qr&title=intro')

    # Add more tests here.

    run_test(serverurl, '/regdetails?classid=8321')

    # Add more tests here.

if __name__ == '__main__':
    main()
