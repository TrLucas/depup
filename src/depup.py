#!/usr/bin/env python

# This file is part of Adblock Plus <https://adblockplus.org/>,
# Copyright (C) 2006-present eyeo GmbH
#
# Adblock Plus is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# Adblock Plus is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Adblock Plus.  If not, see <http://www.gnu.org/licenses/>.

"""Prepare a dependency update.

This script executes the automatable work which needs to be done for a
dependency update and provides additional information, i.e. a complete
diff of imported changes, as well as related integration notes.
"""

from __future__ import print_function, unicode_literals

import argparse
import io
import json
import logging
import os
import re
import subprocess
try:
    from urllib import urlopen
except ImportError:
    from urllib.request import urlopen

import jinja2

from src.vcs import Vcs

logging.basicConfig()
logger = logging.getLogger('depup')


class DepUpdate(object):
    """The main class used to process dependency updates.

    TODO: CLARIFY ME!

    """

    VCS_EXECUTABLE = ('hg', '--config', 'defaults.log=', '--config',
                      'defaults.pull=')
    ISSUE_NUMBER_REGEX = re.compile(r'\b(issue|fixes)\s+(\d+)\b', re.I)
    NOISSUE_REGEX = re.compile(r'^noissue\b', re.I)

    def __init__(self, *args):
        """Construct a DepUpdate object.

        During initialization, DepUpdate will invoke the appropriate VCS to
        fetch a list of changes, parse them and (if not otherwise specified)
        get the matching revisions from the mirrored repository.

        Parameters: *args - Passed down to the argparse.ArgumentParser instance

        """
        self._cwd = os.getcwd()

        self.root_repo = Vcs.factory(self._cwd)

        self._base_revision = None
        self._parsed_changes = None
        self.arguments = None

        self._dep_config = None

        default_template = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'templates',
            'default.trac')

        # Initialize and run the internal argument parser
        self._make_arguments(default_template, *args)

        # Check if root repository is dirty
        if not self.root_repo.repo_is_clean():
            logger.error('Your repository is dirty')
            exit(1)

        # Initialize the main VCS and the list of changes
        self._main_vcs = Vcs.factory(os.path.join(self._cwd,
                                     self.arguments.dependency))
        self.changes = self._main_vcs.change_list(self.base_revision,
                                                  self.arguments.new_revision)
        if len(self.changes) == 0:
            self.changes = self._main_vcs.change_list(
                    self.arguments.new_revision,
                    self.base_revision
            )
            if len(self.changes) > 0:
                # reverse mode. Uh-oh.
                logger.warn('You are trying to downgrade the dependency!')

        self._main_vcs.enhance_changes_information(
            self.changes,
            os.path.join(self._mirror_location(),
                         self.arguments.dependency),
            self.arguments.skip_mirror,
        )

    def _make_arguments(self, default_template, *args):
        """Initialize the argument parser and store the arguments."""
        parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter)

        # First prepare all basic shared options
        options_parser = argparse.ArgumentParser(add_help=False)
        shared = options_parser.add_argument_group()
        shared.add_argument(
                'dependency',
                help=('The dependency to be updated, as specified in the '
                      'dependencies file.')
        )
        shared.add_argument(
                '-r', '--revision', dest='new_revision',
                help=('The revision to update to. Defaults to the remote '
                      'master bookmark/branch. Must be accessible by the '
                      "dependency's vcs.")
        )
        shared.add_argument(
                '-m', '--mirrored-repository', dest='local_mirror',
                help=('Path to the local copy of a mirrored repository. '
                      'Used to fetch the corresponding hash. If not '
                      'given, the source parsed from the dependencies file is '
                      'used.')
        )

        # Shared options for non-commit commands
        advanced_parser = argparse.ArgumentParser(add_help=False)
        advanced = advanced_parser.add_argument_group()
        advanced.add_argument(
                '-f', '--filename', dest='filename', default=None,
                help=("When specified, write the subcommand's output to the "
                      'given file, rather than to STDOUT.')
        )
        advanced.add_argument(
                '-s', '--skip-mirror', action='store_true', dest='skip_mirror',
                help='Do not use any mirror.'
        )
        advanced.add_argument(
                '-l', '--lookup-integration-notes', action='store_true',
                dest='lookup_inotes', default=False,
                help=('Search https://issues.adblockplus.org for integration '
                      'notes associated with the included issue IDs. The '
                      'results are written to STDERR. CAUTION: This is a very '
                      'network heavy operation.')
        )

        subs = parser.add_subparsers(
                title='Subcommands', dest='action', metavar='[subcommand]',
                help=('Required, the actual command to be executed. Execute '
                      'run "<subcommand> -h" for more information.')
        )

        # Add the command and options for creating a diff
        diff_parser = subs.add_parser(
                'diff', parents=[options_parser, advanced_parser],
                help='Create a unified diff of all changes',
                description=("Invoke the current repository's VCS to generate "
                             'a diff, containing all changes made between two '
                             'revisions.'))
        diff_parser.add_argument(
                '-n', '--n-context-lines', dest='unified_lines', type=int,
                default=16,
                help=('Number of unified context lines to be added to the '
                      'diff. Defaults to 16 (Used only with -d/--diff).')
        )

        # Add the command and options for creating an issue body
        issue_parser = subs.add_parser(
                'issue', parents=[options_parser, advanced_parser],
                help='Render an issue body',
                description=('Render an issue subject and an issue body, '
                             'according to the given template.'))
        issue_parser.add_argument(
                '-t', '--template', dest='tmpl_path',
                default=default_template,
                help=('The template to use. Defaults to the provided '
                      'default.trac (Used only with -i/--issue).')
        )

        # Add the command for printing a list of changes
        subs.add_parser(
                'changes', parents=[options_parser, advanced_parser],
                help='Generate a list of commits between two revisions',
                description=('Generate a list of commit hashes and commit '
                             "messages between the dependency's current "
                             'revision and a given new revision.'))

        # Add the command for changing and committing a dependency update
        commit_parser = subs.add_parser(
                'commit', help='Update and commit a dependency change',
                parents=[options_parser],
                description=('Rewrite and commit a dependency file to the new '
                             'revision. WARNING: This actually changes your '
                             "repository's history, use with care!"))
        commit_parser.add_argument(
                'issue_number', help=('The issue number, filed on '
                                      'https://issues.adblockplus.org'))
        commit_parser.set_defaults(skip_mirror=False, lookup_inotes=False,
                                   filename=None)

        self.arguments = parser.parse_args(args if len(args) > 0 else None)

    @property
    def dep_config(self):
        """Provide the dependencies by using ensure_dependencies.read_dep().

        Since this program is meant to be run inside a repository which uses
        the buildtools' dependency functionalities, we are sure that
        ensure_dependencies.py and dependencies exist.

        However, ensure_dependencies is currently only compatible with python2.
        Due to this we explicitly invoke a python2 interpreter to run our
        dependencies.py, which runs ensure_dependencies.read_deps() and returns
        the output as JSON data.
        """
        if self._dep_config is None:
            dependencies_script = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'dependencies.py')

            dep_json = subprocess.check_output(
                ['python2', dependencies_script]
            ).decode('utf-8')
            self._dep_config = json.loads(dep_json)
        return self._dep_config

    @property
    def base_revision(self):
        """Provide the current revision of the dependency to be processed."""
        if self._base_revision is None:
            for key in ['*', self._main_vcs.EXECUTABLE]:
                rev = self.dep_config[self.arguments.dependency][key][1]
                if rev is not None:
                    self._base_revision = rev
                    break
        return self._base_revision

    def _parse_changes(self, changes):
        """Parse the changelist to issues / noissues."""
        issue_ids = set()
        noissues = []
        for change in changes:
            match = self.ISSUE_NUMBER_REGEX.search(change['message'])
            if match:
                issue_ids.add(match.group(2))
            else:
                noissues.append(change)
                if not self.NOISSUE_REGEX.search(change['message']):
                    msg = (
                        'warning: no issue reference in commit message: '
                        '"{message}" (commit {hg_hash} | {git_hash})\n'
                    ).format(**change)
                    logger.warn(msg)

        return issue_ids, noissues

    @property
    def parsed_changes(self):
        """Provide the list of changes, separated by issues and noissues.

        Returns a dictionary, containing the following two key/value pairs:
        'issue_ids': a list of issue IDs (as seen on
                     https://issues.adblockplus.org/)
        'noissues': The remaining changes, with all original information (see
                    DepUpdate.changes) which could not be associated with any
                    issue.
        """
        if self._parsed_changes is None:
            self._parsed_changes = {}
            issue_ids, noissues = self._parse_changes(self.changes)
            self._parsed_changes['issue_ids'] = issue_ids
            self._parsed_changes['noissues'] = noissues
        return self._parsed_changes

    def _possible_sources(self):
        root_conf = self._dep_config['_root']
        config = self.dep_config[self.arguments.dependency]

        # The fallback / main source paths for a repository are given in the
        # dependencies file's _root section.
        keys = ['hg', 'git']
        possible_sources = {}
        possible_sources.update({
            key + '_root': root_conf[key]
            for key in keys
        })

        # Any dependency may specify a custom source location.
        possible_sources.update({
            key: source for key, source in [
                (key, config.get(key, (None, None))[0]) for key in keys
            ] if source is not None
        })

        return possible_sources

    def _mirror_location(self):
        possible_sources = self._possible_sources()
        mirror_ex = self._main_vcs._other_cls.EXECUTABLE

        # If the user specified a local mirror, use it. Otherwise use the
        # mirror, which was specified in the dependencies file.
        if self.arguments.local_mirror:
            mirror = self.arguments.local_mirror
        else:
            for key in [mirror_ex, mirror_ex + '_root']:
                if key in possible_sources:
                    mirror = possible_sources[key]
                    break
        return mirror

    def _make_dependencies_string(self, hg_source=None, hg_rev=None,
                                  git_source=None, git_rev=None,
                                  remote_name=None):
        dependency = '{} = {}'.format(self.arguments.dependency,
                                      remote_name or self.arguments.dependency)

        for prefix, rev, source in [(' hg:', hg_rev, hg_source),
                                    (' git:', git_rev, git_source)]:
            if rev is not None:
                dependency += prefix
                if source is not None:
                    dependency += source + '@'
                dependency += rev

        return dependency

    def _update_dependencies_file(self):
        config = self.dep_config[self.arguments.dependency]

        remote_repository_name, none_hash_rev = config.get('*', (None, None))
        hg_source, hg_rev = config.get('hg', (None, None))
        git_source, git_rev = config.get('git', (None, None))

        current_entry = self._make_dependencies_string(
            hg_source, hg_rev, git_source, git_rev, remote_repository_name
        )

        new_entry = self._make_dependencies_string(
            hg_source, self.changes[0]['hg_hash'], git_source,
            self.changes[0]['git_hash'], remote_repository_name
        )

        dependency_path = os.path.join(self._cwd, 'dependencies')
        with io.open(dependency_path, 'r', encoding='utf-8') as fp:
            current_deps = fp.read()
        with io.open(dependency_path, 'w', encoding='utf-8') as fp:
            fp.write(current_deps.replace(current_entry, new_entry))

    def _update_copied_code(self):
        subprocess.check_output(
            ['python2', 'ensure_dependencies.py'],
            cwd=self._cwd
        )

    def build_diff(self):
        """Generate a unified diff of all changes."""
        return self._main_vcs.merged_diff(self.base_revision,
                                          self.arguments.new_revision,
                                          self.arguments.unified_lines)

    def build_issue(self):
        """Process all changes and render an issue."""
        context = {}
        context['repository'] = self.arguments.dependency
        context['issue_ids'] = self.parsed_changes['issue_ids']
        context['noissues'] = self.parsed_changes['noissues']
        context['hg_hash'] = self.changes[0]['hg_hash']
        context['git_hash'] = self.changes[0]['git_hash']
        context['raw_changes'] = self.changes

        path, filename = os.path.split(self.arguments.tmpl_path)

        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(path or './')
        ).get_template(filename).render(context)

    def lookup_integration_notes(self):
        """Search for any "Integration notes" mentions at the issue-tracker.

        Cycle through the list of issue IDs and search for "Integration Notes"
        in the associated issue on https://issues.adblockplus.org. If found,
        write the corresponding url to STDERR.
        """
        # Let logger show INFO-level messages
        logger.setLevel(logging.INFO)
        integration_notes_regex = re.compile(r'Integration\s*notes', re.I)

        def from_url(issue_url):
            html = ''
            content = urlopen(issue_url)

            for line in content:
                html += line.decode('utf-8')
            return html

        for issue_id in self.parsed_changes['issue_ids']:
            issue_url = 'https://issues.adblockplus.org/ticket/' + issue_id
            html = from_url(issue_url)
            if not integration_notes_regex.search(html):
                continue

            logger.info('Integration notes found: ' + issue_url)

    def build_changes(self):
        """Write a descriptive list of the changes to STDOUT."""
        return os.linesep.join(
            [(
                '( hg:{hg_hash} | git:{git_hash} ) : {message} (by {author})'
             ).format(**change) for change in self.changes]
        )

    def commit_update(self):
        """Commit the new dependency and potentially updated files."""
        commit_msg = 'Issue {} - Update {} to {}'.format(
                self.arguments.issue_number, self.arguments.dependency,
                ' / '.join((self.changes[0]['hg_hash'],
                            self.changes[0]['git_hash'])))
        try:
            self._update_dependencies_file()
            self._update_copied_code()
            self.root_repo.commit_changes(commit_msg)

            return commit_msg
        except subprocess.CalledProcessError:
            self._main_vcs.undo_changes()
            logger.error('Could not safely commit the changes. Reverting.')

    def __call__(self):
        """Let this class's objects be callable, run all desired tasks."""
        action_map = {
            'diff': self.build_diff,
            'changes': self.build_changes,
            'issue': self.build_issue,
            'commit': self.commit_update,
        }

        if len(self.changes) == 0:
            print('NO CHANGES FOUND. You are either trying to update to a '
                  'revision, which the dependency already is at - or '
                  'something went wrong while executing the vcs.')
            return

        if self.arguments.lookup_inotes:
            self.lookup_integration_notes()

        output = action_map[self.arguments.action]()
        if self.arguments.filename is not None:
            with io.open(self.arguments.filename, 'w', encoding='utf-8') as fp:
                fp.write(output)
            print('Output writen to ' + self.arguments.filename)
        else:
            print(output)
