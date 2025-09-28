import configparser
import errno
import logging
import optparse
import os
import sys

log = logging.getLogger("gitosis.app")


class CannotReadConfigError(Exception):
    """Unable to read config file"""

    def __str__(self):
        return f"{self.__doc__}: {': '.join(self.args)}"


class ConfigFileDoesNotExistError(CannotReadConfigError):
    """Configuration does not exist"""


class App:
    name = None

    @classmethod
    def run(cls):
        app = cls()
        return app.main()

    def main(self):
        self.setup_basic_logging()
        parser = self.create_parser()
        (options, args) = parser.parse_args()
        cfg = configparser.RawConfigParser()
        try:
            self.read_config(options, cfg)
        except CannotReadConfigError as e:
            log.error(str(e))
            sys.exit(1)
        self.setup_logging(cfg)
        self.handle_args(parser, cfg, options, args)

    def setup_basic_logging(self):
        logging.basicConfig()

    def create_parser(self):
        parser = optparse.OptionParser()
        parser.set_defaults(
            config=os.path.expanduser("~/.gitosis.conf"),
        )
        parser.add_option(
            "--config",
            metavar="FILE",
            help="read config from FILE",
        )

        return parser

    def read_config(self, options, cfg):
        try:
            with open(options.config) as conffile:
                cfg.readfp(conffile)
        except OSError as e:
            if e.errno == errno.ENOENT:
                # special case this because gitosis-init wants to
                # ignore this particular error case
                raise ConfigFileDoesNotExistError() from e
            else:
                raise CannotReadConfigError() from e

    def setup_logging(self, cfg):
        try:
            loglevel = cfg.get("gitosis", "loglevel")
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
        else:
            try:
                symbolic = logging._levelNames[loglevel]
            except KeyError:
                log.warning(
                    "Ignored invalid loglevel configuration: %r",
                    loglevel,
                )
            else:
                logging.root.setLevel(symbolic)

    def handle_args(self, parser, cfg, options, args):  # noqa: ARG002
        if args:
            parser.error("not expecting arguments")
