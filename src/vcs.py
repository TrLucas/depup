from __future__ import print_function, unicode_literals

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile


class Vcs(object):
    JSON_DQUOTES = '__DQ__'

    class VcsException(Exception):
        pass

    def __init__(self, cwd):
        self._cwd = cwd
        self._mirrored_hash_for = {}

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
        return self.run_cmd('diff', '--unified=' + str(n_unified),
                            *(self._rev_comb(rev_a, rev_b)))

    def change_list(self, rev_a, rev_b):
        self._get_latest()

        log_format = self._log_format()
        rev_cmd = self._rev_comb(rev_a, rev_b)

        changes = self.run_cmd(*('log',) + log_format + rev_cmd)
        return self._changes_as_json(changes)

    def mirrored_hash(self, author, date, message, dep_location):
        key_tuple = (author, date, message)
        prev = self._mirrored_hash_for.get(key_tuple, None)
        if prev is not None:
            return prev

        tmp_cwd = None
        if not self._other_cls.is_vcs_for_repo(dep_location):
            tmp_cwd, other_vcs = self._other_cls.make_temporary_repository(
                    dep_location)
        else:
            other_vcs = self._other_cls(dep_location)

        other_vcs._get_latest()
        other_hash = other_vcs.matching_hash(author, date, message)

        if tmp_cwd is not None:
            shutil.rmtree(tmp_cwd, ignore_errors=True)

        self._mirrored_hash_for[key_tuple] = other_hash
        return other_hash

    @staticmethod
    def factory(cwd):
        obj = None
        for cls in [Git, Mercurial]:
            if cls.is_vcs_for_repo(cwd):
                if obj is not None:
                    raise Vcs.VcsException(
                            "Found multiple possible VCS' for {}".format(cwd))
                obj = cls(cwd)

        if obj is None:
            raise Vcs.VcsException('No valid VCS found for ' + cwd)
        return obj


class Mercurial(Vcs):
    EXECUTABLE = 'hg'
    BASE_CMD = (EXECUTABLE, '--config', 'defaults.log=', '--config',
                'defaults.pull=', '--config', 'defaults.diff=')
    UPDATE_LOCAL_HISTORY = 'pull'
    LOG_TEMLATE = ('\\{"hash":"{node|short}","author":"{author|person}",'
                   '"date":"{date|rfc822date}","message":"{desc|strip|'
                   'firstline}"}\n')

    def __init__(self, cwd):
        self._other_cls = Git
        super(Mercurial, self).__init__(cwd)

    def _rev_comb(self, rev_a, rev_b):
        return ('-r', '{}:{}'.format(rev_a, rev_b))

    def _log_format(self):
        log_format = self.LOG_TEMLATE.replace('"', self.JSON_DQUOTES)
        return ('--template', log_format)

    def change_list(self, base_rev, new_rev):
        # Mercurial's conmmand for producing a log between revisions
        # switches the revisions. Additoinally the current parent is returned.
        return super(Mercurial, self).change_list(new_rev, base_rev)[:-1]

    def matching_hash(self, author, date, message):
        return self.run_cmd('log', '-u', author, '-d', date, '--keyword',
                            message, '--template', '{node|short}')

    @staticmethod
    def is_vcs_for_repo(cwd):
        return os.path.exists(os.path.join(cwd, '.hg'))

    @staticmethod
    def make_temporary_repository(dep_location):
        cwd = tempfile.mkdtemp()
        os.mkdir(os.path.join(cwd, '.hg'))

        with io.open(os.path.join(cwd, '.hg', 'hgrc'), 'w') as fp:
            fp.write('[paths]{}default = {}{}'.format(os.linesep, dep_location,
                                                      os.linesep))
        return cwd, Mercurial(cwd)


class Git(Vcs):
    EXECUTABLE = 'git'
    BASE_CMD = (EXECUTABLE,)
    UPDATE_LOCAL_HISTORY = 'fetch'
    LOG_TEMLATE = '{"hash":"%h","author":"%an","date":"%aD","message":"%s"}'

    def __init__(self, cwd):
        self._other_cls = Mercurial
        super(Git, self).__init__(cwd)

    def _rev_comb(self, rev_a, rev_b):
        return ('{}..{}'.format(rev_a, rev_b),)

    def _log_format(self):
        return ('--pretty=format:{}'.format(self.LOG_TEMLATE.replace(
            '"', self.JSON_DQUOTES)),)

    def matching_hash(self, author, date, message):
        return self.run_cmd('log', '--author={}'.format(author),
                            '--grep={}'.format(message), '--not',
                            '--before={}'.format(date), '--not',
                            '--after={}'.format(date), '--pretty=format:%h')

    def _make_bare(self, dep_location):
        self.run_cmd('clone', '--bare', dep_location, self._cwd)

    @staticmethod
    def is_vcs_for_repo(cwd):
        return os.path.exists(os.path.join(cwd, '.git'))

    @staticmethod
    def make_temporary_repository(dep_location):
        cwd = tempfile.mkdtemp()
        vcs = Git(cwd)

        vcs._make_bare(dep_location)

        return cwd, vcs
