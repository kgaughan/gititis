import configparser
import os

from gitosis import gitdaemon
from gitosis.test.util import write_file


def exported(path: str) -> bool:
    assert os.path.isdir(path)
    p = gitdaemon.export_ok_path(path)
    return os.path.exists(p)


def test_git_daemon_export_ok_repo_missing(tmpdir):
    # configured but not created yet; before first push
    cfg = configparser.RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("repo foo")
    cfg.set("repo foo", "daemon", "yes")
    gitdaemon.set_export_ok(config=cfg)
    assert not os.path.exists(os.path.join(tmpdir, "foo"))
    assert not os.path.exists(os.path.join(tmpdir, "foo.git"))


def test_git_daemon_export_ok_repo_missing_parent(tmpdir):
    # configured but not created yet; before first push
    cfg = configparser.RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("repo foo/bar")
    cfg.set("repo foo/bar", "daemon", "yes")
    gitdaemon.set_export_ok(config=cfg)
    assert not os.path.exists(os.path.join(tmpdir, "foo"))


def test_git_daemon_export_ok_allowed(tmpdir):
    path = os.path.join(tmpdir, "foo.git")
    os.mkdir(path)
    cfg = configparser.RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("repo foo")
    cfg.set("repo foo", "daemon", "yes")
    gitdaemon.set_export_ok(config=cfg)
    assert exported(path)


def test_git_daemon_export_ok_allowed_already(tmpdir):
    path = os.path.join(tmpdir, "foo.git")
    os.mkdir(path)
    write_file(gitdaemon.export_ok_path(path), "")
    cfg = configparser.RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("repo foo")
    cfg.set("repo foo", "daemon", "yes")
    gitdaemon.set_export_ok(config=cfg)
    assert exported(path)


def test_git_daemon_export_ok_denied(tmpdir):
    path = os.path.join(tmpdir, "foo.git")
    os.mkdir(path)
    write_file(gitdaemon.export_ok_path(path), "")
    cfg = configparser.RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("repo foo")
    cfg.set("repo foo", "daemon", "no")
    gitdaemon.set_export_ok(config=cfg)
    assert not exported(path)


def test_git_daemon_export_ok_denied_already(tmpdir):
    path = os.path.join(tmpdir, "foo.git")
    os.mkdir(path)
    cfg = configparser.RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("repo foo")
    cfg.set("repo foo", "daemon", "no")
    gitdaemon.set_export_ok(config=cfg)
    assert not exported(path)


def test_git_daemon_export_ok_subdirs(tmpdir):
    foo = os.path.join(tmpdir, "foo")
    os.mkdir(foo)
    path = os.path.join(foo, "bar.git")
    os.mkdir(path)
    cfg = configparser.RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("repo foo/bar")
    cfg.set("repo foo/bar", "daemon", "yes")
    gitdaemon.set_export_ok(config=cfg)
    assert exported(path)


def test_git_daemon_export_ok_denied_default(tmpdir):
    path = os.path.join(tmpdir, "foo.git")
    os.mkdir(path)
    write_file(gitdaemon.export_ok_path(path), "")
    cfg = configparser.RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.add_section("repo foo")
    gitdaemon.set_export_ok(config=cfg)
    assert not exported(path)


def test_git_daemon_export_ok_denied_even_not_configured(tmpdir):
    # repositories not mentioned in config also get touched; this is
    # to avoid security trouble, otherwise we might expose (or
    # continue to expose) old repositories removed from config
    path = os.path.join(tmpdir, "foo.git")
    os.mkdir(path)
    write_file(gitdaemon.export_ok_path(path), "")
    cfg = configparser.RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    gitdaemon.set_export_ok(config=cfg)
    assert not exported(path)


def test_git_daemon_export_ok_allowed_global(tmpdir):
    for repo in [
        "foo.git",
        "quux.git",
        "thud.git",
    ]:
        path = os.path.join(tmpdir, repo)
        os.mkdir(path)

    # try to provoke an invalid allow
    write_file(gitdaemon.export_ok_path(os.path.join(tmpdir, "thud.git")), "")

    cfg = configparser.RawConfigParser()
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", tmpdir)
    cfg.set("gitosis", "daemon", "yes")
    cfg.add_section("repo foo")
    cfg.add_section("repo quux")
    # same as default, no effect
    cfg.set("repo quux", "daemon", "yes")
    cfg.add_section("repo thud")
    # this is still hidden
    cfg.set("repo thud", "daemon", "no")
    gitdaemon.set_export_ok(config=cfg)
    assert exported(os.path.join(tmpdir, "foo.git"))
    assert exported(os.path.join(tmpdir, "quux.git"))
    assert not exported(os.path.join(tmpdir, "thud.git"))
