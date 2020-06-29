#!/usr/bin/env python

import argparse
import os
import re
import socket


##############################################################################
# prune_ssh_known_hosts
# 2018-12-06 paddy@tchpc.tcd.ie
#
# Parse ~/.ssh/known_hosts and attempt to identify old entries which
# can be pruned.
#
# Criteria:
# - hostname no longer resolves -> definite candidate
# - hostname/IP address not pingable -> possible candidate (could be just
#   down)
# - host key does not match -> possible candidate (host since reinstalled,
#   but be careful!) [TODO]
#
# For matched entries, print a 'sed' command to comment out that line. It's
# not a 'sed -i' line; that can be manually added!
##############################################################################


def main():

    all_entries = {} # for duplicates
    non_resolving_hosts = {} # for hosts/IPs which don't resolve

    if args.hostsfile:
        filename = args.hostsfile
    else:
        if 'HOME' in os.environ:
            filename = os.environ['HOME'] + '/.ssh/known_hosts'
        else:
            filename = '.ssh/known_hosts'

    try:
        hostsfile = open(filename, 'r')
    except IOError, reason:
        print "Could not open hostsfile: %s" % (str(reason))
        return None

    if args.verbose:
        print "# Reading hostsfile %s" % (filename)

    # To be able to count line numbers
    lineno = 0

    for fline in hostsfile:
        fline = fline.strip()

        # Always increment, need to count comment lines as well
        lineno += 1

        # Ignore blank and comment lines
        if re.match(r'^$', fline):
            continue
        elif re.match(r'^\s*#', fline):
            continue

        # Record line numbers, and append duplicate lines
        if fline in all_entries:
            all_entries[fline].append(lineno)
        else:
            all_entries[fline] = [lineno]

        # Split based on whitespace
        # typical line:
        # 10.2.3.4 ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAIEA4VyLBb......
        (host, _, _) = fline.split()

        # What kind of host entry? we can have:
        # - short or long hostname
        # - ip address
        # - short or long hostname,ip address

        if ',' in host:
            # short or long hostname,ip address
            (hostname, ipaddr) = host.split(',')
            res = resolve_hostname(hostname)
        elif ':' in host:
            # ipv6 address
            (hostname, ipaddr) = ('', host)
            res = resolve_ipaddr(ipaddr)
        elif re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", host):
            # ip address
            (hostname, ipaddr) = ('', host)
            res = resolve_ipaddr(ipaddr)
        else:
            # short or long hostname
            (hostname, ipaddr) = (host, '')
            res = resolve_hostname(hostname)

        if not res:
            non_resolving_hosts[host] = lineno

    hostsfile.close()

    # Print the requested reports

    if args.duplicates:
        print_duplicates(all_entries, filename)

    if args.non_resolving:
        print_non_resolving(non_resolving_hosts, filename)


def resolve_hostname(hostname):
    try:
        resolved_ip = socket.gethostbyname(hostname)
        return True
    except socket.error:
        return False


def resolve_ipaddr(ipaddr):
    try:
        resolved_host = socket.gethostbyaddr(ipaddr)
        return True
    except socket.error:
        return False


# report loop: duplicate lines
def print_duplicates(all_entries, filename):
    sed_str = ''

    if args.verbose:
        print "\n# Duplicate entries:"

    for fline in all_entries:
        linenos = all_entries[fline]

        if len(linenos) > 1:
            if args.verbose:
                print "#   %s: %s" % (fline, linenos)
            # skip the first entry, duplicates follow it
            for lineno in linenos[1:]:

                if args.split_sed:
                    print r"sed '%ds/^\(.*\)/##  \1/' %s" "\n" % (lineno, filename)
                else:
                    sed_str += r" -e '%ds/^\(.*\)/##  \1/'" % (lineno)

    if sed_str and not args.split_sed:
        print "\nsed %s %s" % (sed_str, filename)


# report loop: non-resolving hosts/IPs
def print_non_resolving(non_resolving_hosts, filename):
    sed_str = ''

    if args.verbose:
        print "\n# Non-resolving entries:"

    for host in non_resolving_hosts:
        if args.verbose:
            print "#   %s" % (host)

        lineno = non_resolving_hosts[host]

        if args.split_sed:
            print r"sed '%ds/^\(.*\)/##  \1/' %s" "\n" % (lineno, filename)
        else:
            sed_str += r" -e '%ds/^\(.*\)/##  \1/'" % (lineno)

    if sed_str and not args.split_sed:
        print "\nsed %s %s" % (sed_str, filename)


if __name__ == '__main__':

    # don't you just love argparse!!
    parser = argparse.ArgumentParser()
    # positional arguments
    # options
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    parser.add_argument("-f", "--hostsfile",
                        help="filename to parse (defaults to $HOME/.ssh/known_hosts)",
                        type=str)
    parser.add_argument("-d", "--duplicates", help="print 'sed' lines to remove duplicates",
                        action="store_true")
    parser.add_argument("-r", "--non_resolving",
                        help="print 'sed' lines to remove non-resolving hosts",
                        action="store_true")
    parser.add_argument("-s", "--split_sed", help="split the 'sed' edits into individual lines",
                        action="store_true")
    args = parser.parse_args()

    main()


# vim: tabstop=4 expandtab nosmartindent shiftwidth=4 smarttab
