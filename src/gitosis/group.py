from collections import abc
import configparser
import logging

from gitosis import util

_log = logging.getLogger(__name__)

GROUP_PREFIX = "group "


def _get_membership(config: configparser.ConfigParser, user: str, seen: set[str]) -> abc.Iterator[str]:
    for section in config.sections():
        if not section.startswith(GROUP_PREFIX):
            continue
        group = section[len(GROUP_PREFIX) :]
        if group in seen:
            continue

        members = frozenset(util.get(config, section, "members", default="").split())  # type: ignore

        # @all is the only group where membership needs to be
        # bootstrapped like this, anything else gets started from the
        # username itself
        if user in members or "@all" in members:
            _log.debug("found %s in %s", user, group)
            seen.add(group)
            yield group

            yield from _get_membership(
                config,
                f"@{group}",
                seen,
            )


def get_membership(config: configparser.ConfigParser, user: str) -> abc.Iterator[str]:
    """Generate groups ``user`` is member of, according to ``config``."""
    seen: set[str] = set()
    yield from _get_membership(config, user, seen)
    # everyone is always a member of group "all"
    yield "all"
