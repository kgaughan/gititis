"""Generate ``gitweb`` project list based on ``gitosis.conf``.

To plug this into ``gitweb``, you have two choices.

- The global way, edit ``/etc/gitweb.conf`` to say::

        $projects_list = "/path/to/your/projects.list";

  Note that there can be only one such use of gitweb.

- The local way, create a new config file::

        do "/etc/gitweb.conf" if -e "/etc/gitweb.conf";
        $projects_list = "/path/to/your/projects.list";
        # see ``repositories`` in the ``gitosis`` section
        # of ``~/.gitosis.conf``; usually ``~/repositories``
        # but you need to expand the tilde here
        $projectroot = "/path/to/your/repositories";

   Then in your web server, set environment variable ``GITWEB_CONFIG``
   to point to this file.

   This way allows you have multiple separate uses of ``gitweb``, and
   isolates the changes a bit more nicely. Recommended.
"""

import configparser
import logging
import os
import typing as t
from urllib.parse import quote_plus

from gitosis import util

_log = logging.getLogger(__name__)


def generate_project_list_fp(config: configparser.ConfigParser, fp: t.IO) -> None:
    """Generate projects list for ``gitweb``.

    :param config: configuration to read projects from

    :param fp: writable for ``projects.list``
    :type fp: (file-like, anything with ``.write(data)``)
    """
    repositories = util.get_repository_dir(config)

    global_enable = util.get_boolean(config, "gitosis", "gitweb", default=False)

    for section in config.sections():
        parts = section.split(None, 1)
        type_ = parts.pop(0)
        if type_ != "repo":
            continue
        if not parts:
            continue

        enable = util.get_boolean(config, section, "gitweb", default=global_enable)
        if not enable:
            continue

        (name,) = parts

        if not os.path.exists(os.path.join(repositories, name)):
            namedotgit = f"{name}.git"
            if os.path.exists(os.path.join(repositories, namedotgit)):
                name = namedotgit
            else:
                _log.warning("Cannot find '%s' in '%s'", name, repositories)

        response = [name]
        owner = util.get(config, section, "owner")
        if owner is not None:
            response.append(owner)

        line = " ".join(quote_plus(s) for s in response)
        print(line, file=fp)


def generate_project_list(config: configparser.ConfigParser, path: str) -> None:
    """Generate projects list for ``gitweb``.

    :param config: configuration to read projects from

    :param path: path to write projects list to
    """
    with util.safe_open_write(path) as fp:
        generate_project_list_fp(config=config, fp=fp)


def set_descriptions(config: configparser.ConfigParser) -> None:
    """Set descriptions for gitweb use."""
    repositories = util.get_repository_dir(config)

    for section in config.sections():
        parts = section.split(None, 1)
        type_ = parts.pop(0)
        if type_ != "repo" or not parts:
            continue

        description = util.get(config, section, "description")
        if not description:
            continue

        (name,) = parts

        if not os.path.exists(os.path.join(repositories, name)):
            namedotgit = f"{name}.git"
            if os.path.exists(os.path.join(repositories, namedotgit)):
                name = namedotgit
            else:
                _log.warning("Cannot find '%s' in '%s'", name, repositories)
                continue

        path = os.path.join(
            repositories,
            name,
            "description",
        )
        with util.safe_open_write(path) as fp:
            print(description, file=fp)
