"""Perform gitosis actions for a git hook."""

import configparser
import errno
import logging
import optparse
import os
import shutil
import sys

from gitosis import app, gitdaemon, gitweb, repository, ssh, util

_log = logging.getLogger(__name__)


def post_update(cfg: configparser.ConfigParser, git_dir: str) -> None:
    export = os.path.join(git_dir, "gitosis-export")
    try:
        shutil.rmtree(export)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise
    repository.export(git_dir=git_dir, path=export)
    os.rename(
        os.path.join(export, "gitosis.conf"),
        os.path.join(export, os.path.pardir, "gitosis.conf"),
    )
    # re-read config to get up-to-date settings
    cfg.read(os.path.join(export, os.path.pardir, "gitosis.conf"))
    gitweb.set_descriptions(config=cfg)
    generated = util.get_generated_files_dir(config=cfg)
    gitweb.generate_project_list(
        config=cfg,
        path=os.path.join(generated, "projects.list"),
    )
    gitdaemon.set_export_ok(config=cfg)
    authorized_keys = util.get_ssh_authorized_keys_path(config=cfg)
    ssh.write_authorized_keys(
        path=authorized_keys,
        keydir=os.path.join(export, "keydir"),
    )


class Main(app.App):
    def create_parser(self) -> optparse.OptionParser:
        parser = super().create_parser()
        parser.set_usage("%prog [OPTS] HOOK")
        parser.set_description("Perform gitosis actions for a git hook")
        return parser

    def handle_args(
        self,
        parser: optparse.OptionParser,
        cfg: configparser.ConfigParser,
        options: optparse.Values,  # noqa: ARG002
        args: list[str],
    ) -> None:
        hook = None
        try:
            (hook,) = args
        except ValueError:
            parser.error("Missing argument HOOK.")

        os.umask(0o022)

        git_dir = os.environ.get("GIT_DIR")
        if git_dir is None:
            _log.error("Must have GIT_DIR set in enviroment")
            sys.exit(1)

        if hook == "post-update":
            _log.info("Running hook %s", hook)
            post_update(cfg, git_dir)
            _log.info("Done.")
        else:
            _log.warning("Ignoring unknown hook: %s", hook)
