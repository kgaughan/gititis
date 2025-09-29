import os
import secrets
import subprocess

import pytest

from gitosis import repository
from gitosis.util import read_file, write_file

from .util import check_mode


def check_bare(path):
    # we want it to be a bare repository
    assert not os.path.exists(os.path.join(path, ".git"))


def test_init_simple(tmpdir):
    path = os.path.join(tmpdir, "repo.git")
    repository.init(path)
    check_mode(path, 0o750, is_dir=True)
    check_bare(path)


def test_init_exist_dir(tmpdir):
    path = os.path.join(tmpdir, "repo.git")
    os.makedirs(path, mode=0o710)
    check_mode(path, 0o710, is_dir=True)
    repository.init(path)
    # my weird access mode is preserved
    check_mode(path, 0o710, is_dir=True)
    check_bare(path)


def test_init_exist_git(tmpdir):
    path = os.path.join(tmpdir, "repo.git")
    repository.init(path)
    repository.init(path)
    check_mode(path, 0o750, is_dir=True)
    check_bare(path)


def test_init_templates(tmpdir):
    path = os.path.join(tmpdir, "repo.git")
    templatedir = os.path.join(
        os.path.dirname(__file__),
        "mocktemplates",
    )

    # for reproducibility
    os.umask(0o022)

    repository.init(path, template=templatedir)
    repository.init(path)
    got = read_file(os.path.join(path, "no-confusion"))
    assert got == "i should show up\n"
    check_mode(
        os.path.join(path, "hooks", "post-update"),
        0o755,
        is_file=True,
    )
    got = read_file(os.path.join(path, "hooks", "post-update"))
    assert got == "#!/bin/sh\n# i can override standard templates\n"


def test_init_environment(tmpdir):
    path = os.path.join(tmpdir, "repo.git")
    mockbindir = os.path.join(tmpdir, "mockbin")
    os.mkdir(mockbindir)
    mockgit = os.path.join(mockbindir, "git")
    write_file(
        mockgit,
        """\
#!/bin/sh
set -e
# git wrapper for gitosis unit tests
printf '%s' "$GITOSIS_UNITTEST_COOKIE" >"$(dirname "$0")/../cookie"

# strip away my special PATH insert so system git will be found
PATH="${PATH#*:}"

exec git "$@"
""",
    )
    os.chmod(mockgit, 0o700)
    magic_cookie = secrets.token_hex(16)
    good_path = os.environ["PATH"]
    try:
        os.environ["PATH"] = f"{mockbindir}:{good_path}"
        os.environ["GITOSIS_UNITTEST_COOKIE"] = magic_cookie
        repository.init(path)
    finally:
        os.environ["PATH"] = good_path
        os.environ.pop("GITOSIS_UNITTEST_COOKIE", None)
    assert sorted(os.listdir(tmpdir)) == sorted(
        [
            "mockbin",
            "cookie",
            "repo.git",
        ]
    )
    got = read_file(os.path.join(tmpdir, "cookie"))
    assert got == magic_cookie


def test_fast_import_environment(tmpdir):
    path = os.path.join(tmpdir, "repo.git")
    repository.init(path=path)
    mockbindir = os.path.join(tmpdir, "mockbin")
    os.mkdir(mockbindir)
    mockgit = os.path.join(mockbindir, "git")
    write_file(
        mockgit,
        """\
#!/bin/sh
set -e
# git wrapper for gitosis unit tests
printf '%s' "$GITOSIS_UNITTEST_COOKIE" >"$(dirname "$0")/../cookie"

# strip away my special PATH insert so system git will be found
PATH="${PATH#*:}"

exec git "$@"
""",
    )
    os.chmod(mockgit, 0o700)
    magic_cookie = secrets.token_hex(16)
    good_path = os.environ["PATH"]
    try:
        os.environ["PATH"] = f"{mockbindir}:{good_path}"
        os.environ["GITOSIS_UNITTEST_COOKIE"] = magic_cookie
        repository.fast_import(
            git_dir=path,
            commit_msg="foo initial bar",
            committer="Mr. Unit Test <unit.test@example.com>",
            files=[
                ("foo", "bar\n"),
            ],
        )
    finally:
        os.environ["PATH"] = good_path
        os.environ.pop("GITOSIS_UNITTEST_COOKIE", None)
    assert sorted(os.listdir(tmpdir)) == sorted(
        [
            "mockbin",
            "cookie",
            "repo.git",
        ]
    )
    got = read_file(os.path.join(tmpdir, "cookie"))
    assert got == magic_cookie

    git_dir = os.path.join(tmpdir, "repo.git")
    repository.init(path=git_dir)
    repository.fast_import(
        git_dir=git_dir,
        committer="John Doe <jdoe@example.com>",
        commit_msg="""\
Reverse the polarity of the neutron flow.

Frobitz the quux and eschew obfuscation.
""",
        files=[
            ("foo", "content"),
            ("bar/quux", "another"),
        ],
    )
    export = os.path.join(tmpdir, "export")
    repository.export(git_dir=git_dir, path=export)
    assert sorted(os.listdir(export)) == sorted(["foo", "bar"])
    assert read_file(os.path.join(export, "foo")) == "content"
    assert os.listdir(os.path.join(export, "bar")) == ["quux"]
    assert read_file(os.path.join(export, "bar", "quux")) == "another"
    child = subprocess.Popen(
        args=[
            "git",
            f"--git-dir={git_dir}",
            "cat-file",
            "commit",
            "HEAD",
        ],
        cwd=git_dir,
        stdout=subprocess.PIPE,
        close_fds=True,
        universal_newlines=True,
    )
    assert child.stdout is not None
    got = child.stdout.read().splitlines()
    returncode = child.wait()
    if returncode != 0:
        raise RuntimeError(f"git exit status {returncode}")
    assert got[0].split(None, 1)[0] == "tree"
    assert got[1].rsplit(None, 2)[0] == "author John Doe <jdoe@example.com>"
    assert got[2].rsplit(None, 2)[0] == "committer John Doe <jdoe@example.com>"
    assert got[3] == ""
    assert got[4] == "Reverse the polarity of the neutron flow."
    assert got[5] == ""
    assert got[6] == "Frobitz the quux and eschew obfuscation."
    assert got[7:] == []


