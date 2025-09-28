from configparser import RawConfigParser
from io import StringIO
import logging
import os
import tempfile

import pytest

from gitosis import repository, serve
from gitosis.test import util


def test_bad_newline():
    cfg = RawConfigParser()
    with pytest.raises(
        serve.CommandMayNotContainNewlineError,
        match="Command may not contain newline",
    ):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="ev\nil",
        )


def test_bad_dash_noargs():
    cfg = RawConfigParser()
    with pytest.raises(serve.UnknownCommandError, match="Unknown command denied"):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git-upload-pack",
        )


def test_bad_space_noargs():
    cfg = RawConfigParser()
    with pytest.raises(serve.UnknownCommandError, match="Unknown command denied"):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git upload-pack",
        )


def test_bad_command():
    cfg = RawConfigParser()
    with pytest.raises(serve.UnknownCommandError, match="Unknown command denied"):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="evil 'foo'",
        )


def test_bad_unsafe_arguments_not_quoted():
    cfg = RawConfigParser()
    with pytest.raises(
        serve.UnsafeArgumentsError,
        match="Arguments to command look dangerous",
    ):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git-upload-pack foo",
        )


def test_bad_unsafe_arguments_bad_characters():
    cfg = RawConfigParser()
    with pytest.raises(
        serve.UnsafeArgumentsError,
        match="Arguments to command look dangerous",
    ):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git-upload-pack 'ev!l'",
        )


def test_bad_unsafe_arguments_dotdot():
    cfg = RawConfigParser()
    with pytest.raises(
        serve.UnsafeArgumentsError,
        match="Arguments to command look dangerous",
    ):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git-upload-pack 'something/../evil'",
        )


def test_bad_forbidden_command_read_dash():
    cfg = RawConfigParser()
    with pytest.raises(serve.ReadAccessDeniedError, match="Repository read access denied"):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git-upload-pack 'foo'",
        )


def test_bad_forbidden_command_read_space():
    cfg = RawConfigParser()
    with pytest.raises(serve.ReadAccessDeniedError, match="Repository read access denied"):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git upload-pack 'foo'",
        )


def test_bad_forbidden_command_write_no_access_dash():
    cfg = RawConfigParser()
    # error message talks about read in an effort to make it more
    # obvious that jdoe doesn't have *even* read access
    with pytest.raises(serve.ReadAccessDeniedError, match="Repository read access denied"):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git-receive-pack 'foo'",
        )


def test_bad_forbidden_command_write_no_access_space():
    cfg = RawConfigParser()
    # error message talks about read in an effort to make it more
    # obvious that jdoe doesn't have *even* read access
    with pytest.raises(serve.ReadAccessDeniedError, match="Repository read access denied"):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git receive-pack 'foo'",
        )


def test_bad_forbidden_command_write_read_access_dash():
    cfg = RawConfigParser()
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "readonly", "foo")
    with pytest.raises(serve.WriteAccessDeniedError, match="Repository write access denied"):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git-receive-pack 'foo'",
        )


def test_bad_forbidden_command_write_read_access_space():
    cfg = RawConfigParser()
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "readonly", "foo")
    with pytest.raises(serve.WriteAccessDeniedError, match="Repository write access denied"):
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git receive-pack 'foo'",
        )


def test_simple_read_dash(tmpdir):
    repository.init(os.path.join(tmpdir, "foo.git"))
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "readonly", "foo")
    got = serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-upload-pack 'foo'",
    )
    assert got == f"git-upload-pack '{tmpdir}/foo.git'"


def test_simple_read_space(tmpdir):
    repository.init(os.path.join(tmpdir, "foo.git"))
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "readonly", "foo")
    got = serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git upload-pack 'foo'",
    )
    assert got == f"git upload-pack '{tmpdir}/foo.git'"


def test_read_inits_if_needed(tmpdir):
    # a clone of a non-existent repository (but where config
    # authorizes you to do that) will create the repository on the fly
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    repositories = os.path.join(tmpdir, "repositories")
    os.mkdir(repositories)
    cfg.set("gitosis", "repositories", repositories)
    generated = os.path.join(tmpdir, "generated")
    os.mkdir(generated)
    cfg.set("gitosis", "generate-files-in", generated)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "readonly", "foo")
    got = serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-upload-pack 'foo'",
    )
    assert got == f"git-upload-pack '{repositories}/foo.git'"
    assert os.listdir(repositories) == ["foo.git"]
    assert os.path.isfile(os.path.join(repositories, "foo.git", "HEAD"))


