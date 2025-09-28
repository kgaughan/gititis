import configparser
import logging
import os

from gitosis import group


def have_access(config, user, mode, path):
    """
    Map request for write access to allowed path.

    Note for read-only access, the caller should check for write
    access too.

    Returns ``None`` for no access, or a tuple of toplevel directory
    containing repositories and a relative path to the physical repository.
    """
    log = logging.getLogger("gitosis.access.haveAccess")

    log.debug(f"Access check for {user!r} as {mode!r} on {path!r}...")

    basename, ext = os.path.splitext(path)
    if ext == ".git":
        log.debug(f"Stripping .git suffix from {path!r}, new value {basename!r}")
        path = basename

    for groupname in group.get_membership(config=config, user=user):
        try:
            repos = config.get(f"group {groupname}", mode)
        except (configparser.NoSectionError, configparser.NoOptionError):
            repos = []
        else:
            repos = repos.split()

        mapping = None

        if path in repos:
            log.debug(f"Access ok for {user!r} as {mode!r} on {path!r}")
            mapping = path
        else:
            try:
                mapping = config.get(f"group {groupname}", f"map {mode} {path}")
            except (configparser.NoSectionError, configparser.NoOptionError):
                pass
            else:
                log.debug(f"Access ok for {user!r} as {mode!r} on {path!r}={mapping!r}")

        if mapping is not None:
            prefix = None
            try:
                prefix = config.get(f"group {groupname}", "repositories")
            except (configparser.NoSectionError, configparser.NoOptionError):
                try:
                    prefix = config.get("gitosis", "repositories")
                except (configparser.NoSectionError, configparser.NoOptionError):
                    prefix = "repositories"

            log.debug(f"Using prefix {prefix!r} for {mapping!r}")
            return (prefix, mapping)
