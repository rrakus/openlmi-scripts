# Account Management Providers
#
# Copyright (C) 2013 Red Hat, Inc.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are those
# of the authors and should not be interpreted as representing official policies,
# either expressed or implied, of the FreeBSD Project.
#
#
# Authors: Roman Rakus <rrakus@redhat.com>
#
"""
POSIX user information and management.

Usage:
    %(cmd)s list
    %(cmd)s show [ <user> ...]
    %(cmd)s create <name> [options]
    %(cmd)s delete [--nodeletehome --nodeletegroup --force] <user> ...

Commands:
    list        Prints a list of users.

    show        Show detailed information about user. If no users are provided,
                all of them are displayed.

    create      Creates a new user. See Create options below for options
                description.

    delete      Delete specified user (or user list). See Delete options
                below for options description.

Create options:
    -c gecos, --gecos=gecos       Set the GECOS field to gecos.
    -d dir, --directory=dir       Set the user's home directory to dir.
                                  If this option is not set, a default value
                                  is used.
    -s shell, --shell=shell       Set user's login shell to shell. If this
                                  option is not set, a default value is used.
    -u uid, --uid=uid             Use user ID uid for the newly created user.
                                  If this option is not set, a default value
                                  is used.
    -g gid, --gid=gid             Set user's primary group ID to gid. If this
                                  option is not set, a default value is used.
    -r, --reserved                The user is a system user.
                                  Implies the -M option.
    -M, --nocreatehome            Don't create a home directory.
    -n, --nocreategroup           Don't create a primary group for user.
    -P, --plainpassword=password  Set user's password to password
    -p, --password=encrypted      Set user's password to the password
                                  represented by the hash encrypted.

Delete options:
    --nodeletehome   Do not remove home directory.
    --nodeletegroup  Do not remove user's primary group.
    --force          Remove home directory even if the user is not owner.
"""

# TODO -- option separator

from lmi.scripts.common import command
from lmi.scripts.common.errors import LmiFailed
from lmi.scripts.common.errors import LmiInvalidOptions

def list(ns):
    """
    Implementation of 'user list' command.
    """
    for s in sorted(ns.LMI_Account.instances(),
                    key=lambda i: i.Name):
        yield (s.Name, s.UserID, s.ElementName)

def get_user_info(ns, user):
    """
    Return detailed information of the user to show.
    """
    return (user.Name, user.UserID, user.HomeDirectory, user.LoginShell,
            user.PasswordLastChange)

def show_user(ns, users=None):
    if (users):
        for user in users:
            inst = ns.LMI_Account.first_instance({"Name": user})
            if inst is None:
                raise LmiFailed('No such user "%s"' % user)
            yield inst
    else:
        for user in ns.LMI_Account.instances():
            yield user

def delete_user(ns, _nodeletegroup, _nodeletehome, _force, users):
    instances = []
    params = {
        "DontDeleteHomeDirectory": _nodeletehome,
        "DontDeleteGroup": _nodeletegroup,
        "Force": _force
    }
    for user in users:
        inst = ns.LMI_Account.first_instance({"Name": user})
        if inst is None:
            raise LmiFailed('No such user "%s"' % user)
        instances.append(inst)
    for inst in instances:
        inst.DeleteUser(**params)

def create_user(ns, name, **kwargs):
    cs = ns.Linux_ComputerSystem.first_instance()
    lams = ns.LMI_AccountManagementService.first_instance()

    used_password = kwargs['_password']
    is_plain = False
    if kwargs['_password'] is None and kwargs['_plainpassword'] is not None:
        used_password = kwargs['_plainpassword']
        is_plain = True
    params = dict({
        "Name": name,
        "System": cs,
        "GECOS": kwargs['_gecos'],
        "HomeDirectory": kwargs['_directory'],
        "DontCreateHome": kwargs['_nocreatehome'],
        "Shell": kwargs['_shell'],
        "UID": kwargs['_uid'],
        "GID": kwargs['_gid'],
        "SystemAccount": kwargs['_reserved'],
        "Password": used_password,
        "DontCreateGroup": kwargs['_nocreategroup'],
        "PasswordIsPlain": is_plain
        })
    for key in params.keys():
        if params[key] is None:
            del params[key]

    lams.CreateAccount(**params)

class Lister(command.LmiLister):
    CALLABLE = 'lmi.scripts.account.user_cmd:list'
    COLUMNS = ('Name', "UID", "Full name")

class Show(command.LmiInstanceLister):
    CALLABLE = show_user
    PROPERTIES = (
            'Name',
            ('UID', 'UserID'),
            ('Home', 'HomeDirectory'),
            ('Login shell', 'LoginShell'),
            ('Password last change', lambda i: i.PasswordLastChange.datetime.strftime("%Y/%m/%d"))
    )

    def transform_options(self, options):
        """
        Rename 'user' option to 'users' parameter name for better
        readability
        """
        options['<users>'] = options.pop('<user>')

class Delete(command.LmiCheckResult):
    CALLABLE = delete_user
    EXPECT = None

    def transform_options(self, options):
        """
        Rename 'user' option to 'users' parameter name for better
        readability
        """
        options['<users>'] = options.pop('<user>')

class Create(command.LmiCheckResult):
    CALLABLE = create_user
    EXPECT = None

    def verify_options(self, opts):
        _password = opts['--password']
        _plainpassword = opts['--plainpassword']
        _uid = opts['--uid']
        _gid = opts['--gid']
        if _password is not None and _plainpassword is not None:
            raise LmiInvalidOptions("Must set only one of password options")
        if _uid is not None and not _uid.isdigit():
            raise LmiInvalidOptions("User ID must be a number")
        if _gid is not None and not _gid.isdigit():
            raise LmiInvalidOptions("Group ID must be a number")

User = command.register_subcommands(
        'user', __doc__,
        { 'list'    : Lister
        , 'show'    : Show
        , 'delete'  : Delete
        , 'create'  : Create
        },
    )