def test_simple_read_archive(tmpdir):
    repository.init(os.path.join(tmpdir, "foo.git"))
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "readonly", "foo")
    got = serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git upload-archive 'foo'",
    )
    assert got == f"git upload-archive '{tmpdir}/foo.git'"


def test_simple_write_dash(tmpdir):
    repository.init(os.path.join(tmpdir, "foo.git"))
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writable", "foo")
    got = serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-receive-pack 'foo'",
    )
    assert got == f"git-receive-pack '{tmpdir}/foo.git'"


def test_simple_write_space(tmpdir):
    repository.init(os.path.join(tmpdir, "foo.git"))
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writable", "foo")
    got = serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git receive-pack 'foo'",
    )
    assert got == f"git receive-pack '{tmpdir}/foo.git'"


def test_push_inits_if_needed(tmpdir):
    # a push to a non-existent repository (but where config authorizes
    # you to do that) will create the repository on the fly
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    repositories = os.path.join(tmpdir, "repositories")
    os.mkdir(repositories)
    cfg.set("gitosis", "repositories", repositories)
    generated = os.path.join(tmpdir, "generated")
    os.mkdir(generated)
    cfg.set("gitosis", "generate-files-in", generated)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writable", "foo")
    serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-receive-pack 'foo'",
    )
    assert os.listdir(repositories) == ["foo.git"]
    assert os.path.isfile(os.path.join(repositories, "foo.git", "HEAD"))


def test_push_inits_if_needed_have_extension(tmpdir):
    # a push to a non-existent repository (but where config authorizes
    # you to do that) will create the repository on the fly
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    repositories = os.path.join(tmpdir, "repositories")
    os.mkdir(repositories)
    cfg.set("gitosis", "repositories", repositories)
    generated = os.path.join(tmpdir, "generated")
    os.mkdir(generated)
    cfg.set("gitosis", "generate-files-in", generated)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writable", "foo")
    serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-receive-pack 'foo.git'",
    )
    assert os.listdir(repositories) == ["foo.git"]
    assert os.path.isfile(os.path.join(repositories, "foo.git", "HEAD"))


def test_push_inits_subdir_parent_missing(tmpdir):
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    repositories = os.path.join(tmpdir, "repositories")
    os.mkdir(repositories)
    cfg.set("gitosis", "repositories", repositories)
    generated = os.path.join(tmpdir, "generated")
    os.mkdir(generated)
    cfg.set("gitosis", "generate-files-in", generated)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writable", "foo/bar")
    serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-receive-pack 'foo/bar.git'",
    )
    assert os.listdir(repositories) == ["foo"]
    foo = os.path.join(repositories, "foo")
    util.check_mode(foo, 0o750, is_dir=True)
    assert os.listdir(foo) == ["bar.git"]
    assert os.path.isfile(os.path.join(repositories, "foo", "bar.git", "HEAD"))


def test_push_inits_subdir_parent_exists(tmpdir):
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    repositories = os.path.join(tmpdir, "repositories")
    os.mkdir(repositories)
    foo = os.path.join(repositories, "foo")
    # silly mode on purpose; not to be touched
    os.mkdir(foo, 0o751)
    cfg.set("gitosis", "repositories", repositories)
    generated = os.path.join(tmpdir, "generated")
    os.mkdir(generated)
    cfg.set("gitosis", "generate-files-in", generated)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writable", "foo/bar")
    serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-receive-pack 'foo/bar.git'",
    )
    assert os.listdir(repositories) == ["foo"]
    util.check_mode(foo, 0o751, is_dir=True)
    assert os.listdir(foo) == ["bar.git"]
    assert os.path.isfile(os.path.join(repositories, "foo", "bar.git", "HEAD"))


def test_push_inits_if_needed_exists_with_extension(tmpdir):
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    repositories = os.path.join(tmpdir, "repositories")
    os.mkdir(repositories)
    cfg.set("gitosis", "repositories", repositories)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writable", "foo")
    os.mkdir(os.path.join(repositories, "foo.git"))
    serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-receive-pack 'foo'",
    )
    assert os.listdir(repositories) == ["foo.git"]
    # it should *not* have HEAD here as we just mkdirred it and didn't
    # create it properly, and the mock repo didn't have anything in
    # it.. having HEAD implies serve ran git init, which is supposed
    # to be unnecessary here
    assert os.listdir(os.path.join(repositories, "foo.git")) == []


