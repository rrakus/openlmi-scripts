# Software Management Providers
#
# Copyright (C) 2012-2013 Red Hat, Inc.  All rights reserved.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# Authors: Michal Minar <miminar@redhat.com>
#
"""
System software management.

Usage:
    lmi sw list pkgs [(--available [--repo <repo>] | --all)] [--allow-duplicates]
    lmi sw list repos [--disabled | --all]
    lmi sw list files <pkg>
    lmi sw show pkg [--repo <repo>] <pkg> ...
    lmi sw show repo <repo> ...
    lmi sw install [--force] <pkg> ...
    lmi sw install --uri <uri>
    lmi sw remove <pkg> ...
    lmi sw verify <pkg> ...
    lmi sw update <pkg> ...
    lmi sw enable <repo> ...
    lmi sw disable <repo> ...

Commands:
    list        List various information about packages, repositories or
                files.
    start       Show detailed informations about package or repository.
    install     Install packages specified in one of following notations:
                    <name>
                    <name>.<arch>
                    <name>-<epoch>:<version>-<release>.<arch>
                Installation from URI is also supported, it must be prefixed
                with --uri option.
    remove      Remove installed package.
    verify      Verify package.
    update      Update package.
    enable      Enable one or more repositories.

Options:
    --force        Force installation 
    --repo <repo>  Select a repository, where the given package will be
                   searched.
    --uri <uri>    Operate upon an rpm package available on remote system
                   through http or ftp service.
"""

from lmi.scripts.common import command

CALLABLE = 'lmi.scripts.software:list'
COLUMNS = ('Name', "Started", 'Status')

class PkgLister(command.LmiLister):
    CALLABLE = 'lmi.scripts.software:list_pkgs'

class RepoLister(command.LmiLister):
    CALLABLE = 'lmi.scripts.software:list_repos'

class Lister(command.LmiCommandMultiplexer):
    COMMANDS = { 'pkgs' : PkgLister, 'files' : RepoLister }

Software = command.register_subcommands(
        'Software', __doc__,
        { 'list'    : Lister },
    )