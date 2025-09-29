import configparser
import errno
import logging
import os

from gitosis import util

log = logging.getLogger(__name__)


def export_ok_path(repopath: str) -> str:
    return os.path.join(repopath, "git-daemon-export-ok")


def allow_export(repopath: str) -> None:
    open(export_ok_path(repopath), "a").close()


def deny_export(repopath: str) -> None:
    p = export_ok_path(repopath)
    try:
        os.unlink(p)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise


def _extract_reldir(topdir: str, dirpath: str) -> str:
    if topdir == dirpath:
        return os.path.curdir
    prefix = topdir + os.path.sep
    return dirpath[len(prefix) :]


def set_export_ok(config: configparser.ConfigParser) -> None:
    repositories = util.get_repository_dir(config)

    global_enable = util.get_boolean(config, "gitosis", "daemon", default=False)
    log.debug("Global default is %s", "allow" if global_enable else "deny")

    def _error(e: OSError) -> None:
        if e.errno != errno.ENOENT:
            raise e

    for dirpath, dirnames, _ in os.walk(repositories, onerror=_error):
        # oh how many times i have wished for os.walk to report
        # topdir and reldir separately, instead of dirpath
        reldir = _extract_reldir(topdir=repositories, dirpath=dirpath)

        log.debug("Walking %s, seeing %r", reldir, dirnames)

        to_recurse = []
        repos = []
        for dirname in dirnames:
            if dirname.endswith(".git"):
                repos.append(dirname)
            else:
                to_recurse.append(dirname)
        dirnames[:] = to_recurse

        for repo in repos:
            name, _ = os.path.splitext(repo)
            if reldir != os.path.curdir:
                name = os.path.join(reldir, name)

            if util.get_boolean(config, f"repo {name}", "daemon", default=global_enable):
                log.debug("Allow %s", name)
                allow_export(os.path.join(dirpath, repo))
            else:
                log.debug("Deny %s", name)
                deny_export(os.path.join(dirpath, repo))
