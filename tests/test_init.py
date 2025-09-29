import configparser
import os

import pytest

from gitosis import init, repository, util

from .util import check_mode


def test_ssh_extract_user_simple():
    got = init.ssh_extract_user(
        "ssh-somealgo "
        + "0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser@fakehost"
    )
    assert got == "fakeuser@fakehost"


def test_ssh_extract_user_domain():
    got = init.ssh_extract_user(
        "ssh-somealgo "
        + "0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser@fakehost.example.com"
    )
    assert got == "fakeuser@fakehost.example.com"


def test_ssh_extract_user_domain_dashes():
    got = init.ssh_extract_user(
        "ssh-somealgo "
        + "0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser@ridiculously-long.example.com"
    )
    assert got == "fakeuser@ridiculously-long.example.com"


def test_ssh_extract_user_underscore():
    got = init.ssh_extract_user(
        "ssh-somealgo "
        + "0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fake_user@example.com"
    )
    assert got == "fake_user@example.com"


def test_ssh_extract_user_dot():
    got = init.ssh_extract_user(
        "ssh-somealgo "
        + "0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fake.u.ser@example.com"
    )
    assert got == "fake.u.ser@example.com"


def test_ssh_extract_user_dash():
    got = init.ssh_extract_user(
        "ssh-somealgo "
        + "0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fake.u-ser@example.com"
    )
    assert got == "fake.u-ser@example.com"


def test_ssh_extract_user_no_at():
    got = init.ssh_extract_user(
        "ssh-somealgo "
        + "0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser"
    )
    assert got == "fakeuser"


def test_ssh_extract_user_caps():
    got = init.ssh_extract_user(
        "ssh-somealgo "
        + "0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= Fake.User@Domain.Example.Com"
    )
    assert got == "Fake.User@Domain.Example.Com"


def test_ssh_extract_user_bad():
    with pytest.raises(
        init.InsecureSSHKeyUsernameError,
        match="Username contains not allowed characters: 'ER3%#@e%'",
    ):
        init.ssh_extract_user(
            "ssh-somealgo AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= ER3%#@e%"
        )


def test_init_admin_repository(tmpdir):
    admin_repository = os.path.join(tmpdir, "admin.git")
    pubkey = (
        "ssh-somealgo "
        + "0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser@fakehost"
    )
    user = "jdoe"
    init.init_admin_repository(
        git_dir=admin_repository,
        pubkey=pubkey,
        user=user,
    )
    assert os.listdir(tmpdir) == ["admin.git"]
    hook = os.path.join(
        tmpdir,
        "admin.git",
        "hooks",
        "post-update",
    )
    check_mode(hook, 0o755, is_file=True)
    got = util.read_file(hook).splitlines()
    assert "gitosis-run-hook post-update" in got
    export_dir = os.path.join(tmpdir, "export")
    repository.export(git_dir=admin_repository, path=export_dir)
    assert sorted(os.listdir(export_dir)) == sorted(["gitosis.conf", "keydir"])
    assert os.listdir(os.path.join(export_dir, "keydir")) == ["jdoe.pub"]
    got = util.read_file(os.path.join(export_dir, "keydir", "jdoe.pub"))
    assert got == pubkey
    # the only thing guaranteed of initial config file ordering is
    # that [gitosis] is first
    got = util.read_file(os.path.join(export_dir, "gitosis.conf"))
    got = got.splitlines()[0]
    assert got == "[gitosis]"
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(os.path.join(export_dir, "gitosis.conf"))
    assert sorted(cfg.sections()) == sorted(
        [
            "gitosis",
            "group gitosis-admin",
        ]
    )
    assert cfg.items("gitosis") == []
    assert sorted(cfg.items("group gitosis-admin")) == sorted(
        [
            ("writable", "gitosis-admin"),
            ("members", "jdoe"),
        ]
    )
