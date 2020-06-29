#!/usr/bin/env python

"""
prune_ssh_known_hosts

Parse ~/.ssh/known_hosts and attempt to identify old entries which
can be pruned.

Criteria:
- duplicate entry -> definite candidate
- hostname no longer resolves -> definite candidate
- hostname/IP address not pingable -> possible candidate (could be just
  down) [TODO]
- host key does not match -> possible candidate (host since reinstalled,
  but be careful!) [TODO]

For matched entries, print a 'sed' command to comment out that line. It's
not a 'sed -i' line; that can be manually added!
"""

from __future__ import print_function
import argparse
import os
import re
import socket


def main():
    """Open the file and find entries according to the given criteria."""

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
        print("Could not open hostsfile: {}".format(reason))
        return None

    if args.verbose:
        print("# Reading hostsfile {}".format(filename))

    # To be able to count line numbers
    lineno = 0

    for fline in hostsfile:
        fline = fline.strip()

        # Always increment, need to count comment lines as well
        lineno += 1

        # Ignore blank and comment lines, and any lines starting with markers
        if re.match(r'^$', fline):
            continue
        elif re.match(r'^\s*#', fline):
            continue
        elif not re.match(r'^\s*\w', fline):
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
    """DNS lookup: hostname to IP address."""
    try:
        _ = socket.gethostbyname(hostname)
        return True
    except socket.error:
        return False


def resolve_ipaddr(ipaddr):
    """DNS lookup: IP address to hostname."""
    try:
        _ = socket.gethostbyaddr(ipaddr)
        return True
    except socket.error:
        return False


def print_duplicates(all_entries, filename):
    """Report duplicate entries and print 'sed' lines to remove them."""
    sed_str = ''

    if args.verbose:
        print("\n# Duplicate entries:")

    for fline in all_entries:
        linenos = all_entries[fline]

        if len(linenos) > 1:
            if args.verbose:
                print("#   {}: {}".format(fline, linenos))
            # skip the first entry, duplicates follow it
            for lineno in linenos[1:]:

                if args.split_sed:
                    print(r"sed '{}s/^\(.*\)/##  \1/' {}" "\n".format(lineno, filename))
                else:
                    sed_str += r" -e '{}s/^\(.*\)/##  \1/'".format(lineno)

    if sed_str and not args.split_sed:
        print("\nsed {} {}".format(sed_str, filename))


def print_non_resolving(non_resolving_hosts, filename):
    """Report non-resolving hostnames/IP addresses and print 'sed' lines to remove them."""
    sed_str = ''

    if args.verbose:
        print("\n# Non-resolving entries:")

    for host in non_resolving_hosts:
        if args.verbose:
            print("#   {}".format(host))

        lineno = non_resolving_hosts[host]

        if args.split_sed:
            print(r"sed '{}s/^\(.*\)/##  \1/' {}" "\n".format(lineno, filename))
        else:
            sed_str += r" -e '{}s/^\(.*\)/##  \1/'".format(lineno)

    if sed_str and not args.split_sed:
        print("\nsed {} {}".format(sed_str, filename))


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
