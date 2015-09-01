"""Define configurations for api server"""
from __future__ import print_function

try:
    import configparser as ConfigParser  # py3
except ImportError:
    import ConfigParser  # py2
import optparse
import os.path
import sys
import warnings


__all__ = ['CONF', 'UndefinedOption', 'UnsetOption']


class UndefinedOption(Exception):
    """Raised if the option is not defined."""


class UnsetOption(Exception):
    """Raised if required option has no value."""


class Config(object):
    """Use Config to parse cmdline options and config files.

    How to use it:

    * define an option in your module file::

        CONF.define('option_name', default='default_value',
                    required=True  # if this option has to be provided by user
                    cmdline=True  # if it can be provided through command line
                    help='description of this option')

    make sure this statement is executed when your module file imported.

    * use the option in your module file::

        CONF.get('option_name')
        or,
        CONF.get('option_name', 'not_default_section')

    * parse config file in your startup py::

        CONF.parse_conf_file()

    which will parse the command line first, then the config file.

    # TODO(wangst): option type can be set when define an option.
    """
    LOGGING_FORMAT = '%(asctime)s %(levelname)s %(name)s:%(funcName)s[%(lineno)d] %(message)s'  # NOQA

    def __init__(self):
        self._opt_parser = optparse.OptionParser()
        self._options = None
        self._config_parser = ConfigParser.ConfigParser()
        self._required = []
        self._opt_parser.add_option('-f', '--conf',
                                    dest='conf',
                                    help="Configuration file.")

    def parse_cmdline(self, argv=None):
        """Parse cmdline args"""
        options, args = self._opt_parser.parse_args(argv)

        if args:
            sys.stderr.write('Unknown arguments: %s\n' % str(args))
            sys.exit(1)
        self._options = options

    def parse_conf_file(self, config_file):
        self._config_parser.read(config_file)

    def __call__(self, config_file=None, check_required=False):
        """Parse configuration files.

        Config files are chosen in below order:

        * parameter "config_file"
        * cli option: conf
        """

        self.parse_cmdline()

        config_file = config_file or (self._options and self._options.conf)

        if not config_file or not os.path.exists(config_file):
            warnings.warn('Config file not found: %s' % config_file)
        else:
            self.parse_conf_file()

        # TODO(wangst): maybe there are better way to check if all
        # required option has value.
        if check_required:
            for section, opt in self._required:
                assert self.get(opt, section=section), \
                    "[%s]%s is not config" % (section, opt)

    def define(self, option, section=None, type_=str, default=None, cmdline=False,
               required=False, help=None):
        """Define a option.

        :arg str option: name of the option, which should not start with '-'
                         and use '_' to combine words.
        :param section: which section this option belongs to
        :param default: the default value for this option
        :param cmdline: whether this option can be provided through
                        command line
        :param required: True if the option is required, which means exception
                        will be raised when no value for the option.
        :param help: help message
        """
        section = section or ConfigParser.DEFAULTSECT
        assert isinstance(section, str) and isinstance(option, str)
        if cmdline:
            cmd_option = self._cmd_option(section, option)
            self._opt_parser.add_option('--' + cmd_option.replace('_', '-'),
                                        dest=cmd_option,
                                        help=help)
        try:
            self._config_parser.add_section(section)
        except (ConfigParser.DuplicateSectionError, ValueError):
            pass

        self._config_parser.set(section, option, str(default or ''))
        if required:
            self._required.append((section, option))

    def _cmd_option(self, section, option):
        if section.upper() != ConfigParser.DEFAULTSECT:
            option = section.lower() + '_' + option
        return option

    def get(self, option, section=None, **kwargs):
        """Return the value of the option.

        :arg str option: name of the option.
        :param str section: which section this option belongs to. The
            DEFAULT_SECTION will be used if not provided.

        The order of the option value:
        1.If the option is a cmdline option and is provided in sys.argv,
        the cmdline value will be used.
        2.If the option is set in config file, the value will used.
        3.If default value exist, the default will be used.

        Exception will be raised if nothing found.
        """
        section = section or ConfigParser.DEFAULTSECT
        cmd_option = self._cmd_option(section, option)
        value = getattr(self._options, cmd_option, None)
        if value:
            return value

        try:
            value = self._config_parser.get(section, option)
            if value:
                return value
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            err_msg = 'Section: %s, option: %s' % (section, option)
            raise UndefinedOption(err_msg)

        if 'default' in kwargs:
            return kwargs['default']
        raise UnsetOption('Section: %s, option: %s' % (section, option))


CONF = Config()


if __name__ == '__main__':
    CONF.define('address', section='zk', cmdline=True,
                required=True, help="the ip address of the zookeeper server")
    CONF.define('port', section='zk', cmdline=True,
                help="the ip address of the zookeeper server")
    CONF.define('host', cmdline=True, default='0.0.0.0',
                help='the ip address on which the api server will listen')
    CONF.define('port', cmdline=True, default='9090',
                help='the port on which the api server will listen')
    CONF()
    print('zookeeper address: %s, port: %s' % (
        CONF.get('address', section='zk'),
        CONF.get('port', section='zk', default=9999)))
    print('bind_address:', (CONF.get('host'), CONF.get('port')))
