#!/usr/bin/env python

''' This runs a sequence of commands on a remote host using SSH. It runs a
simple system checks such as uptime and free to monitor the state of the remote
host.

./monitor.py [-s server_hostname] [-u username] [-p password]
    -s : hostname of the remote server to login to.
    -u : username to user for login.
    -p : Password to user for login.

Example:
    This will print information about the given host:
        ./monitor.py -s www.example.com -u mylogin -p mypassword

It works like this:
    Login via SSH (This is the hardest part).
    Run and parse 'uptime'.
    Run 'iostat'.
    Run 'vmstat'.
    Run 'netstat'
    Run 'free'.
    Exit the remote host.

PEXPECT LICENSE

    This license is approved by the OSI and FSF as GPL-compatible.
        http://opensource.org/licenses/isc-license.txt

    Copyright (c) 2012, Noah Spurrier <noah@noah.org>
    PERMISSION TO USE, COPY, MODIFY, AND/OR DISTRIBUTE THIS SOFTWARE FOR ANY
    PURPOSE WITH OR WITHOUT FEE IS HEREBY GRANTED, PROVIDED THAT THE ABOVE
    COPYRIGHT NOTICE AND THIS PERMISSION NOTICE APPEAR IN ALL COPIES.
    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
    ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
    OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

'''

from __future__ import print_function

from __future__ import absolute_import

import os, sys, re, getopt, getpass
import pexpect


try:
    raw_input
except NameError:
    raw_input = input


#
# Some constants.
#
COMMAND_PROMPT = '[#$] ' ### This is way too simple for industrial use -- we will change is ASAP.
TERMINAL_PROMPT = r'(?i)terminal type\?'
TERMINAL_TYPE = 'vt100'
# This is the prompt we get if SSH does not have the remote host's public key stored in the cache.
SSH_NEWKEY = '(?i)are you sure you want to continue connecting'

def exit_with_usage():

    print(globals()['__doc__'])
    os._exit(1)

def check_server():
    global COMMAND_PROMPT, TERMINAL_PROMPT, TERMINAL_TYPE, SSH_NEWKEY
    ######################################################################
    ## Parse the options, arguments, get ready, etc.
    ######################################################################
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'h?s:u:p:', ['help','h','?'])
    except Exception as e:
        print(str(e))
        exit_with_usage()
    options = dict(optlist)
    if len(args) > 1:
        exit_with_usage()

    if [elem for elem in options if elem in ['-h','--h','-?','--?','--help']]:
        print("Help:")
        exit_with_usage()

    if '-s' in options:
        host = options['-s']
    else:
        host = raw_input('hostname: ')
    if '-u' in options:
        user = options['-u']
    else:
        user = raw_input('username: ')
    if '-p' in options:
        password = options['-p']
    else:
        password = getpass.getpass('password: ')

    #
    # Login via SSH
    #
    child = pexpect.spawn('ssh -l %s %s'%(user, host))
    i = child.expect([pexpect.TIMEOUT, SSH_NEWKEY, COMMAND_PROMPT, '(?i)password'])
    if i == 0: # Timeout
        print('ERROR! could not login with SSH. Here is what SSH said:')
        print(child.before, child.after)
        print(str(child))
        sys.exit (1)
    if i == 1: # In this case SSH does not have the public key cached.
        child.sendline ('yes')
        child.expect ('(?i)password')
    if i == 2:
        # This may happen if a public key was setup to automatically login.
        # But beware, the COMMAND_PROMPT at this point is very trivial and
        # could be fooled by some output in the MOTD or login message.
        pass
    if i == 3:
        child.sendline(password)
        # Now we are either at the command prompt or
        # the login process is asking for our terminal type.
        i = child.expect ([COMMAND_PROMPT, TERMINAL_PROMPT])
        if i == 1:
            child.sendline (TERMINAL_TYPE)
            child.expect (COMMAND_PROMPT)
    #
    # Set command prompt to something more unique.
    #
    COMMAND_PROMPT = r"\[PEXPECT\]\$ "
    child.sendline (r"PS1='[PEXPECT]\$ '") # In case of sh-style
    i = child.expect ([pexpect.TIMEOUT, COMMAND_PROMPT], timeout=10)
    if i == 0:
        print("# Couldn't set sh-style prompt -- trying csh-style.")
        child.sendline (r"set prompt='[PEXPECT]\$ '")
        i = child.expect ([pexpect.TIMEOUT, COMMAND_PROMPT], timeout=10)
        if i == 0:
            print("Failed to set command prompt using sh or csh style.")
            print("Response was:")
            print(child.before)
            sys.exit (1)

    # Now we should be at the command prompt and ready to run some commands.
    print('---------------------------------------')
    print('Server {} Status:'.format(host))
    print('---------------------------------------')

    # Run uname.
    child.sendline ('nvidia-smi')
    child.expect (COMMAND_PROMPT)
    print(child.before)

    # Now exit the remote host.
    child.sendline ('exit')
    index = child.expect([pexpect.EOF, "(?i)there are stopped jobs"])
    if index==1:
        child.sendline("exit")
        child.expect(EOF)

if __name__ == "__main__":
    check_server()
