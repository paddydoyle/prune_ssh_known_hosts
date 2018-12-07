# prune_ssh_known_hosts
Simple checks of entries in .ssh/known_hosts

## Motivation

I know that ssh'ing to nodes is an anti-pattern for modern scalable
administration, but when you don't have all the nice tooling to avoid
it, you still end up logging into lots of hosts.

My .ssh/known_hosts file had something like 900 entries, including
lots of old dead hosts, and lots of duplicate entries for some odd
reason.

This silly python script let me remove about 250 entries.

