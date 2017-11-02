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

Execute setup.py:
```
$ python setup.py install
```

_Please note: setup.py will additionally install [jinja2](http://jinja.pocoo.org/docs/2.9/) on your machine._

## Running the programm

Simply call the executable inside a repository which as dependencies.
A few examples:

### Show a list of changes between the current revision and the remote master for adblockpluscore

```
$ depup changes adblockpluscore

( dbfc37143497 ) : Noissue - Fix the escaping of '{' and '}' in CSS selectors (by Hubert Figuière)
( 1bb277740973 ) : Issue 5160 - Alias new class names and properties. (by Hubert Figuière)
( 280efb445cc1 ) : Issue 5147 - Invalidate wrapper on delete (by Hubert Figuière)

```

### Generate a bare issue body with an ambiguous tag, rather than hashes

```
$ depup issue adblockpluscore -r master -a
=== Background ===

CHANGE ME!

=== Included changes in `adblockpluscore` ===
The list of changes imported by this is:
[[TicketQuery(id=5147&id=5160,order=id,desc=1,format=table,col=summary|component)]]

|| [https://hg.adblockplus.org/adblockpluscore/rev/dbfc37143497 dbfc37143497] || Noissue - Fix the escaping of '{' and '}' in CSS selectors || Hubert Figuière ||


=== What to change ===
Update the `adblockpluscore` dependency

**from**:
`adblockpluscore = adblockpluscore hg:b21bddce2678 git:2b57122`
**to**:
`adblockpluscore = adblockpluscore master`

=== Integration Notes ===

CHANGE ME!

=== Hints for testers ===

CHANGE ME!
```

### Print information on the last 5 commits and lookup possible "Integration Notes" for those

```
(gitrepo)$ depup changes adblockpluscore -r HEAD~5 -l

WARNING: you are trying to downgrade the dependency!
Integration notes found: https://issues.adblockplus.org/ticket/5735
( 2b57122 ) : Noissue - Fixed typo with getLocalizedTexts function Review: https://codereview.adblockplus.org/29567746/ (by Dave Barker)
( 662ce93 ) : Noissue - Updated recommended subscriptions (by Wladimir Palant)
( 0591517 ) : Issue 5773 - use ES6 for stylesheets and cssRules. (by Hubert Figuière)
( 991b43c ) : Issue 5797 - Removed obsolete arguments from ElemHideEmulation constructor (by Sebastian Noack)
( e533ded ) : Issue 5735 - Use JS Map instead of Object for matcher properties filterByKeyword and keywordByFilter (by Sergei Zabolotskikh)
```

## Templating

You can provide your own template, which can be rendered with all available information. The default template renders as shown in the above example.

There are at any time these values exposed to the template:

- `repository` - the repository to update (equals the positional argument of depup).
- `issue_ids` - A list of encountered Issue ids or an empty array.
- `noissues` - Changes which could not be associated with an issue id. Either an empty array, or a list of dictionaries, each containg the following key/value pairs:
  * `author` - the author of the commit.
  * `hash` - the hash of the commit (format depends on the VCS which is used).
  * `message` - the commit message, stripped to the first line.
  * `date` - The commit date, in the rfc822 format.
- `old` - the line, currently defining the dependency in the dependencies file.
- `new` - the newly generated entry in the dependencies file, pointing to the new revision.

For more information, please consult [the jinja2 documentation](http://jinja.pocoo.org/docs/2.9/).

## Help

Depup comes with an integrated help page for each subcommand. The full pages:

### Root

```
usage: depup [-h] {diff,issue,changes} ...

Prepare a dependency update.

This script executes the automatable work which needs to be done for a
dependency update and provides additional information, i.e. a complete
diff of imported changes, as well as related integration notes.

optional arguments:
  -h, --help            show this help message and exit

Subcommands:
  {diff,issue,changes}  Required, the actual command to be executed. Execute
                        run "<subcommand> -h" for more information.

```

### diff

```
usage: depup diff [-h] [-r NEW_REVISION] [-a] [-f FILENAME] [-l] [-s]
                  [-m LOCAL_MIRROR] [-n UNIFIED_LINES]
                  dependency

optional arguments:
  -h, --help            show this help message and exit
  -n UNIFIED_LINES, --n-context-lines UNIFIED_LINES
                        Number of unified context lines to be added to the
                        diff. Defaults to 16 (Used only with -d/--diff).

Shared options:
  dependency            The dependency to be updated, as specified in the
                        dependencies file.
  -r NEW_REVISION, --revision NEW_REVISION
                        The revision to update to. Defaults to the remote
                        master bookmark/branch. Must be accessible by the
                        dependency's vcs.
  -a, --ambiguous       Use possibly ambiguous revisions, such as tags,
                        bookmarks, branches.
  -f FILENAME, --filename FILENAME
                        When specified, write the subcommand's output to the
                        given file, rather than to STDOUT.
  -l, --lookup-integration-notes
                        Search https://issues.adblockplus.org for integration
                        notes associated with the included issue IDs. The
                        results are written to STDERR. CAUTION: This is a very
                        network heavy operation.
  -s, --skip-mirror     Do not use any mirror.
  -m LOCAL_MIRROR, --mirrored-repository LOCAL_MIRROR
                        Path to the local copy of a mirrored repository. Used
                        to fetch the corresponding hash. If not given, the
                        source parsed from the dependencies file is used.

```

### changes

```
usage: depup changes [-h] [-r NEW_REVISION] [-a] [-f FILENAME] [-l] [-s]
                     [-m LOCAL_MIRROR]
                     dependency

optional arguments:
  -h, --help            show this help message and exit

Shared options:
  dependency            The dependency to be updated, as specified in the
                        dependencies file.
  -r NEW_REVISION, --revision NEW_REVISION
                        The revision to update to. Defaults to the remote
                        master bookmark/branch. Must be accessible by the
                        dependency's vcs.
  -a, --ambiguous       Use possibly ambiguous revisions, such as tags,
                        bookmarks, branches.
  -f FILENAME, --filename FILENAME
                        When specified, write the subcommand's output to the
                        given file, rather than to STDOUT.
  -l, --lookup-integration-notes
                        Search https://issues.adblockplus.org for integration
                        notes associated with the included issue IDs. The
                        results are written to STDERR. CAUTION: This is a very
                        network heavy operation.
  -s, --skip-mirror     Do not use any mirror.
  -m LOCAL_MIRROR, --mirrored-repository LOCAL_MIRROR
                        Path to the local copy of a mirrored repository. Used
                        to fetch the corresponding hash. If not given, the
                        source parsed from the dependencies file is used.

```

### issue

```
usage: depup issue [-h] [-r NEW_REVISION] [-a] [-f FILENAME] [-l] [-s]
                   [-m LOCAL_MIRROR] [-t TMPL_PATH]
                   dependency

optional arguments:
  -h, --help            show this help message and exit
  -t TMPL_PATH, --template TMPL_PATH
                        The template to use. Defaults to the provided
                        default.trac (Used only with -i/--issue).

Shared options:
  dependency            The dependency to be updated, as specified in the
                        dependencies file.
  -r NEW_REVISION, --revision NEW_REVISION
                        The revision to update to. Defaults to the remote
                        master bookmark/branch. Must be accessible by the
                        dependency's vcs.
  -a, --ambiguous       Use possibly ambiguous revisions, such as tags,
                        bookmarks, branches.
  -f FILENAME, --filename FILENAME
                        When specified, write the subcommand's output to the
                        given file, rather than to STDOUT.
  -l, --lookup-integration-notes
                        Search https://issues.adblockplus.org for integration
                        notes associated with the included issue IDs. The
                        results are written to STDERR. CAUTION: This is a very
                        network heavy operation.
  -s, --skip-mirror     Do not use any mirror.
  -m LOCAL_MIRROR, --mirrored-repository LOCAL_MIRROR
                        Path to the local copy of a mirrored repository. Used
                        to fetch the corresponding hash. If not given, the
                        source parsed from the dependencies file is used.

```
