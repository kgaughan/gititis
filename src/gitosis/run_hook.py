"""
Perform gitosis actions for a git hook.
"""

import errno
import logging
import os
import shutil
import sys

from gitosis import app, gitdaemon, gitweb, repository, ssh, util


def post_update(cfg, git_dir):
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
        os.path.join(export, "..", "gitosis.conf"),
    )
    # re-read config to get up-to-date settings
    cfg.read(os.path.join(export, "..", "gitosis.conf"))
    gitweb.set_descriptions(
        config=cfg,
    )
    generated = util.get_generated_files_dir(config=cfg)
    gitweb.generate_project_list(
        config=cfg,
        path=os.path.join(generated, "projects.list"),
    )
    gitdaemon.set_export_ok(
        config=cfg,
    )
    authorized_keys = util.get_ssh_authorized_keys_path(config=cfg)
    ssh.write_authorized_keys(
        path=authorized_keys,
        keydir=os.path.join(export, "keydir"),
    )


class Main(app.App):
    def create_parser(self):
        parser = super().create_parser()
        parser.set_usage("%prog [OPTS] HOOK")
        parser.set_description("Perform gitosis actions for a git hook")
        return parser

    def handle_args(self, parser, cfg, options, args):  # noqa: ARG002
        hook = None
        try:
            (hook,) = args
        except ValueError:
            parser.error("Missing argument HOOK.")

        log = logging.getLogger("gitosis.run_hook")
        os.umask(0o022)

        git_dir = os.environ.get("GIT_DIR")
        if git_dir is None:
            log.error("Must have GIT_DIR set in enviroment")
            sys.exit(1)

        if hook == "post-update":
            log.info("Running hook %s", hook)
            post_update(cfg, git_dir)
            log.info("Done.")
        else:
            log.warning("Ignoring unknown hook: %r", hook)
