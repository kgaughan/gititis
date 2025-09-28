"""
Initialize a user account for use with gitosis.
"""

import configparser
import errno
import io
import logging
import os
import sys

from gitosis import app, repository, run_hook, ssh, util

log = logging.getLogger("gitosis.init")


def read_ssh_pubkey(fp=None):
    if fp is None:
        fp = sys.stdin
    line = fp.readline()
    return line


class InsecureSSHKeyUsernameError(Exception):
    """Username contains not allowed characters"""

    def __str__(self):
        return f"{self.__doc__}: {': '.join(self.args)}"


def ssh_extract_user(pubkey):
    _, user = pubkey.rsplit(None, 1)
    if ssh.is_safe_username(user):
        return user
    else:
        raise InsecureSSHKeyUsernameError(repr(user))


def initial_commit(git_dir, cfg, pubkey, user):
    repository.fast_import(
        git_dir=git_dir,
        commit_msg="Automatic creation of gitosis repository.",
        committer=f"Gitosis Admin <{user}>",
        files=[
            (f"keydir/{user}.pub", pubkey),
            ("gitosis.conf", cfg),
        ],
    )


def symlink_config(git_dir):
    dst = os.path.expanduser("~/.gitosis.conf")
    tmp = f"{dst}.{os.getpid()}.tmp"
    try:
        os.unlink(tmp)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise
    os.symlink(os.path.join(git_dir, "gitosis.conf"), tmp)
    os.rename(tmp, dst)


def init_admin_repository(
    git_dir,
    pubkey,
    user,
):
    repository.init(
        path=git_dir,
        # This is not ideal, but I don't have anything better right now. This
        # should be using importlib, but I need to experiment with it more to
        # see if I can get it playing nice with git.
        template=os.path.join(os.path.dirname(__file__), "templates/admin"),
    )
    repository.init(path=git_dir, template=None)

    # can't rely on setuptools and all kinds of distro packaging to
    # have kept our templates executable, it seems
    os.chmod(os.path.join(git_dir, "hooks", "post-update"), 0o755)  # noqa: S103

    if not repository.has_initial_commit(git_dir):
        log.info("Making initial commit...")
        # ConfigParser does not guarantee order, so jump through hoops
        # to make sure [gitosis] is first
        cfg_file = io.StringIO()
        print("[gitosis]", file=cfg_file)
        print(file=cfg_file)
        cfg = configparser.RawConfigParser()
        cfg.add_section("group gitosis-admin")
        cfg.set("group gitosis-admin", "members", user)
        cfg.set("group gitosis-admin", "writable", "gitosis-admin")
        cfg.write(cfg_file)
        initial_commit(
            git_dir=git_dir,
            cfg=cfg_file.getvalue(),
            pubkey=pubkey,
            user=user,
        )


class Main(app.App):
    def create_parser(self):
        parser = super().create_parser()
        parser.set_usage("%prog [OPTS]")
        parser.set_description("Initialize a user account for use with gitosis")
        return parser

    def read_config(self, *a, **kw):
        # ignore errors that result from non-existent config file
        try:
            super().read_config(*a, **kw)
        except app.ConfigFileDoesNotExistError:
            pass

    def handle_args(self, parser, cfg, options, args):
        super().handle_args(parser, cfg, options, args)

        os.umask(0o022)

        log.info("Reading SSH public key...")
        pubkey = read_ssh_pubkey()
        user = ssh_extract_user(pubkey)
        if user is None:
            log.error("Cannot parse user from SSH public key.")
            sys.exit(1)
        log.info("Admin user is %r", user)
        log.info("Creating generated files directory...")
        generated = util.get_generated_files_dir(config=cfg)
        os.makedirs(generated, exist_ok=True)
        log.info("Creating repository structure...")
        repositories = util.get_repository_dir(cfg)
        os.makedirs(repositories, exist_ok=True)
        admin_repository = os.path.join(repositories, "gitosis-admin.git")
        init_admin_repository(
            git_dir=admin_repository,
            pubkey=pubkey,
            user=user,
        )
        log.info("Running post-update hook...")
        os.makedirs(os.path.expanduser("~/.ssh"), mode=0o700, exist_ok=True)
        run_hook.post_update(cfg=cfg, git_dir=admin_repository)
        log.info("Symlinking ~/.gitosis.conf to repository...")
        symlink_config(git_dir=admin_repository)
        log.info("Done.")
