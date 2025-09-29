import configparser
import logging
import os
import typing as t

from gitosis import group

_log = logging.getLogger(__name__)


def have_access(config: configparser.ConfigParser, user: str, mode: str, path: str) -> t.Optional[tuple[str, str]]:
    """Map request for write access to allowed path.

    Note for read-only access, the caller should check for write
    access too.

    Returns ``None`` for no access, or a tuple of toplevel directory
    containing repositories and a relative path to the physical repository.
    """
    _log.debug("Access check for %s as %s on %s...", user, mode, path)

    basename, ext = os.path.splitext(path)
    if ext == ".git":
        _log.debug("Stripping .git suffix from '%s', new value '%s'", path, basename)
        path = basename

    for groupname in group.get_membership(config=config, user=user):
        try:
            repos = config.get(f"group {groupname}", mode).split()
        except (configparser.NoSectionError, configparser.NoOptionError):
            repos = []

        mapping = None

        if path in repos:
            _log.debug("Access OK for %s as %s on %s", user, mode, path)
            mapping = path
        else:
            try:
                mapping = config.get(f"group {groupname}", f"map {mode} {path}")
            except (configparser.NoSectionError, configparser.NoOptionError):
                pass
            else:
                _log.debug("Access OK for %s as %s on %s=%s", user, mode, path, mapping)

        if mapping is not None:
            prefix = None
            try:
                prefix = config.get(f"group {groupname}", "repositories")
            except (configparser.NoSectionError, configparser.NoOptionError):
                try:
                    prefix = config.get("gitosis", "repositories")
                except (configparser.NoSectionError, configparser.NoOptionError):
                    prefix = "repositories"

            _log.debug("Using prefix %s for %s", prefix, mapping)
            return (prefix, mapping)

    return None