def test_export_environment(tmpdir):
    git_dir = os.path.join(tmpdir, "repo.git")
    mockbindir = os.path.join(tmpdir, "mockbin")
    os.mkdir(mockbindir)
    mockgit = os.path.join(mockbindir, "git")
    write_file(
        mockgit,
        """\
#!/bin/sh
set -e
# git wrapper for gitosis unit tests
printf '%s\n' "$GITOSIS_UNITTEST_COOKIE" >>"$(dirname "$0")/../cookie"

# strip away my special PATH insert so system git will be found
PATH="${PATH#*:}"

exec git "$@"
""",
    )
    os.chmod(mockgit, 0o700)
    repository.init(path=git_dir)
    repository.fast_import(
        git_dir=git_dir,
        committer="John Doe <jdoe@example.com>",
        commit_msg="""\
Reverse the polarity of the neutron flow.

Frobitz the quux and eschew obfuscation.
""",
        files=[
            ("foo", "content"),
            ("bar/quux", "another"),
        ],
    )
    export = os.path.join(tmpdir, "export")
    magic_cookie = secrets.token_hex(16)
    good_path = os.environ["PATH"]
    try:
        os.environ["PATH"] = f"{mockbindir}:{good_path}"
        os.environ["GITOSIS_UNITTEST_COOKIE"] = magic_cookie
        repository.export(git_dir=git_dir, path=export)
    finally:
        os.environ["PATH"] = good_path
        os.environ.pop("GITOSIS_UNITTEST_COOKIE", None)
    got = read_file(os.path.join(tmpdir, "cookie"))
    # export runs git twice
    assert got == f"{magic_cookie}\n{magic_cookie}\n"


def test_has_initial_commit_fail_not_a_git_dir(tmpdir):
    with pytest.raises(
        repository.GitRevParseError,
        match="rev-parse failed: exit status 128",
    ):
        repository.has_initial_commit(git_dir=tmpdir)


def test_has_initial_commit_no(tmpdir):
    repository.init(path=tmpdir)
    assert not repository.has_initial_commit(git_dir=tmpdir)


def test_has_initial_commit_yes(tmpdir):
    repository.init(path=tmpdir)
    repository.fast_import(
        git_dir=tmpdir,
        commit_msg="fakecommit",
        committer="John Doe <jdoe@example.com>",
        files=[],
    )
    assert repository.has_initial_commit(git_dir=tmpdir)


def test_has_initial_commit_environment(tmpdir):
    mockbindir = os.path.join(tmpdir, "mockbin")
    os.mkdir(mockbindir)
    mockgit = os.path.join(mockbindir, "git")
    write_file(
        mockgit,
        """\
#!/bin/sh
set -e
# git wrapper for gitosis unit tests
printf '%s' "$GITOSIS_UNITTEST_COOKIE" >"$(dirname "$0")/../cookie"

# strip away my special PATH insert so system git will be found
PATH="${PATH#*:}"

exec git "$@"
""",
    )
    os.chmod(mockgit, 0o700)
    repository.init(path=tmpdir)
    repository.fast_import(
        git_dir=tmpdir,
        commit_msg="fakecommit",
        committer="John Doe <jdoe@example.com>",
        files=[],
    )
    magic_cookie = secrets.token_hex(16)
    good_path = os.environ["PATH"]
    try:
        os.environ["PATH"] = f"{mockbindir}:{good_path}"
        os.environ["GITOSIS_UNITTEST_COOKIE"] = magic_cookie
        assert repository.has_initial_commit(git_dir=tmpdir)
    finally:
        os.environ["PATH"] = good_path
        os.environ.pop("GITOSIS_UNITTEST_COOKIE", None)
    assert read_file(os.path.join(tmpdir, "cookie")) == magic_cookie


def test_fast_import_parent(tmpdir):
    path = os.path.join(tmpdir, "repo.git")
    repository.init(path=path)
    repository.fast_import(
        git_dir=path,
        commit_msg="foo initial bar",
        committer="Mr. Unit Test <unit.test@example.com>",
        files=[
            ("foo", "bar\n"),
        ],
    )
    repository.fast_import(
        git_dir=path,
        commit_msg="another",
        committer="Sam One Else <sam@example.com>",
        parent="refs/heads/master^0",
        files=[
            ("quux", "thud\n"),
        ],
    )
    export = os.path.join(tmpdir, "export")
    repository.export(
        git_dir=path,
        path=export,
    )
    assert sorted(os.listdir(export)) == sorted(["foo", "quux"])
