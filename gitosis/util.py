import configparser
import os


def get_repository_dir(config: configparser.RawConfigParser) -> str:
    repositories = os.path.expanduser("~")
    try:
        path = config.get("gitosis", "repositories")
    except (configparser.NoSectionError, configparser.NoOptionError):
        return os.path.join(repositories, "repositories")
    return os.path.join(repositories, path)


def get_generated_files_dir(config: configparser.RawConfigParser) -> str:
    try:
        return config.get("gitosis", "generate-files-in")
    except (configparser.NoSectionError, configparser.NoOptionError):
        return os.path.expanduser("~/gitosis")


def get_ssh_authorized_keys_path(config: configparser.RawConfigParser) -> str:
    try:
        return config.get("gitosis", "ssh-authorized-keys-path")
    except (configparser.NoSectionError, configparser.NoOptionError):
        return os.path.expanduser("~/.ssh/authorized_keys")
