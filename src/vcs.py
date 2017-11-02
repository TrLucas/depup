"""CHANGE ME."""
from __future__ import print_function, unicode_literals

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile


class Vcs(object):
    """CHANGE ME."""

    JSON_DQUOTES = '__DQ__'

    class VcsException(Exception):
        """CHANGE ME."""

    def __init__(self, location):
        """CHANGE ME."""
        self._source, self._repository = os.path.split(location)
        if not os.path.exists(location):
            self._make_temporary(location)
            self._clean_up = True
        else:
            self._cwd = location
            self._clean_up = False

    def __enter__(self):
        """CHANGE ME."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """CHANGE ME."""
        if self._clean_up:
            shutil.rmtree(self._cwd)

    @classmethod
    def is_vcs_for_repo(cls, path):
        """CHANGE ME."""
        return os.path.exists(os.path.join(path, cls.VCS_REQUIREMENT))

    def run_cmd(self, *args, **kwargs):
        """Run the vcs with the given commands."""
        cmd = self.BASE_CMD + args
        try:
            with open(os.devnull, 'w') as fpnull:
                return subprocess.check_output(
                    cmd,
                    cwd=os.path.join(self._cwd),
                    stderr=fpnull,
                ).decode('utf-8')
        except subprocess.CalledProcessError as e:
            print(e.output.decode('utf-8'), file=sys.stderr)
            raise

    def _get_latest(self):
        self.run_cmd(self.UPDATE_LOCAL_HISTORY)

    def _escape_changes(self, changes):
        return changes.replace('"', '\\"').replace(self.JSON_DQUOTES, '"')

    def _changes_as_json(self, changes):
        return json.loads(
            '[{}]'.format(','.join(
                self._escape_changes(changes).strip().splitlines()
            )))

    def merged_diff(self, rev_a, rev_b, n_unified=16):
        """CHANGE ME."""
        return self.run_cmd('diff', '--unified=' + str(n_unified),
                            *(self._rev_comb(rev_a, rev_b)))

    def change_list(self, rev_a, rev_b):
        """CHANGE ME."""
        self._get_latest()

        log_format = self._log_format()
        rev_cmd = self._rev_comb(rev_a, rev_b)

        changes = self.run_cmd(*('log',) + log_format + rev_cmd)
        return self._changes_as_json(changes)

    def enhance_changes_information(self, changes, dependency_location, fake):
        """CHANGE ME."""
        self_ex = self.EXECUTABLE
        mirr_ex = self._other_cls.EXECUTABLE

        if not fake:
            with self._other_cls(dependency_location) as mirror:
                mirror._get_latest()

                mirrored_hashes = {
                        change['hash']: mirror.matching_hash(change['author'],
                                                             change['date'],
                                                             change['message'])
                        for change in changes
                }
        else:
            mirrored_hashes = {}

        for change in changes:
            change[self_ex + '_url'] = self.REVISION_URL.format(
                    repository=self._repository, revision=change['hash'])
            change[self_ex + '_hash'] = change['hash']

            mirrored_hash = mirrored_hashes.get(change['hash'], 'NO MIRROR')
            del change['hash']

            change[mirr_ex + '_url'] = self._other_cls.REVISION_URL.format(
                    repository=self._repository, revision=mirrored_hash)
            change[mirr_ex + '_hash'] = mirrored_hash

    @staticmethod
    def factory(cwd):
        """CHANGE ME."""
        obj = None
        for cls in [Git, Mercurial]:
            if cls.is_vcs_for_repo(cwd):
                if obj is not None:
                    raise Vcs.VcsException(
                            "Found multiple possible VCS' for " + cwd)
                obj = cls(cwd)

        if obj is None:
            raise Vcs.VcsException('No valid VCS found for ' + cwd)
        return obj


class Mercurial(Vcs):
    """CHANGE ME."""

    EXECUTABLE = 'hg'
    VCS_REQUIREMENT = '.hg'
    BASE_CMD = (EXECUTABLE, '--config', 'defaults.log=', '--config',
                'defaults.pull=', '--config', 'defaults.diff=')
    UPDATE_LOCAL_HISTORY = 'pull'
    LOG_TEMLATE = ('\\{"hash":"{node|short}","author":"{author|person}",'
                   '"date":"{date|rfc822date}","message":"{desc|strip|'
                   'firstline}"}\n')

    REVISION_URL = 'https://hg.adblockplus.org/{repository}/rev/{revision}'

    def __init__(self, cwd):
        """CHANGE ME."""
        self._other_cls = Git
        super(Mercurial, self).__init__(cwd)

    def _rev_comb(self, rev_a, rev_b):
        # Only take into account those changesets, which are actually affecting
        # the repository's content. See
        # https://www.mercurial-scm.org/repo/hg/help/revsets
        return ('-r', '{}::{}'.format(rev_a, rev_b))

    def _log_format(self):
        log_format = self.LOG_TEMLATE.replace('"', self.JSON_DQUOTES)
        return ('--template', log_format)

    def change_list(self, *args):
        """CHANGE ME."""
        # Mercurial's conmmand for producing a log between revisions using the
        # revision set produced by self._rev_comb returns the changesets in a
        # reversed order. Additoinally the current revision is returned.
        return list(reversed(super(Mercurial, self).change_list(*args)[1:]))

    def matching_hash(self, author, date, message):
        """CHANGE ME."""
        return self.run_cmd('log', '-u', author, '-d', date, '--keyword',
                            message, '--template', '{node|short}')

    def _make_temporary(self, location):
        self._cwd = tempfile.mkdtemp()
        os.mkdir(os.path.join(self._cwd, '.hg'))

        with io.open(os.path.join(self._cwd, '.hg', 'hgrc'), 'w') as fp:
            fp.write('[paths]{}default = {}{}'.format(os.linesep, location,
                                                      os.linesep))


class Git(Vcs):
    """CHANGE ME."""

    EXECUTABLE = 'git'
    VCS_REQUIREMENT = '.git'
    BASE_CMD = (EXECUTABLE,)
    UPDATE_LOCAL_HISTORY = 'fetch'
    LOG_TEMLATE = '{"hash":"%h","author":"%an","date":"%aD","message":"%s"}'

    REVISION_URL = ('https://www.github.com/adblockplus/{repository}/commit/'
                    '{revision}')

    def __init__(self, cwd):
        """CHANGE ME."""
        self._other_cls = Mercurial
        super(Git, self).__init__(cwd)

    def _rev_comb(self, rev_a, rev_b):
        return ('{}..{}'.format(rev_a, rev_b),)

    def _log_format(self):
        return ('--pretty=format:{}'.format(self.LOG_TEMLATE.replace(
            '"', self.JSON_DQUOTES)),)

    def matching_hash(self, author, date, message):
        """CHANGE ME."""
        return self.run_cmd('log', '--author={}'.format(author),
                            '--grep={}'.format(message), '--not',
                            '--before={}'.format(date), '--not',
                            '--after={}'.format(date), '--pretty=format:%h')

    def _make_temporary(self, location):
        self._cwd = tempfile.mkdtemp()
        self.run_cmd('clone', '--bare', location, self._cwd)
