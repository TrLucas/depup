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
import shutil
import subprocess
import sys
import tempfile
try:
    from urllib import urlopen
except ImportError:
    from urllib.request import urlopen

import jinja2


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

        self._tmp_girepo_path = None
        self._mirrored_git_hash = None

        self._base_revision = None
        self._parsed_changes = None
        self._arguments = None

        self._dep_config = None

        self._tag_mode = False

        self._default_tmpl_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'templates',
            'default.trac')

        self._make_arguments(*args)

        self.changes = self._get_changes(self.base_revision,
                                         self._arguments.new_revision)

        new_is_hash = self.changes[0]['hash'] == self._arguments.new_revision
        if not new_is_hash and not self._arguments.force_hash:
            self._tag_mode = True

    def _make_arguments(self, *args):
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
                      'master bookmark.'),
        )
        parser.add_argument(
                '-i', '--issue', action='store_true', dest='make_issue',
                help=('Generate a bare issue body to STDOUT with included '
                      'changes that can be filed on '
                      'https://issues.adblockplus.org/. Uses either the '
                      'provided default template, or that provided  by '
                      '--template'),
        )
        parser.add_argument(
                '-c', '--changes', action='store_true', default=False,
                help=('Write the commit messages of all changes between the '
                      'given revisions to STDOUT. If given, -i/--issue is '
                      'ignored.'),
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
                '-t', '--template', dest='tmpl_path',
                default=self._default_tmpl_path,
                help=('The template to use. Defaults to the provided '
                      'default.trac'),
        )
        parser.add_argument(
                '-g', '--gitrepo', dest='local_mirror',
                help=('Path to the local copy of a mirrored git repository. '
                      'Used to fetch the corresponding git hash. If not '
                      'given, the source parsed from the dependencies file is '
                      'used.'),
        )
        parser.add_argument(
                '-d', '--diff-file', dest='diff_file',
                help='File to write a complete diff to.',
        )
        parser.add_argument(
                '-u', '--update', action='store_true',
                dest='update_dependencies',
                help='Update the local dependencies to the new revisions.',
        )
        parser.add_argument(
                '-f', '--force-hash', action='store_true', default=False,
                dest='force_hash',
                help=('Force the generated issue or dependency update to '
                      'contain hashes, rather than tags / bookmarks / '
                      'branches'),
        )

        self._arguments = parser.parse_args(args if len(args) > 0 else None)

    def _run_vcs(self, *args, **kwargs):
        """Run mercurial with our overriden defaults."""
        cmd = self.VCS_EXECUTABLE + args
        try:
            return subprocess.check_output(
                cmd,
                cwd=os.path.join(self._cwd, self._arguments.dependency),
            ).decode('utf-8')
        except subprocess.CalledProcessError as e:
            print(e.output, file=sys.stderr)
            raise

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
            for key in ['*', 'hg']:
                rev = self.dep_config[self._arguments.dependency][key][1]
                if rev is not None:
                    self._base_revision = rev
                    break
        return self._base_revision

    @property
    def mirrored_git_hash(self):
        """Provide the mirrored git-hash of the new revision.

        If no local mirror is given, we attempt to perform a bare clone of
        the mirrored repository from the configured host.
        """
        dependency = self._arguments.dependency

        if self._mirrored_git_hash is None:
            repo_path = None
            if not self._arguments.local_mirror:
                self._tmp_girepo_path = tempfile.mkdtemp()
                repo_path = self._tmp_girepo_path

                # Get the git mirror, which should be used, from the dependency
                # configuration
                try:
                    try:
                        mirror_source, _ = self.dep_config[dependency]['git']
                    except KeyError:
                        mirror_source = None
                    if mirror_source is None:
                        mirror_source = self.dep_config['_root']['git']
                except KeyError:
                    raise self.MirrorException('No valid mirror was found.')

                # Clone the bare repository, in order to only get the commit
                # history but no sources.
                fpnull = open(os.devnull, 'w')
                subprocess.check_output([
                    'git', 'clone', '--bare',
                    os.path.join(mirror_source, dependency),
                    repo_path], stderr=fpnull)
            else:
                repo_path = self._arguments.local_mirror
                # Make sure that the latest commit history is available
                subprocess.check_output(['git', 'fetch'], cwd=repo_path)

            change = self.changes[0]

            # To get the correct mirrored hash, we have to search for the
            # combination of all 3 paramters: Author, commit message and date.
            cmd = ['git', 'log', '--author={}'.format(change['author']),
                   '--grep={}'.format(change['message']), '--not',
                   '--before={}'.format(change['date']), '--not',
                   '--after={}'.format(change['date']), '--pretty=format:%h']

            self._mirrored_git_hash = subprocess.check_output(
                cmd, cwd=repo_path
            ).decode('utf-8')
            if not self._mirrored_git_hash:
                raise self.MirrorException(
                    'Could not find the mirrored git hash.')
        return self._mirrored_git_hash

    def _get_changes(self, base, new):
        """Provide a list of changes between the 2 configured revisions.

        Return a list of change-dictionaries, each containing the following
        key/values pairs:
            'hash': the commit's hash
            'author': the commit's author
            'date': the committing date
            'message': the commit's message (stripped down to the first line)
        """
        # Make sure that the latest commit history is available
        self._run_vcs('pull')

        # Commit messages containing double quotes will break JSON parsing, if
        # we don't escape them properly
        log_template = ('\\{__DQ__hash__DQ__:__DQ__{node|short}__DQ__,'
                        '__DQ__author__DQ__:__DQ__{author|person}__DQ__,'
                        '__DQ__date__DQ__:__DQ__{date|rfc822date}__DQ__,'
                        '__DQ__message__DQ__:__DQ__{desc|strip|'
                        'firstline}__DQ__}\n')

        changes = self._run_vcs(
            'log', '--template', log_template, '-r', '{}:{}'.format(new, base)
        ).replace('"', '\\"').replace('__DQ__', '"')

        # 'hg log' contains the last specified revision. We don't want to
        # process that.
        return json.loads(
            '[{}]'.format(','.join(changes.strip().splitlines()))
        )[:-1]

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

    def write_diff(self, filename):
        """Write a unified (hg) diff of all changes to the given file."""
        with io.open(filename, 'w', encoding='utf-8') as fp:
            fp.write(self._run_vcs(
                'diff', '-r', '{}:{}'.format(self._arguments.new_revision,
                                             self.base_revision)
            ))

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
        config = self.dep_config[self._arguments.dependency]

        root_source, root_rev = config.get('*', (None, None))

        current = '{} = {}'.format(self._arguments.dependency, root_source)

        if root_rev:
            current = ' '.join([current, root_rev])
        else:
            for key in ['hg', 'git']:
                source, rev = config.get(key, (None, None))
                if rev:
                    if source:
                        dep_string = '{}:{}@{}'.format(key, source, rev)
                    else:
                        dep_string = '{}:{}'.format(key, rev)
                    current = ' '.join([current, dep_string])

        if self._tag_mode:
            new = '{} = {} {}'.format(
                self._arguments.dependency,
                root_source,
                self._arguments.new_revision,
            )

        else:
            new = '{} = {} hg:{} git:{}'.format(
                self._arguments.dependency,
                root_source,
                self.changes[0]['hash'],
                self.mirrored_git_hash,
            )

        return current, new

    def update_dependencies_file(self):
        """Update the local dependencies file to contain the new revision."""
        current, new = self._build_dep_entry()

        dependency_path = os.path.join(self._cwd, 'dependencies')

        with io.open(dependency_path, 'r', encoding='utf-8') as fp:
            current_deps = fp.read()

        with io.open(dependency_path, 'w', encoding='utf-8') as fp:
            fp.write(current_deps.replace(current, new))

    def __enter__(self):
        """Let this class's objects be available as a context."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Clean up after leaving this class's objects context.

        In DepUpdate.mirrored_git_hash, we potentially create a temporary
        directory. Remove this directory after leaving self's context.
        """
        if self._tmp_girepo_path is not None:
            shutil.rmtree(self._tmp_girepo_path, ignore_errors=True)

    def __call__(self):
        """Let this class's objects be callable, run all desired tasks."""
        if self._arguments.lookup_inotes:
            self.lookup_integration_notes()

        if self._arguments.diff_file is not None:
            self.write_diff(self._arguments.diff_file)

        if self._arguments.update_dependencies:
            self.update_dependencies_file()

        if self._arguments.changes:
            self.write_changes()
        elif self._arguments.make_issue:
            print(self._render())
