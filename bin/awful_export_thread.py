#!/usr/bin/env python
import argparse
import logging
import sys

from awfulutils.awfulclient import AwfulClient


usage = """
Exports a Something Awful thread, including images and stylesheets, to local disk for archival purposes

Example:

awful_export_thread -u 38563 -s 99bd7c5025316dae9dcb6ea6d7366870 -t 2675400
"""

logger = logging.getLogger('awfulutils')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=usage)
    parser.add_argument('-u', '--userid',
                        help='Something Awful User Id number. Use the value from your bbuserid cookie.',
                        type=int, dest='userid')
    parser.add_argument('-s', '--session', help='Something Awful Session Id. Use the value of your bbpassword cookie.',
                        dest='session')
    parser.add_argument('-t', '--threadid', help='Something Awful Thread Id number you wish to export',
                        type=int, dest='threadid')
    parser.add_argument('-x', '--timeout', help='Set the timeout to use for HTTP requests. Default is 10 seconds.',
                        type=int, dest='timeout', default=AwfulClient.DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args()
    if args.userid and args.session and args.threadid:
        awful_client = AwfulClient(args.userid, args.session, timeout=args.timeout)
        awful_client.export_thread(args.threadid)
    else:
        parser.print_help()
        sys.exit(1)
