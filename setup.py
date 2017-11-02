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

"""depup installation script."""

from setuptools import setup

setup(
    name='depup',
    version='0.1',
    packages=['src', ],
    data_files=[('src/templates', ['src/templates/default.trac'])],
    scripts=['depup'],
    install_requires=['jinja2'],
    tests_require=['pytest'],
    setup_requires=['pytest-runner'],
)
