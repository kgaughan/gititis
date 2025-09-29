import configparser
import errno
import logging
import optparse
import os
import sys

log = logging.getLogger(__name__)

_level_names = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


class CannotReadConfigError(Exception):
    """Unable to read config file."""

    def __str__(self) -> str:
        return f"{self.__doc__}: {': '.join(self.args)}"


class ConfigFileDoesNotExistError(CannotReadConfigError):
    """Configuration does not exist."""


class App:
    name = None

    @classmethod
    def run(cls) -> None:
        cls().main()

    def main(self) -> None:
        self.setup_basic_logging()
        parser = self.create_parser()
        options, args = parser.parse_args()
        cfg = configparser.ConfigParser(interpolation=None)
        try:
            self.read_config(options, cfg)
        except CannotReadConfigError as e:
            log.error(str(e))  # noqa: TRY400
            sys.exit(1)
        self.setup_logging(cfg)
        self.handle_args(parser, cfg, options, args)

    def setup_basic_logging(self) -> None:
        logging.basicConfig()

    def create_parser(self) -> optparse.OptionParser:
        parser = optparse.OptionParser()
        parser.set_defaults(config=os.path.expanduser("~/.gitosis.conf"))
        parser.add_option(
            "--config",
            metavar="FILE",
            help="read config from FILE",
        )
        return parser

    def read_config(self, options: optparse.Values, cfg: configparser.ConfigParser) -> None:
        try:
            cfg.read(options.config)
        except OSError as e:
            if e.errno == errno.ENOENT:
                # special case this because gitosis-init wants to
                # ignore this particular error case
                raise ConfigFileDoesNotExistError from e
            raise CannotReadConfigError from e

    def setup_logging(self, cfg: configparser.ConfigParser) -> None:
        try:
            log_level = _level_names.get(cfg.get("gitosis", "loglevel"), logging.INFO)
        except (configparser.NoSectionError, configparser.NoOptionError):
            log_level = logging.INFO
        logging.root.setLevel(log_level)

    def handle_args(
        self,
        parser: optparse.OptionParser,
        cfg: configparser.ConfigParser,  # noqa: ARG002
        options: optparse.Values,  # noqa: ARG002
        args: list[str],
    ) -> None:
        if args:
            parser.error("not expecting arguments")
