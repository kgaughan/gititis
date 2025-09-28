"""
Generate ``gitweb`` project list based on ``gitosis.conf``.

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
from urllib.parse import quote_plus

from gitosis import util


def _escape_filename(s):
    s = s.replace("\\", "\\\\")
    s = s.replace("$", "\\$")
    s = s.replace('"', '\\"')
    return s


def generate_project_list_fp(config, fp):
    """
    Generate projects list for ``gitweb``.

    :param config: configuration to read projects from
    :type config: RawConfigParser

    :param fp: writable for ``projects.list``
    :type fp: (file-like, anything with ``.write(data)``)
    """
    log = logging.getLogger("gitosis.gitweb.generate_projects_list")

    repositories = util.get_repository_dir(config)

    try:
        global_enable = config.getboolean("gitosis", "gitweb")
    except (configparser.NoSectionError, configparser.NoOptionError):
        global_enable = False

    for section in config.sections():
        parts = section.split(None, 1)
        type_ = parts.pop(0)
        if type_ != "repo":
            continue
        if not parts:
            continue

        try:
            enable = config.getboolean(section, "gitweb")
        except (configparser.NoSectionError, configparser.NoOptionError):
            enable = global_enable

        if not enable:
            continue

        (name,) = parts

        if not os.path.exists(os.path.join(repositories, name)):
            namedotgit = f"{name}.git"
            if os.path.exists(os.path.join(repositories, namedotgit)):
                name = namedotgit
            else:
                log.warning(f"Cannot find {name!r} in {repositories!r}")

        response = [name]
        try:
            owner = config.get(section, "owner")
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
        else:
            response.append(owner)

        line = " ".join(quote_plus(s) for s in response)
        print(line, file=fp)


def generate_project_list(config, path):
    """
    Generate projects list for ``gitweb``.

    :param config: configuration to read projects from
    :type config: RawConfigParser

    :param path: path to write projects list to
    :type path: str
    """
    tmp = f"{path}.{os.getpid()}.tmp"

    with open(tmp, "w") as f:
        generate_project_list_fp(config=config, fp=f)

    os.rename(tmp, path)


def set_descriptions(config):
    """
    Set descriptions for gitweb use.
    """
    log = logging.getLogger("gitosis.gitweb.set_descriptions")

    repositories = util.get_repository_dir(config)

    for section in config.sections():
        parts = section.split(None, 1)
        type_ = parts.pop(0)
        if type_ != "repo":
            continue
        if not parts:
            continue

        try:
            description = config.get(section, "description")
        except (configparser.NoSectionError, configparser.NoOptionError):
            continue

        if not description:
            continue

        (name,) = parts

        if not os.path.exists(os.path.join(repositories, name)):
            namedotgit = f"{name}.git"
            if os.path.exists(os.path.join(repositories, namedotgit)):
                name = namedotgit
            else:
                log.warning(f"Cannot find {name!r} in {repositories!r}")
                continue

        path = os.path.join(
            repositories,
            name,
            "description",
        )
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w") as f:
            print(description, file=f)
        os.rename(tmp, path)
