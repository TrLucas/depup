# Easy dependency updating



## Introduction

This program is meant to ease up the process of gathering information /
preparing an issue on issues.adblockplus.org, in order to update a given
dependency.

You can run this programm to get a list of potentially included changes
(represented by their commit messages), you can create a unified diff of all
potentially included changes or you can create an issue body, which is supposed
to be filed on https://issues.adblockplus.org.

Since there won't be any way to bridge submodules / subrepositories between
Git and Mercurial any time soon, we will stay dependent on a manual approach
for mirroring these ourselves.

## Requirements

 - [Python 2.7](https://www.python.org/download/releases/2.7/)
 - [Git](https://git-scm.com/)
 - [Mercurial](https://www.mercurial-scm.org/)

_(Please note, as soon as https://hg.adblockplus.org/buildtools/file/tip/ensure_dependencies.py
is made Python 3.* compatible, the requirement for Python 2.7.* will be removed.)_

## Compatibility

This program runs with both Python 2.7.* and Python 3.*.

## Installation

Execute setup.py:
```
$ python setup.py install
```

_Please note: setup.py will additionally install
[jinja2](http://jinja.pocoo.org/docs/2.9/) on your machine._

## Limitations

Mainly due to humans being involved in reporting issues, there is no guarantee
that looking up integration notes will find everything that is needed to be
done, in order to update to a new revision.

## Running the programm

Simply call the executable inside a repository which as dependencies.
A few examples:

### Show a list of changes between the current revision and the remote master for adblockpluscore

```
$ depup changes adblockpluscore
```

Result:

```
( dbfc37143497 ) : Noissue - Fix the escaping of '{' and '}' in CSS selectors (by Hubert Figuière)
( 1bb277740973 ) : Issue 5160 - Alias new class names and properties. (by Hubert Figuière)
( 280efb445cc1 ) : Issue 5147 - Invalidate wrapper on delete (by Hubert Figuière)

```

### Generate a bare issue body for updating to the local master (-r master), but explicitly skip any mirroring (-s)

```
$ depup issue adblockpluscore -r master -s
```

Result:

```
=== Background ===

CHANGE ME!

=== Included changes in `adblockpluscore` ===
The list of changes imported by this is:
[[TicketQuery(id=5728&id=5773&id=5797&id=5735,order=id,desc=1,format=table,col=summary|component)]]

|| [https://hg.adblockplus.org/adblockpluscore/rev/dbfc37143497 dbfc37143497] || Noissue - Fix the escaping of '{' and '}' in CSS selectors || Hubert Figuière ||
|| [https://hg.adblockplus.org/adblockpluscore/rev/b21bddce2678 b21bddce2678] || Noissue - Fixed typo with getLocalizedTexts function || Dave Barker ||
|| [https://hg.adblockplus.org/adblockpluscore/rev/a1b481e7d728 a1b481e7d728] || Noissue - Updated recommended subscriptions || Wladimir Palant ||
|| [https://hg.adblockplus.org/adblockpluscore/rev/fb758f96f7bb fb758f96f7bb] || Noissue - rename variable 'ret' to more meaningful 'filter' in lib/filterClasses.js || Sergei Zabolotskikh ||


=== What to change ===
Update the `adblockpluscore` dependency to:

|| **mercurial** || **git** ||
|| dbfc37143497 || NO MIRROR ||

=== Integration Notes ===

CHANGE ME!

=== Hints for testers ===

CHANGE ME!
```

### Print information on the last 5 commits (-r HEAD~5) and lookup possible "Integration Notes" for those (-l)

```
(gitrepo)$ depup changes adblockpluscore -r HEAD~5 -l
```

Result:
```
WARNING: you are trying to downgrade the dependency!
Integration notes found: https://issues.adblockplus.org/ticket/5735
( 2b57122 ) : Noissue - Fixed typo with getLocalizedTexts function Review: https://codereview.adblockplus.org/29567746/ (by Dave Barker)
( 662ce93 ) : Noissue - Updated recommended subscriptions (by Wladimir Palant)
( 0591517 ) : Issue 5773 - use ES6 for stylesheets and cssRules. (by Hubert Figuière)
( 991b43c ) : Issue 5797 - Removed obsolete arguments from ElemHideEmulation constructor (by Sebastian Noack)
( e533ded ) : Issue 5735 - Use JS Map instead of Object for matcher properties filterByKeyword and keywordByFilter (by Sergei Zabolotskikh)
```

### Generate a unified diff for the changes to buildtools @ remote master
```
$ depup diff buildtools
```

Result:
```
diff --git a/.gitignore b/.gitignore
index 4090c27..5832582 100644
--- a/.gitignore
+++ b/.gitignore
@@ -1,3 +1,6 @@
 *.pyc
 *.pyo
 /.tox
+/.cache
+.coverage

...
...
```

## Help

Depup comes with an integrated help page for each subcommand. The full pages:

### Root

```
usage: depup [-h] [subcommand] ...

Prepare a dependency update.

This script executes the automatable work which needs to be done for a
dependency update and provides additional information, i.e. a complete
diff of imported changes, as well as related integration notes.

optional arguments:
  -h, --help    show this help message and exit

Subcommands:
  [subcommand]  Required, the actual command to be executed. Execute run
                "<subcommand> -h" for more information.
    diff        Create a unified diff of all changes
    issue       Render an issue body
    changes     Generate a list of commits between two revisions

```

### diff

```
usage: depup diff [-h] [-r NEW_REVISION] [-f FILENAME] [-l] [-s]
                  [-m LOCAL_MIRROR] [-n UNIFIED_LINES]
                  dependency

Invoke the current repository's VCS to generate a diff, containing all changes
made between two revisions.

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
usage: depup changes [-h] [-r NEW_REVISION] [-f FILENAME] [-l] [-s]
                     [-m LOCAL_MIRROR]
                     dependency

Generate a list of commit hashes and commit messages between the dependency's
current revision and a given new revision.

optional arguments:
  -h, --help            show this help message and exit

Shared options:
  dependency            The dependency to be updated, as specified in the
                        dependencies file.
  -r NEW_REVISION, --revision NEW_REVISION
                        The revision to update to. Defaults to the remote
                        master bookmark/branch. Must be accessible by the
                        dependency's vcs.
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
usage: depup issue [-h] [-r NEW_REVISION] [-f FILENAME] [-l] [-s]
                   [-m LOCAL_MIRROR] [-t TMPL_PATH]
                   dependency

Render an issue subject and an issue body, according to the given template.

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

## Templating

You can provide your own template, which can be rendered with all available information. The default template renders as shown in the above example.

There are at any time these values exposed to the template:

- `repository` - the repository to update (equals the positional argument of depup).
- `raw_changes` - the unparsed but mirrored list of changes (if existing, the item at index 0 is the revision to update to), each item containing the following key/value pairs:
  * `author` - the author of the commit.
  * `message` - the commit message, stripped to the first line.
  * `date` - The commit date, in the rfc822 format.
  * `git_hash` - the git hash of the commit, (mirrored if root VCS is mercurial, 'NO MIRROR' if mirroring was skipped)
  * `git_url` - the revisions' url @ www.github.com
  * `hg_hash` - the mercurial hash of the commit, (mirrored if root VCS is git, 'NO MIRROR' if mirroring was skipped)
  * `hg_url` - the revisions url @ hg.adblockplus.org
- `issue_ids` - A list of encountered Issue ids or an empty array.
- `noissues` - Changes which could not be associated with an issue id. Either an empty array, or a list of dictionaries, each containing the same key/value pairs as `raw_changes`
- `hg_hash` - the mercurial hash for the new revision ('NO MIRROR' if mercurial is the mirror's vcs and mirroring is skipped)
- `git_hash` the git hash for the new revision ('NO MIRROR' if git is the mirror's vcs and mirroring is skipped)

For more information, please consult [the jinja2 documentation](http://jinja.pocoo.org/docs/2.9/).

### Example template

The following template generates an issue body, from which the line in "What to change"
can be copied to the dependencies file.

Additionally, the hashes in the "What to change" section are hyperlinks to
their respective hosts.

```
SUBJECT:
Update {{ repository }} dependency to {{ hg_hash }}

=== Background ===

CHANGE ME!

=== Included changes in `{{ repository }}` ===
The list of changes imported by this is:
[[TicketQuery({%- for issue_id in issue_ids -%}
    id={{ issue_id }}{%- if not loop.last -%}&{%- endif -%}
{%- endfor -%}
,order=id,desc=1,format=table,col=summary|component)]]

{% for change in noissues -%}
|| [{{ change.hg_url }} {{ change.hg_hash }}] || {{ change.message }} || {{ change.author }} ||
{% endfor %}

=== What to change ===
Update the `{{ repository }}` dependency to:

{{ repository }} = {{ repository }} hg:[{{ raw_changes[0].hg_url }} {{ raw_changes[0].hg_hash }}] git:[{{ raw_changes[0].git_url }} {{ raw_changes[0].git_hash }}]

|| **mercurial** || **git** ||
|| {{ hg_hash }} || {{ git_hash }} ||

=== Integration Notes ===

CHANGE ME!

=== Hints for testers ===

CHANGE ME!
```
