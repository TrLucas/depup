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

"""This module contains the tests for src/vcs.py."""

from __future__ import unicode_literals

import io
import os
import subprocess

import pytest

from src.vcs import Vcs, Git, Mercurial

DATA_DIR = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), 'data'
)


class _VcsCmd(object):
    def __init__(self, executable, cwd):
        self.executable = executable
        self.cwd = cwd

    def run(self, *cmd):
        return subprocess.check_output((self.executable,) + cmd, cwd=self.cwd)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return


@pytest.fixture
def hg_repo(tmpdir):
    """Create a mercurial repository for the tests."""
    hg_dir = tmpdir.mkdir('hg').mkdir('testrepo')
    hg = _VcsCmd('hg', str(hg_dir))

    hg.run('init')
    hg.run('import', os.path.join(DATA_DIR, '0.diff'))
    hg.run('import', os.path.join(DATA_DIR, '1.diff'))

    hg.run('update', '-c', '0')
    hg.run('import', os.path.join(DATA_DIR, '2.diff'))
    hg.run('bookmark', 'master')

    with io.open(os.path.join(str(hg_dir), '.hg', 'hgrc'), 'w') as fp:
        fp.write('[paths]{}default = {}{}'.format(os.linesep, str(hg_dir),
                                                  os.linesep))
    return hg_dir


@pytest.fixture
def git_repo(tmpdir):
    """Create a git repository for the tests."""
    git_dir = tmpdir.mkdir('git').mkdir('testrepo')
    git = _VcsCmd('git', str(git_dir))

    git.run('init')
    git.run('am', os.path.join(DATA_DIR, '0.diff'))
    git.run('am', os.path.join(DATA_DIR, '2.diff'))

    git.run('checkout', '-b', 'splitted')
    git.run('am', os.path.join(DATA_DIR, '1.diff'))
    git.run('checkout', 'master')

    git.run('remote', 'add', 'origin', str(git_dir))
    return git_dir


def test_factory(git_repo, hg_repo):
    """Test VCS determination."""
    assert Vcs.factory(str(git_repo)).__class__ == Git
    assert Vcs.factory(str(hg_repo)).__class__ == Mercurial


def test_hash_lookup(git_repo, hg_repo):
    """Assert correct mirroring between Mercurial / Git."""
    git = Vcs.factory(str(git_repo))
    hg = Vcs.factory(str(hg_repo))

    first_git_commit = git.run_cmd('rev-list', '--max-parents=0',
                                   'HEAD').strip()
    first_hg_commit = hg.run_cmd('log', '-r', '0',
                                 '--template="{node|short}"').strip()

    change_list_git = git.change_list(first_git_commit, 'master')
    change_list_hg = hg.change_list(first_hg_commit, 'master')

    git.enhance_changes_information(change_list_git, str(hg_repo), False)
    hg.enhance_changes_information(change_list_hg, str(git_repo), False)

    assert len(change_list_git) == len(change_list_hg)
    for i, change in enumerate(change_list_git):
        assert change['hg_hash'] == change_list_hg[i]['hg_hash']
        assert change['git_hash'] == change_list_hg[i]['git_hash']
        assert change['hg_url'] == change_list_hg[i]['hg_url']
        assert change['git_url'] == change_list_hg[i]['git_url']


def test_dirty_check_and_clean(git_repo, hg_repo):
    """Test discovering and cleaning of a dirty repository."""
    for repo in [git_repo, hg_repo]:
        vcs = Vcs.factory(str(repo))

        repo.join('foobar.txt').write('foobar')
        assert vcs.repo_is_clean() is False

        vcs.undo_changes()
        assert vcs.repo_is_clean()

        repo.join('foo').write('bar')
        assert vcs.repo_is_clean() is False


def test_tmp_cloning_and_cleanup(git_repo, hg_repo):
    """Test cleanup after temporary cloning a repository."""
    for repo in [git_repo, hg_repo]:
        with Vcs.factory(str(repo), True) as tmp_repo:
            tmp_dir = tmp_repo._cwd
            tmp_repo._get_latest()

        assert os.path.exists(tmp_dir) is False


def test_commit(git_repo, hg_repo):
    """Test commit functionality of Vcs."""
    for repo in [git_repo, hg_repo]:
        vcs = Vcs.factory(str(repo))

        repo.join('foobar.txt').write('foobar')

        vcs.commit_changes('Testing commit')

        assert 'Testing commit' in vcs.run_cmd('log')
