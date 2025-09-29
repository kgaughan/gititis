"""Enforce git-shell to only serve allowed by access control policy.
directory. The client should refer to them without any extra directory
prefix. Repository names are forced to match ALLOW_RE.
"""

import configparser
import logging
import optparse
import os
import re
import sys

from gitosis import access, app, gitdaemon, gitweb, repository, util

_log = logging.getLogger(__name__)

ALLOW_RE = re.compile("^'/*(?P<path>[a-zA-Z0-9][a-zA-Z0-9@._-]*(/[a-zA-Z0-9][a-zA-Z0-9@._-]*)*)'$")

COMMANDS_READONLY = [
    "git-upload-pack",
    "git upload-pack",
    "git-upload-archive",
    "git upload-archive",
]

COMMANDS_WRITE = [
    "git-receive-pack",
    "git receive-pack",
]


class ServingError(Exception):
    """Serving error"""

    def __str__(self) -> str:
        return f"{self.__doc__}"


class CommandMayNotContainNewlineError(ServingError):
    """Command may not contain newline"""


class UnknownCommandError(ServingError):
    """Unknown command denied"""


class UnsafeArgumentsError(ServingError):
    """Arguments to command look dangerous"""


class AccessDeniedError(ServingError):
    """Access denied to repository"""


class WriteAccessDeniedError(AccessDeniedError):
    """Repository write access denied"""


class ReadAccessDeniedError(AccessDeniedError):
    """Repository read access denied"""


def serve(
    cfg: configparser.ConfigParser,
    user: str,
    command: str,
) -> str:
    if "\n" in command:
        raise CommandMayNotContainNewlineError

    try:
        verb, args = command.split(None, 1)
    except ValueError as e:
        # all known "git-foo" commands take one argument; improve if/when needed
        raise UnknownCommandError from e

    if verb == "git":
        try:
            subverb, args = args.split(None, 1)
        except ValueError as e:
            # all known "git foo" commands take one argument; improve
            # if/when needed
            raise UnknownCommandError from e
        verb = f"{verb} {subverb}"

    if verb not in COMMANDS_WRITE and verb not in COMMANDS_READONLY:
        raise UnknownCommandError

    match = ALLOW_RE.match(args)
    if match is None:
        raise UnsafeArgumentsError

    path = match.group("path")

    # write access is always sufficient
    newpath = access.have_access(config=cfg, user=user, mode="writable", path=path)

    if newpath is None:
        # didn't have write access; try once more with the popular
        # misspelling
        newpath = access.have_access(config=cfg, user=user, mode="writeable", path=path)
        if newpath is not None:
            _log.warning('Repository "%s" config has typo: "writeable", should be "writable"', path)

    if newpath is None:
        # didn't have write access
        newpath = access.have_access(config=cfg, user=user, mode="readonly", path=path)
        if newpath is None:
            raise ReadAccessDeniedError
        if verb in COMMANDS_WRITE:
            # didn't have write access and tried to write
            raise WriteAccessDeniedError

    (topdir, relpath) = newpath
    repopath = f"{relpath}.git"
    fullpath = os.path.join(topdir, repopath)
    if not os.path.exists(fullpath):
        # it doesn't exist on the filesystem, but the configuration
        # refers to it, we're serving a write request, and the user is
        # authorized to do that: create the repository on the fly

        # create leading directories
        p = topdir
        for segment in repopath.split(os.sep)[:-1]:
            p = os.path.join(p, segment)
            os.makedirs(p, mode=0o750, exist_ok=True)

        repository.init(path=fullpath)
        gitweb.set_descriptions(config=cfg)
        generated = util.get_generated_files_dir(config=cfg)
        gitweb.generate_project_list(
            config=cfg,
            path=os.path.join(generated, "projects.list"),
        )
        gitdaemon.set_export_ok(config=cfg)

    # put the verb back together with the new path
    return f"{verb} '{fullpath}'"


class Main(app.App):
    def create_parser(self) -> optparse.OptionParser:
        parser = super().create_parser()
        parser.set_usage("%prog [OPTS] USER")
        parser.set_description("Allow restricted git operations under DIR")
        return parser

    def handle_args(
        self,
        parser: optparse.OptionParser,
        cfg: configparser.ConfigParser,
        options: optparse.Values,  # noqa: ARG002
        args: list[str],
    ) -> None:
        try:
            (user,) = args
        except ValueError:
            parser.error("Missing argument USER.")
            user = "nobody"

        os.umask(0o022)

        cmd = os.environ.get("SSH_ORIGINAL_COMMAND", None)
        if cmd is None:
            _log.error("Need SSH_ORIGINAL_COMMAND in environment.")
            sys.exit(1)

        _log.debug("Got command: %s", cmd)

        os.chdir(os.path.expanduser("~"))

        try:
            newcmd = serve(
                cfg=cfg,
                user=user,
                command=cmd,
            )
        except ServingError as e:
            _log.error("%s", e)
            sys.exit(1)

        _log.debug("Serving %s", newcmd)
        os.environ["GITOSIS_USER"] = user
        os.execvp("git", ["git", "shell", "-c", newcmd])
        _log.error("Cannot execute git-shell.")
        sys.exit(1)
