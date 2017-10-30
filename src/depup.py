#!/usr/bin/env python

"""Prepare a dependency update.

This script executes the automatable work which needs to be done for a
dependency update and provides additional information, i.e. a complete
diff of imported changes, as well as related integration notes.
"""

from __future__ import print_function, unicode_literals

import argparse
import io
import json
import os
import re
import subprocess
import sys
try:
    from urllib import urlopen
except ImportError:
    from urllib.request import urlopen

import jinja2

from src.vcs import Vcs


class DepUpdate(object):
    """The main class used to process dependency updates.

    TODO: CLARIFY ME!

    """

    class MirrorException(Exception):
        """Represents errors while processing a git mirror."""

    VCS_EXECUTABLE = ('hg', '--config', 'defaults.log=', '--config',
                      'defaults.pull=')
    DEFAULT_NEW_REVISION = 'master'

    ISSUE_NUMBER_REGEX = re.compile(r'\b(issue|fixes)\s+(\d+)\b', re.I)
    NOISSUE_REGEX = re.compile(r'^noissue\b', re.I)

    def __init__(self, *args):
        """Construct a DepUpdate object.

        Parameters: *args - Passed down to the argparse.ArgumentParser instance

        """
        self._cwd = os.getcwd()

        self._base_revision = None
        self._parsed_changes = None
        self._arguments = None

        self._dep_config = None

        self._tag_mode = False

        default_template = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'templates',
            'default.trac')

        self._make_arguments(default_template, *args)

        self._main_vcs = Vcs.factory(os.path.join(self._cwd,
                                     self._arguments.dependency))

        self.changes = self._main_vcs.change_list(self.base_revision,
                                                  self._arguments.new_revision)
        if len(self.changes) == 0:
            self.changes = self._main_vcs.change_list(
                    self._arguments.new_revision,
                    self.base_revision
            )
            if len(self.changes) == 0:
                print(
                    ('NO CHANGES FOUND. You are either trying to update to a '
                     'revision, which the dependency already is at - or '
                     'something went wrong while executing the vcs. Exiting.'),
                    file=sys.stderr)
                exit(1)
            else:
                # reverse mode. Uh-oh.
                print('WARNING: you are trying to downgrade the dependency!',
                      file=sys.stderr)

    def _make_arguments(self, default_template, *args):
        """Initialize the argument parser and store the arguments."""
        parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.add_argument(
                'dependency',
                help=('The dependency to be updated, as specified in the '
                      'dependencies file.'),
        )
        parser.add_argument(
                '-r', '--revision', dest='new_revision',
                default=self.DEFAULT_NEW_REVISION,
                help=('The revision to update to. Defaults to the remote '
                      'master bookmark/branch. Must be accessible by the '
                      "dependency's vcs."),
        )
        changes_group = parser.add_argument_group(
                title='Output changes',
                description=('Process the list of included changes to either '
                             'a bare issue body, or print it to STDOUT.'))
        excl_group = changes_group.add_mutually_exclusive_group(required=True)
        excl_group.add_argument(
                '-c', '--changes', action='store_true', default=False,
                help=('Write the commit messages of all changes between the '
                      'given revisions to STDOUT.'),
        )
        excl_group.add_argument(
                '-i', '--issue', action='store_true', dest='make_issue',
                help=('Generate a bare issue body to STDOUT with included '
                      'changes that can be filed on '
                      'https://issues.adblockplus.org/. Uses either the '
                      'provided default template, or that provided  by '
                      '--template'),
        )
        excl_group.add_argument(
                '-d', '--diff', dest='diff', action='store_true',
                help=('Print a merged unified diff of all included changes to '
                      'STDOUT. By default, 16 lines of context are integrated '
                      '(see -n/--n-context-lines).'),
        )
        changes_group.add_argument(
                '-n', '--n-context-lines', dest='unified_lines', type=int,
                default=16,
                help=('Number of unified context lines to be added to the '
                      'diff. Defaults to 16 (Used only with -d/--diff).'),
        )
        changes_group.add_argument(
                '-t', '--template', dest='tmpl_path',
                default=default_template,
                help=('The template to use. Defaults to the provided '
                      'default.trac (Used only with -i/--issue).'),
        )
        parser.add_argument(
                '-l', '--lookup-integration-notes', action='store_true',
                dest='lookup_inotes', default=False,
                help=('Search https://issues.adblockplus.org for integration '
                      'notes associated with the included issue IDs. The '
                      'results are written to STDERR. CAUTION: This is a very '
                      'network heavy operation.'),
        )
        parser.add_argument(
                '-m', '--mirrored-repository', dest='local_mirror',
                help=('Path to the local copy of a mirrored repository. '
                      'Used to fetch the corresponding hash. If not '
                      'given, the source parsed from the dependencies file is '
                      'used.'),
        )
        parser.add_argument(
                '-u', '--update', action='store_true',
                dest='update_dependencies',
                help='Update the local dependencies to the new revisions.',
        )
        parser.add_argument(
                '-a', '--ambiguous', action='store_true', default=False,
                dest='tag_mode',
                help=('Use possibly ambiguous revisions, such as tags, '
                      'bookmarks, branches.'),
        )

        self._arguments = parser.parse_args(args if len(args) > 0 else None)

    @property
    def dep_config(self):
        """Provide the dependencies by using ensure_dependencies.read_dep().

        Since this program is meant to be run inside a repository which uses
        the buildtools' dependency functionalities, we are sure that
        ensure_dependencies.py and dependencies exist.

        However, ensure_dependencies is currently only compatible with python2.
        Due to this we invoke a python2 interpreter to run our dependencies.py,
        which runs ensure_dependencies.read_deps() and returns the output as
        JSON data.
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
                rev = self.dep_config[self._arguments.dependency][key][1]
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
                    msg = ('warning: no issue reference in commit message: '
                           '"{message}" (commit {hash})\n').format(**change)
                    print(msg, file=sys.stderr)

        return issue_ids, noissues

    @property
    def parsed_changes(self):
        """Provide the list of changes, separated by issues and noissues.

        Returns a dictionary, containing the following two key/value pairs:
        'issue_ids': a list of issue IDs (as seen on
            https://issues.adblockplus.org/)
        'noissues': The remaining changes, with all original information (see
            DepUpdate.changes) which could not be associated with any issue.
        """
        if self._parsed_changes is None:
            self._parsed_changes = {}
            issue_ids, noissues = self._parse_changes(self.changes)
            self._parsed_changes['issue_ids'] = issue_ids
            self._parsed_changes['noissues'] = noissues
        return self._parsed_changes

    def write_diff(self):
        """Write a unified diff of all changes to STDOUT."""
        print(self._main_vcs.merged_diff(self.base_revision,
                                         self._arguments.new_revision,
                                         self._arguments.unified_lines))

    def _render(self):
        context = {}
        context['repository'] = self._arguments.dependency
        context['issue_ids'] = self.parsed_changes['issue_ids']
        context['noissues'] = self.parsed_changes['noissues']
        context['old'], context['new'] = self._build_dep_entry()

        path, filename = os.path.split(self._arguments.tmpl_path)

        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(path or './')
        ).get_template(filename).render(context)

    def lookup_integration_notes(self):
        """Search for any "Integration notes" mentions at the issue-tracker.

        Cycle through the list of issue IDs and search for "Integration Notes"
        in the associated issue on https://issues.adblockplus.org. If found,
        write the corresponding url to STDERR.
        """
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

            print('Integration notes found: ' + issue_url, file=sys.stderr)

    def write_changes(self):
        """Write a descriptive list of the changes to STDOUT."""
        for change in self.changes:
            print('( {hash} ) : {message} (by {author})'.format(**change))

    def _build_dep_entry(self):
        """Build the current and new string of dependencies file."""
        root_conf = self._dep_config['_root']
        config = self.dep_config[self._arguments.dependency]

        remote_repository_name, none_hash_rev = config.get('*', (None, None))

        current = '{} = {}'.format(self._arguments.dependency,
                                   remote_repository_name)

        possible_sources = {
            'hg_root': os.path.join(root_conf['hg'],
                                    self._arguments.dependency),
            'git_root': os.path.join(root_conf['git'],
                                     self._arguments.dependency),
        }

        current_dep_strings = {}

        for key in ['hg', 'git']:
            tmp_dep = key + ':'
            source, rev = config.get(key, (None, None))
            if source:
                possible_sources[key] = source
                tmp_dep = '{}{}@'.format(tmp_dep, source)

            if rev:
                tmp_dep += rev
            current_dep_strings[key] = tmp_dep

        if none_hash_rev:
            current = ' '.join([current, none_hash_rev])
        else:
            current = ' '.join(
                    [current, ] +
                    [current_dep_strings.get(x, '') for x in ['hg', 'git']]
            ).strip()

        if self._arguments.tag_mode:
            new = '{} = {} {}'.format(
                self._arguments.dependency,
                remote_repository_name,
                self._arguments.new_revision,
            )
        else:
            main_ex = self._main_vcs.EXECUTABLE
            mirror_ex = self._main_vcs._other_cls.EXECUTABLE

            if self._arguments.local_mirror:
                mirror = self._arguments.local_mirror
            else:
                for key in [mirror_ex, mirror_ex + '_root']:
                    if key in possible_sources:
                        mirror = possible_sources[key]
                        break

            hashes = {
                main_ex: self.changes[0]['hash'],
                mirror_ex: self._main_vcs.mirrored_hash(
                       self.changes[0]['author'],
                       self.changes[0]['date'],
                       self.changes[0]['message'],
                       mirror),
                }

            for key in [main_ex, mirror_ex]:
                if key in possible_sources:
                    hashes[key] = '{}@{}'.format(possible_sources[key],
                                                 hashes[key])

            new = '{} = {} hg:{hg} git:{git}'.format(
                self._arguments.dependency, remote_repository_name, **hashes)

        return current, new

    def update_dependencies_file(self):
        """Update the local dependencies file to contain the new revision."""
        current, new = self._build_dep_entry()

        dependency_path = os.path.join(self._cwd, 'dependencies')

        with io.open(dependency_path, 'r', encoding='utf-8') as fp:
            current_deps = fp.read()

        with io.open(dependency_path, 'w', encoding='utf-8') as fp:
            fp.write(current_deps.replace(current, new))

    def __call__(self):
        """Let this class's objects be callable, run all desired tasks."""
        if self._arguments.lookup_inotes:
            self.lookup_integration_notes()

        if self._arguments.diff:
            self.write_diff()

        if self._arguments.update_dependencies:
            self.update_dependencies_file()

        if self._arguments.changes:
            self.write_changes()
        elif self._arguments.make_issue:
            print(self._render())
