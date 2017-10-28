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
