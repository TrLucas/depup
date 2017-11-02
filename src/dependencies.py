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

"""Script run ensure_dependencies.get_deps() externally."""

from __future__ import print_function

import json
import os
import sys


def dep_as_json():
    """Read configured dependencies via ensure_dependencies.get_deps()."""
    cwd = os.getcwd()
    sys.path.append(cwd)
    import ensure_dependencies
    return json.dumps(ensure_dependencies.read_deps(cwd), indent=4)


if __name__ == '__main__':
    print(dep_as_json())
