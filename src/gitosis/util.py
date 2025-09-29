from collections import abc
import configparser
import contextlib
import os
import secrets
import typing as t


@contextlib.contextmanager
def safe_open_write(path: str) -> abc.Iterator[t.IO]:
    tmp = f"{path}.{secrets.token_hex(16)}.tmp"
    with open(tmp, "w") as fp:
        yield fp
        os.fsync(fp)
    os.rename(tmp, path)


def write_file(path: str, contents: str) -> None:
    with safe_open_write(path) as fp:
        fp.write(contents)


def read_file(path: str) -> str:
    with open(path) as f:
        return f.read()


def get(cfg: configparser.ConfigParser, section: str, key: str, *, default=None):  # noqa: ANN001, ANN201
    try:
        return cfg.get(section, key)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return default


def get_boolean(cfg: configparser.ConfigParser, section: str, key: str, *, default: bool) -> bool:
    try:
        return cfg.getboolean(section, key)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return default


def get_repository_dir(config: configparser.ConfigParser) -> str:
    path = get(config, "gitosis", "repositories", default="repositories")
    return os.path.join(os.path.expanduser("~"), path)  # type: ignore


def get_generated_files_dir(config: configparser.ConfigParser) -> str:
    return get(config, "gitosis", "generate-files-in", default=os.path.expanduser("~/gitosis"))  # type: ignore


def get_ssh_authorized_keys_path(config: configparser.ConfigParser) -> str:
    return get(config, "gitosis", "ssh-authorized-keys-path", default=os.path.expanduser("~/.ssh/authorized_keys"))  # type: ignore