def test_push_inits_no_stdout_spam(tmpdir):
    # git init has a tendency to spew to stdout, and that confuses
    # e.g. a git push
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    repositories = os.path.join(tmpdir, "repositories")
    os.mkdir(repositories)
    cfg.set("gitosis", "repositories", repositories)
    generated = os.path.join(tmpdir, "generated")
    os.mkdir(generated)
    cfg.set("gitosis", "generate-files-in", generated)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writable", "foo")
    old_stdout = os.dup(1)
    try:
        fd, temp_filename = tempfile.mkstemp()
        os.dup2(fd, 1)
        serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git-receive-pack 'foo'",
        )
    finally:
        os.dup2(old_stdout, 1)
        os.close(old_stdout)
    with os.fdopen(fd) as new_stdout:
        new_stdout.seek(0)
        got = new_stdout.read()
    os.unlink(temp_filename)
    assert got == ""
    assert os.listdir(repositories) == ["foo.git"]
    assert os.path.isfile(os.path.join(repositories, "foo.git", "HEAD"))


def test_push_inits_sets_description(tmpdir):
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    repositories = os.path.join(tmpdir, "repositories")
    os.mkdir(repositories)
    cfg.set("gitosis", "repositories", repositories)
    generated = os.path.join(tmpdir, "generated")
    os.mkdir(generated)
    cfg.set("gitosis", "generate-files-in", generated)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writable", "foo")
    cfg.add_section("repo foo")
    cfg.set("repo foo", "description", "foodesc")
    serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-receive-pack 'foo'",
    )
    assert os.listdir(repositories) == ["foo.git"]
    path = os.path.join(repositories, "foo.git", "description")
    assert os.path.exists(path)
    got = util.read_file(path)
    assert got == "foodesc\n"


def test_push_inits_updates_projects_list(tmpdir):
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    repositories = os.path.join(tmpdir, "repositories")
    os.mkdir(repositories)
    cfg.set("gitosis", "repositories", repositories)
    generated = os.path.join(tmpdir, "generated")
    os.mkdir(generated)
    cfg.set("gitosis", "generate-files-in", generated)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writable", "foo")
    cfg.add_section("repo foo")
    cfg.set("repo foo", "gitweb", "yes")
    os.mkdir(os.path.join(repositories, "gitosis-admin.git"))
    serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-receive-pack 'foo'",
    )
    assert sorted(os.listdir(repositories)) == sorted(["foo.git", "gitosis-admin.git"])
    path = os.path.join(generated, "projects.list")
    assert os.path.exists(path)
    got = util.read_file(path)
    assert got == "foo.git\n"


def test_push_inits_sets_export_ok(tmpdir):
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    repositories = os.path.join(tmpdir, "repositories")
    os.mkdir(repositories)
    cfg.set("gitosis", "repositories", repositories)
    generated = os.path.join(tmpdir, "generated")
    os.mkdir(generated)
    cfg.set("gitosis", "generate-files-in", generated)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writable", "foo")
    cfg.add_section("repo foo")
    cfg.set("repo foo", "daemon", "yes")
    serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-receive-pack 'foo'",
    )
    assert os.listdir(repositories) == ["foo.git"]
    path = os.path.join(repositories, "foo.git", "git-daemon-export-ok")
    assert os.path.exists(path)


def test_absolute(tmpdir):
    # as the only convenient way to use non-standard SSH ports with
    # git is via the ssh://user@host:port/path syntax, and that syntax
    # forces absolute urls, just force convert absolute paths to
    # relative paths; you'll never really want absolute paths via
    # gitosis, anyway.
    repository.init(os.path.join(tmpdir, "foo.git"))
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "readonly", "foo")
    got = serve.serve(
        cfg=cfg,
        user="jdoe",
        command="git-upload-pack '/foo'",
    )
    assert got == f"git-upload-pack '{tmpdir}/foo.git'"


def test_typo_writeable(tmpdir):
    repository.init(os.path.join(tmpdir, "foo.git"))
    cfg = RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("group foo")
    cfg.set("group foo", "members", "jdoe")
    cfg.set("group foo", "writeable", "foo")
    log = logging.getLogger("gitosis.serve")
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    log.addHandler(handler)
    try:
        got = serve.serve(
            cfg=cfg,
            user="jdoe",
            command="git-receive-pack 'foo'",
        )
    finally:
        log.removeHandler(handler)
    assert got == f"git-receive-pack '{tmpdir}/foo.git'"
    handler.flush()
    assert buf.getvalue() == "Repository 'foo' config has typo \"writeable\", shou" + 'ld be "writable"\n'
