import configparser
from io import StringIO
import os

from gitosis import gitweb
from gitosis.util import read_file, write_file


def test_projects_list_empty():
    cfg = configparser.ConfigParser(interpolation=None)
    got = StringIO()
    gitweb.generate_project_list_fp(config=cfg, fp=got)
    assert (
        got.getvalue()
        == """\
"""
    )


def test_projects_list_repo_denied():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("repo foo/bar")
    got = StringIO()
    gitweb.generate_project_list_fp(config=cfg, fp=got)
    assert (
        got.getvalue()
        == """\
"""
    )


def test_projects_list_no_owner():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("repo foo/bar")
    cfg.set("repo foo/bar", "gitweb", "yes")
    got = StringIO()
    gitweb.generate_project_list_fp(config=cfg, fp=got)
    assert (
        got.getvalue()
        == """\
foo%2Fbar
"""
    )


def test_projects_list_have_owner():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("repo foo/bar")
    cfg.set("repo foo/bar", "gitweb", "yes")
    cfg.set("repo foo/bar", "owner", "John Doe")
    got = StringIO()
    gitweb.generate_project_list_fp(config=cfg, fp=got)
    assert (
        got.getvalue()
        == """\
foo%2Fbar John+Doe
"""
    )


def test_projects_list_multiple():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("gitosis")
    cfg.add_section("repo foo/bar")
    cfg.set("repo foo/bar", "owner", "John Doe")
    cfg.set("repo foo/bar", "gitweb", "yes")
    cfg.add_section("repo quux")
    cfg.set("repo quux", "gitweb", "yes")
    got = StringIO()
    gitweb.generate_project_list_fp(config=cfg, fp=got)
    assert frozenset(got.getvalue().splitlines(keepends=True)) == frozenset(["quux\n", "foo%2Fbar John+Doe\n"])


def test_projects_list_multiple_global_gitweb_yes():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("gitosis")
    cfg.set("gitosis", "gitweb", "yes")
    cfg.add_section("repo foo/bar")
    cfg.set("repo foo/bar", "owner", "John Doe")
    cfg.add_section("repo quux")
    # same as default, no effect
    cfg.set("repo quux", "gitweb", "yes")
    cfg.add_section("repo thud")
    # this is still hidden
    cfg.set("repo thud", "gitweb", "no")
    got = StringIO()
    gitweb.generate_project_list_fp(config=cfg, fp=got)
    assert frozenset(got.getvalue().splitlines(keepends=True)) == frozenset(["quux\n", "foo%2Fbar John+Doe\n"])


def test_projects_list_really_ends_with_git(tmpdir):
    path = os.path.join(tmpdir, "foo.git")
    os.makedirs(path)
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", str(tmpdir))
    cfg.add_section("repo foo")
    cfg.set("repo foo", "gitweb", "yes")
    got = StringIO()
    gitweb.generate_project_list_fp(config=cfg, fp=got)
    assert (
        got.getvalue()
        == """\
foo.git
"""
    )


def test_projects_list_path(tmpdir):
    path = os.path.join(tmpdir, "foo.git")
    os.makedirs(path)
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", str(tmpdir))
    cfg.add_section("repo foo")
    cfg.set("repo foo", "gitweb", "yes")
    projects_list = os.path.join(tmpdir, "projects.list")
    gitweb.generate_project_list(config=cfg, path=projects_list)
    got = read_file(projects_list)
    assert (
        got
        == """\
foo.git
"""
    )


def test_description_none(tmpdir):
    path = os.path.join(tmpdir, "foo.git")
    os.makedirs(path)
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", str(tmpdir))
    cfg.add_section("repo foo")
    cfg.set("repo foo", "description", "foodesc")
    gitweb.set_descriptions(
        config=cfg,
    )
    got = read_file(os.path.join(path, "description"))
    assert got == "foodesc\n"


def test_description_repo_missing(tmpdir):
    # configured but not created yet; before first push
    os.path.join(tmpdir, "foo.git")
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", str(tmpdir))
    cfg.add_section("repo foo")
    cfg.set("repo foo", "description", "foodesc")
    gitweb.set_descriptions(
        config=cfg,
    )
    assert not os.path.exists(os.path.join(tmpdir, "foo"))
    assert not os.path.exists(os.path.join(tmpdir, "foo.git"))


def test_description_repo_missing_parent(tmpdir):
    # configured but not created yet; before first push
    os.path.join(tmpdir, "foo/bar.git")
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", str(tmpdir))
    cfg.add_section("repo foo")
    cfg.set("repo foo", "description", "foodesc")
    gitweb.set_descriptions(
        config=cfg,
    )
    assert not os.path.exists(os.path.join(tmpdir, "foo"))


def test_description_default(tmpdir):
    path = os.path.join(tmpdir, "foo.git")
    os.makedirs(path)
    write_file(
        os.path.join(path, "description"),
        "Unnamed repository; edit this file to name it for gitweb.\n",
    )
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", str(tmpdir))
    cfg.add_section("repo foo")
    cfg.set("repo foo", "description", "foodesc")
    gitweb.set_descriptions(
        config=cfg,
    )
    got = read_file(os.path.join(path, "description"))
    assert got == "foodesc\n"


def test_description_not_set(tmpdir):
    path = os.path.join(tmpdir, "foo.git")
    os.makedirs(path)
    write_file(
        os.path.join(path, "description"),
        "i was here first\n",
    )
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", str(tmpdir))
    cfg.add_section("repo foo")
    gitweb.set_descriptions(
        config=cfg,
    )
    got = read_file(os.path.join(path, "description"))
    assert got == "i was here first\n"


def test_description_again(tmpdir):
    path = os.path.join(tmpdir, "foo.git")
    os.makedirs(path, exist_ok=True)
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", str(tmpdir))
    cfg.add_section("repo foo")
    cfg.set("repo foo", "description", "foodesc")
    gitweb.set_descriptions(config=cfg)
    gitweb.set_descriptions(config=cfg)
    got = read_file(os.path.join(path, "description"))
    assert got == "foodesc\n"
