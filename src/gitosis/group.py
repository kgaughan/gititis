import configparser
import logging

GROUP_PREFIX = "group "


def _get_membership(config, user, seen):
    log = logging.getLogger("gitosis.group.getMembership")

    for section in config.sections():
        if not section.startswith(GROUP_PREFIX):
            continue
        group = section[len(GROUP_PREFIX) :]
        if group in seen:
            continue

        try:
            members = config.get(section, "members")
        except (configparser.NoSectionError, configparser.NoOptionError):
            members = []
        else:
            members = members.split()

        # @all is the only group where membership needs to be
        # bootstrapped like this, anything else gets started from the
        # username itself
        if user in members or "@all" in members:
            log.debug(f"found {user!r} in {group!r}")
            seen.add(group)
            yield group

            yield from _get_membership(
                config,
                f"@{group}",
                seen,
            )


def get_membership(config, user):
    """
    Generate groups ``user`` is member of, according to ``config``

    :type config: RawConfigParser
    :type user: str
    :param _seen: internal use only
    """

    seen = set()
    yield from _get_membership(config, user, seen)

    # everyone is always a member of group "all"
    yield "all"
