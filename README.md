# Easy dependency updating

## Trivial

Since there won't be any way to bridge submodules / subrepositories between git
and mercurial any time soon, we will stay dependent on a manual approach for
mirroring these ourselves.

This program is meant to be pure convenience for those, who find themselves in
the need to update a project's dependency.

## Requirements

 - [Python 2.7](https://www.python.org/download/releases/2.7/)
 - [Git](https://git-scm.com/)
 - [Mercurial](https://www.mercurial-scm.org/)

_(Please note, as soon as https://hg.adblockplus.org/buildtools/file/tip/ensure_dependencies.py is made Python 3.* compatible, the requirement for Python 2.7.* will be removed.)_

## Compatibility

This program runs with both Python 2.7.* and Python 3.*.

## Installation

Run the setup.y:
```
$ python setup.py install
```

_Please note: setup.py will additionally install [jinja2](http://jinja.pocoo.org/docs/2.9/) on your machine._

## Running the programm

Simply call the executable inside a repository which as dependencies.
Example:

```
$ depup adblockpluscore -r master -f
```
## Help

Depup comes with an integrated help page. The full page:

```
usage: depup [-h] [-r NEW_REVISION] [-c | -i] [-t TMPL_PATH] [-l]
             [-m LOCAL_MIRROR] [-d FILENAME] [-n UNIFIED_LINES] [-u] [-f]
             dependency

Prepare a dependency update.

This script executes the automatable work which needs to be done for a
dependency update and provides additional information, i.e. a complete
diff of imported changes, as well as related integration notes.

positional arguments:
  dependency            The dependency to be updated, as specified in the
                        dependencies file.

optional arguments:
  -h, --help            show this help message and exit
  -r NEW_REVISION, --revision NEW_REVISION
                        The revision to update to. Defaults to the remote
                        master bookmark/branch. Must be accessible by the
                        dependency's vcs.
  -l, --lookup-integration-notes
                        Search https://issues.adblockplus.org for integration
                        notes associated with the included issue IDs. The
                        results are written to STDERR. CAUTION: This is a very
                        network heavy operation.
  -m LOCAL_MIRROR, --mirrored-repository LOCAL_MIRROR
                        Path to the local copy of a mirrored repository. Used
                        to fetch the corresponding hash. If not given, the
                        source parsed from the dependencies file is used.
  -u, --update          Update the local dependencies to the new revisions.
  -f, --force-hash      Force the generated issue or dependency update to
                        contain hashes, rather than tags / bookmarks /
                        branches

Output changes:
  Process the list of included changes to either a bare issue body, or print it to STDOUT.

  -c, --changes         Write the commit messages of all changes between the
                        given revisions to STDOUT.
  -i, --issue           Generate a bare issue body to STDOUT with included
                        changes that can be filed on
                        https://issues.adblockplus.org/. Uses either the
                        provided default template, or that provided by
                        --template
  -t TMPL_PATH, --template TMPL_PATH
                        The template to use. Defaults to the provided
                        default.trac

Diff creation:
  Create a unified diff over all changes, that would be included by updating to the new revision.

  -d FILENAME, --diff-file FILENAME
                        File to write a complete diff to.
  -n UNIFIED_LINES, --n-context-lines UNIFIED_LINES
                        Number of unified context lines to be added to the
                        diff. Defaults to 16

```
