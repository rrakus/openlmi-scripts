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
POSIX group information and management.

Usage:
    %(cmd)s show [ <group> ...]
    %(cmd)s listusers <group> ...
    %(cmd)s create [--reserved --gid=gid] <group>
    %(cmd)s delete <group>
    %(cmd)s add <group> <user> ...
    %(cmd)s remove <group> <user> ...

Commands:
    show        Show detailed information about group. If no groups
                are provided, all of them are displayed.

    listusers   List a users in a group or in a list of groups.

    create      Creates a new group.

    delete      Deletes a group.

    add         Adds a user or a list of users to the group.

    remove      Removes a user or a list of users from the group.

Options:
    -r, --reserved  Create a system group.
    -g, --gid=gid   GID for a new group.
"""

from lmi.scripts.common import command
from lmi.scripts.common.errors import LmiInvalidOptions
from lmi.scripts.common.errors import LmiFailed
from lmi.scripts.common import get_logger

LOG = get_logger(__name__)

def show_group(ns, groups=None):
    if (groups):
        for group in groups:
            inst = ns.LMI_Group.first_instance({"Name": group})
            if inst is None:
                raise LmiFailed('No such group "%s"' % group)
            yield inst
    else:
        for group in ns.LMI_Group.instances():
            yield group

def get_users_in_group(group):
    """
    Yields a user names in group
    Parameter group should be instance of group
    """
    for identity in group.associators(AssocClass = "LMI_MemberOfGroup", ResultClass = "LMI_Identity"):
        yield identity.first_associator(AssocClass = "LMI_AssignedAccountIdentity", ResultClass = "LMI_Account").Name

def list_users(ns, groups=None):
    if (groups):
        for group in groups:
            group_inst = ns.LMI_Group.first_instance({"Name": group})
            if group_inst is None:
                raise LmiFailed('No such group "%s"' % group)
            yield (group, ', '.join(get_users_in_group(group_inst)))
    else:
        for group in ns.LMI_Group.instances():
            yield (group.Name, ', '.join(get_users_in_group(group)))

def create_group(ns, group, _reserved, _gid):
    cs = ns.Linux_ComputerSystem.first_instance()
    lams = ns.LMI_AccountManagementService.first_instance()

    params = {
        "Name" : group,
        "System" : cs}
    if _reserved:
        params["SystemAccount"] = True
    if _gid is not None:
        params["GID"] = _gid

    lams.CreateGroup(**params)

def delete_group(ns, group):
    group_inst = ns.LMI_Group.first_instance({"Name": group})
    if group_inst is None:
        raise LmiFailed('No such group "%s"' % group)
    group_inst.delete()


def is_in_group(group, user):
    """
    Return True if user is in group
    """
    identity = group.first_associator(
        AssocClass="LMI_MemberOfGroup",
        ResultClass="LMI_Identity")
    if identity is None:
        return False
    return identity.InstanceID.split(":")[-1] == user.UserID

def add_to_group(ns, group, users):
    group_inst = ns.LMI_Group.first_instance({"Name": group})
    if group_inst is None:
        raise LmiFailed('No such group "%s"' % group)

    for user in users:
        user_inst = ns.LMI_Account.first_instance({"Name": user})
        if user is None:
            raise LmiFailed('No such user "%s"' % user)
        if is_in_group(group_inst, user_inst):
            LOG().info('User "%s" already is in group "%s", skipping',
                user, group)
        else:
            # get identity
            identity = user_inst.first_associator(ResultClass="LMI_Identity")
            # add the user; create instance of LMI_MemberOfGroup
            ns.LMI_MemberOfGroup.create_instance(
                {"Member":identity.path,"Collection":group_inst.path})

def remove_from_group(ns, group, users):
    group_inst = ns.LMI_Group.first_instance({"Name": group})
    if group_inst is None:
        raise LmiFailed('No such group "%s"' % group)

    for user in users:
        user_inst = ns.LMI_Account.first_instance({"Name": user})
        if user_inst is None:
            raise LmiFailed('No such user "%s"' % user)
        # get identity
        identity = user_inst.first_associator(ResultClass="LMI_Identity")
        # get MemberOfGroup
        for mog in identity.references(ResultClass="LMI_MemberOfGroup"):
            if mog.Collection.Name == group:
                mog.delete()

class Show(command.LmiInstanceLister):
    CALLABLE = show_group
    PROPERTIES = (
            'Name',
            ('GID', lambda i: i.InstanceID.split(":")[-1])
    )

    def transform_options(self, options):
        """
        Rename 'group' option to 'groups' parameter name for better
        readability
        """
        options['<groups>'] = options.pop('<group>')

class ListUsers(command.LmiLister):
    CALLABLE = list_users # TODO graph output instead of table output?
    COLUMNS = ('Group', 'Users')

    def transform_options(self, options):
        """
        Rename 'group' option to 'groups' parameter name for better
        readability
        """
        options['<groups>'] = options.pop('<group>')


class Create(command.LmiCheckResult):
    CALLABLE = create_group
    EXPECT = None

    def verify_options(self, opts):
        _gid = opts['--gid']
        if _gid is not None and not _gid.isdigit():
            raise LmiInvalidOptions("Group ID must be a number")

    def transform_options(self, options):
        """
        Change 'group' list to string
        """
        options['<group>'] = options.pop('<group>')[0]

class Delete(command.LmiCheckResult):
    CALLABLE = delete_group
    EXPECT = None

    def transform_options(self, options):
        """
        Change 'group' list to string
        """
        options['<group>'] = options.pop('<group>')[0]


class Add(command.LmiCheckResult):
    CALLABLE = add_to_group
    EXPECT = None

    def transform_options(self, options):
        """
        Change 'group' list to string
        Rename 'user' to 'users'
        """
        options['<group>'] = options.pop('<group>')[0]
        options['<users>'] = options.pop('<user>')

class Remove(command.LmiCheckResult):
    CALLABLE = remove_from_group
    EXPECT = None

    def transform_options(self, options):
        """
        Change 'group' list to string
        Rename 'user' to 'users'
        """
        options['<group>'] = options.pop('<group>')[0]
        options['<users>'] = options.pop('<user>')

Group = command.register_subcommands(
        'group', __doc__,
        { 'show'    : Show
        , 'listusers' : ListUsers
        , 'create'  : Create
        , 'delete'  : Delete
        , 'add'     : Add
        , 'remove'  : Remove
        },
    )
