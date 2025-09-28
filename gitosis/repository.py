import errno
import os
import re
import subprocess
import sys


class GitError(Exception):
    """git failed"""

    def __str__(self):
        return f"{self.__doc__}: {': '.join(self.args)}"


class GitInitError(Exception):
    """git init failed"""


def init(
    path,
    template=None,
    _git=None,
):
    """
    Create a git repository at C{path} (if missing).

    Leading directories of C{path} must exist.

    @param path: Path of repository create.

    @type path: str

    @param template: Template directory, to pass to C{git init}.

    @type template: str
    """
    if _git is None:
        _git = "git"

    os.makedirs(path, mode=0o750, exist_ok=True)
    args = [
        _git,
        "--git-dir=.",
        "init",
        "--quiet",
    ]
    if template is not None:
        args.append(f"--template={template}")
    returncode = subprocess.call(
        args=args,
        cwd=path,
        stdout=sys.stderr,
        close_fds=True,
    )
    if returncode != 0:
        raise GitInitError(f"exit status {returncode}")


class GitFastImportError(GitError):
    """git fast-import failed"""

    pass


def fast_import(
    git_dir,
    commit_msg,
    committer,
    files,
    parent=None,
):
    """
    Create an initial commit.
    """
    child = subprocess.Popen(
        args=[
            "git",
            "--git-dir=.",
            "fast-import",
            "--quiet",
            "--date-format=now",
        ],
        cwd=git_dir,
        stdin=subprocess.PIPE,
        close_fds=True,
        universal_newlines=True,
    )
    files = list(files)
    for index, (_, content) in enumerate(files):
        child.stdin.write(f"""\
blob
mark :{index + 1}
data {len(content)}
{content}
""")
    child.stdin.write(f"""\
commit refs/heads/master
committer {committer} now
data {len(commit_msg)}
{commit_msg}
""")
    if parent is not None:
        child.stdin.write(f"""\
from {parent}
""")
    for index, (path, _) in enumerate(files):
        child.stdin.write(f"M 100644 :{index + 1} {path}\n")
    child.stdin.close()
    returncode = child.wait()
    if returncode != 0:
        raise GitFastImportError("git fast-import failed", f"exit status {returncode}")


class GitExportError(GitError):
    """Export failed"""

    pass


class GitReadTreeError(GitExportError):
    """git read-tree failed"""


class GitCheckoutIndexError(GitExportError):
    """git checkout-index failed"""


def export(git_dir, path):
    try:
        os.mkdir(path)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise
    returncode = subprocess.call(
        args=[
            "git",
            f"--git-dir={git_dir}",
            "read-tree",
            "HEAD",
        ],
        close_fds=True,
    )
    if returncode != 0:
        raise GitReadTreeError(f"exit status {returncode}")
    # jumping through hoops to be compatible with git versions
    # that don't have --work-tree=
    env = {}
    env.update(os.environ)
    env["GIT_WORK_TREE"] = "."
    returncode = subprocess.call(
        args=[
            "git",
            f"--git-dir={os.path.abspath(git_dir)}",
            "checkout-index",
            "-a",
            "-f",
        ],
        cwd=path,
        close_fds=True,
        env=env,
    )
    if returncode != 0:
        raise GitCheckoutIndexError(f"exit status {returncode}")


class GitHasInitialCommitError(GitError):
    """Check for initial commit failed"""


class GitRevParseError(GitError):
    """rev-parse failed"""


def has_initial_commit(git_dir):
    child = subprocess.Popen(
        args=[
            "git",
            "--git-dir=.",
            "rev-parse",
            "HEAD",
        ],
        cwd=git_dir,
        stdout=subprocess.PIPE,
        close_fds=True,
        universal_newlines=True,
    )
    got = child.stdout.read()
    returncode = child.wait()
    if returncode != 0:
        raise GitRevParseError(f"exit status {returncode}")
    if got == "HEAD\n":
        return False
    elif re.match("^[0-9a-f]{40}\n$", got):
        return True
    else:
        msg = f"Unknown git HEAD: {got!r}"
        raise GitHasInitialCommitError(msg)
