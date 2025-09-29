import configparser
import os

from gitosis import init, repository, run_hook
from gitosis.util import read_file


def test_post_update_simple(tmpdir):
    repos = os.path.join(tmpdir, "repositories")
    os.mkdir(repos)
    admin_repository = os.path.join(repos, "gitosis-admin.git")
    pubkey = (
        "ssh-somealgo "
        + "0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser@fakehost"
    )
    user = "theadmin"
    init.init_admin_repository(
        git_dir=admin_repository,
        pubkey=pubkey,
        user=user,
    )
    repository.init(path=os.path.join(repos, "forweb.git"))
    repository.init(path=os.path.join(repos, "fordaemon.git"))
    repository.fast_import(
        git_dir=admin_repository,
        committer="John Doe <jdoe@example.com>",
        commit_msg="""\
stuff
""",
        parent="refs/heads/master^0",
        files=[
            (
                "gitosis.conf",
                """\
[gitosis]

[group gitosis-admin]
members = theadmin
writable = gitosis-admin

[repo fordaemon]
daemon = yes

[repo forweb]
gitweb = yes
owner = John Doe
description = blah blah
""",
            ),
            (
                "keydir/jdoe.pub",
                "ssh-somealgo "
                + "0123456789ABCDEFBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
                + "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
                + "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
                + "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB= jdoe@host.example.com",
            ),
        ],
    )
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.add_section("gitosis")
    cfg.set("gitosis", "repositories", repos)
    generated = os.path.join(tmpdir, "generated")
    os.mkdir(generated)
    cfg.set("gitosis", "generate-files-in", generated)
    ssh = os.path.join(tmpdir, "ssh")
    os.mkdir(ssh)
    cfg.set(
        "gitosis",
        "ssh-authorized-keys-path",
        os.path.join(ssh, "authorized_keys"),
    )
    run_hook.post_update(
        cfg=cfg,
        git_dir=admin_repository,
    )
    assert read_file(os.path.join(repos, "forweb.git", "description")) == "blah blah\n"
    assert os.listdir(generated) == ["projects.list"]
    assert (
        read_file(os.path.join(generated, "projects.list"))
        == """\
forweb.git John+Doe
"""
    )
    got = os.listdir(os.path.join(repos, "fordaemon.git"))
    assert "git-daemon-export-ok" in got, f"git-daemon-export-ok not created: {got!r}"
    assert os.listdir(ssh) == ["authorized_keys"]
    got = read_file(os.path.join(ssh, "authorized_keys")).splitlines(keepends=True)
    assert (
        'command="gitosis-serve jdoe",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ssh-somealgo 0123456789ABCDEFBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB= jdoe@host.example.com\n'
        in got
    ), f"SSH authorized_keys line for jdoe not found: {got!r}"
