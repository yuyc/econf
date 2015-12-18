
"""Easy to define config options and reference them."""

from __future__ import print_function

try:
    import configparser as ConfigParser  # py3
except ImportError:
    import ConfigParser  # py2
import logging
import optparse
import os.path
import sys
import warnings

__version__ = '0.1.4'

__all__ = ['CONF', 'BaseConf', 'UndefinedOption', 'UnsetOption',
           'BaseOpt', 'StrOpt', 'BoolOpt', 'IntOpt']

LOGGING_FORMAT = '%(asctime)s %(levelname)s %(name)s:%(funcName)s[%(lineno)d] %(message)s'  # NOQA

UNSET = str(object())


class UndefinedOption(Exception):
    """Raised if the option is not defined."""


class UnsetOption(Exception):
    """Raised if required option has no value."""


class BaseOpt(object):
    def __init__(self, name=None, default=UNSET, help=None, required=False, cmdline=False):
        self.name = name
        self.default = default
        self.help = help
        self.required = required
        self.cmdline = cmdline

    def __get__(self, instance, owner):
        convert = self.type()
        section = getattr(owner, "__section__", ConfigParser.DEFAULTSECT)
        return convert(CONF._get(self.name, section))

    def type(self):
        raise NotImplementedError()


class StrOpt(BaseOpt):
    def type(self):
        return str


class IntOpt(BaseOpt):
    def type(self):
        return int


class BoolOpt(BaseOpt):
    def type(self):
        def en_bool(obj):
            """Enhanced bool converter. Only certain strings stands
            for ``True`` .
            """
            if isinstance(obj, str):
                return obj in ('True', 'true', 'T', 't')
            return bool(obj)
        return en_bool


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

    def __init__(self):
        self._opt_parser = optparse.OptionParser()
        self._options = None
        self._config_parser = ConfigParser.ConfigParser()
        self._required = []
        self._opt_parser.add_option('-f', '--conf',
                                    dest='conf',
                                    help="Configuration file.")
        self._opt_parser.add_option('-v', "--version",
                                    action="version",
                                    help="show program's version number and exit")
        self._converters = {}

    def parse_cmdline(self, argv=None):
        """Parse cmdline args"""
        options, args = self._opt_parser.parse_args(argv)
        if args:
            sys.stderr.write('Unknown arguments: %s\n' % str(args))
            sys.exit(1)
        self._options = options

    def parse_conf_file(self, config_file):
        self._config_parser.read(config_file)

    def __call__(self, default_conf=None, check_required=False, argv=None):
        """Parse configuration files.

        Config files are chosen in below order:

        * parameter "config_file"
        * cli option: conf
        """

        self.parse_cmdline(argv)

        config_file = (self._options and self._options.conf) or default_conf

        if not config_file or not os.path.exists(config_file):
            warnings.warn('Config file not found: %s' % config_file)
        else:
            self.parse_conf_file(config_file)

        # TODO(wangst): maybe there are better way to check if all
        # required option has value.
        if check_required:
            for section, opt in self._required:
                assert self.get(opt, section=section), \
                    "[%s]%s is not config" % (section, opt)

    def define(self, option, section=None, type=str, default=UNSET,
               cmdline=False, required=False, help=None):
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

        assert callable(type)
        self._converters[(section, option)] = type

        # NOTE: config parser require value of string type
        self._config_parser.set(section, option, str(default))
        if required:
            self._required.append((section, option))

    def add_opt(self, opt, section=None):
        assert isinstance(opt, BaseOpt)
        self.define(opt.name, section=section, type=opt.type(),
                    default=opt.default, required=opt.required,
                    cmdline=opt.cmdline, help=opt.help)

    def _cmd_option(self, section, option):
        if section.upper() != ConfigParser.DEFAULTSECT:
            option = section.lower() + '_' + option
        return option

    def __getattr__(self, item):
        config, section = self, item

        class SubSection(object):
            def __getattr__(self, item):
                return config.get(item, section=section)

            def options(self):
                return config.options(section)

        if self._config_parser.has_section(section):
            return SubSection()
        return self.get(item)

    def get(self, option, section=None, **kwargs):
        section = section or ConfigParser.DEFAULTSECT
        convert = self._converters.get((section, option), str)
        val = self._get(option, section, **kwargs)
        return convert(val)

    def _get(self, option, section=None, **kwargs):
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
        value = self._options and getattr(self._options, cmd_option, None)
        if value is not None:
            return value

        try:
            value = self._config_parser.get(section, option)
            if value is not UNSET:
                return value
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            err_msg = 'Section: %s, option: %s' % (section, option)
            raise UndefinedOption(err_msg)

        if 'default' in kwargs:
            return kwargs['default']
        raise UnsetOption('Section: %s, option: %s' % (section, option))

    def options(self, section=None):
        if section is None or section == ConfigParser.DEFAULTSECT:
            return [item[0] for item in
                    self._config_parser.items(ConfigParser.DEFAULTSECT)]
        return [name for name in self._config_parser._sections[section]]

    def setup_logging(self, level=None, format=None):
        level = level or CONF.get('log_level', default='info')
        level = getattr(logging, str(level).upper(), 'INFO')
        format = format or LOGGING_FORMAT
        logging.basicConfig(level=level, format=format)

    def dump(self, logger=None):
        logger = logger or logging.getLogger()
        logger.info("Version: %s", self.version)
        logger.info("="*10 + " Configuration " + "="*10)
        config_parser = self._config_parser
        logger.info('[%s]', ConfigParser.DEFAULTSECT)
        for name in self.options():
            value = self.get(name)
            logger.info('%s = "%s"' % (name, value))
        for section in config_parser.sections():
            logger.info('[%s]', section)
            for name in self.options(section):
                value = self.get(name, section=section)
                logger.info('%s = "%s"' % (name, value))
        logger.info("="*34)

    @property
    def version(self):
        return self._opt_parser.version

    @version.setter
    def version(self, ver):
        self._opt_parser.version = ver


CONF = Config()


class ConfMeta(type):
    def __new__(meta_cls, cls, bases, attrs):
        section = attrs.get('__section__', ConfigParser.DEFAULTSECT)
        for name, val in attrs.items():
            if not isinstance(val, BaseOpt):
                continue
            if not val.name:
                val.name = name
            CONF.add_opt(opt=val, section=section)
        return type.__new__(meta_cls, cls, bases, attrs)


class BaseConf(metaclass=ConfMeta):
    """Base Conf that make defining options easy.

    For default options, that belong to 'default' section::

        class DefaultConf(BaseConf):
            host = StrOpt(default='0.0.0.0', cmdline=True,
                          help='ip address')
            port = IntOpt(default=9090, cmdline=True,
                          help='tcp port')

    For options belong to other section::

        class ZKConf(BaseConf):
            __section__ = 'zk'

            hosts = StrOpt(
                required=True,
                help='list of zookeeper ip:port pair. i.e. localhost:2181')
            max_retry = IntOpt(
                default=3,
                help='number of tries before giving up connecting')

    There are two ways to reference an option.
    First, use the specific Conf Class::

        host, port = DefaultConf.host, DefaultConf.port

    Second, use the general CONF::

        host, port = CONF.host, CONF.port

    """

    @classmethod
    def get(cls, opt, **kwargs):
        section = getattr(cls, '__section__', ConfigParser.DEFAULTSECT)
        return CONF.get(opt, section=section, **kwargs)

    @classmethod
    def options(cls):
        section = getattr(cls, '__section__', ConfigParser.DEFAULTSECT)
        return CONF.options(section)


class DefaultConf(BaseConf):
    log_level = StrOpt(default='info', cmdline=True,
                       help='level of the root logger')
    debug = BoolOpt(default=False, cmdline=True,
                    help='whether run in debug mode')


def test():
    class ZKConf(BaseConf):
        __section__ = 'zk'
        hosts = StrOpt(required=True, cmdline=True,
                       help="address of zookeeper hosts, i.e. localhost:2181")
        max_retry = IntOpt(default=3,
                           help="max number of try before give up connecting")
        keep_alive = BoolOpt(default=True,
                             help="the same as the default one, on purpose")
        user = StrOpt(default='', help='zookeeper user')

    class DefaultConf(BaseConf):
        host = StrOpt(default='0.0.0.0', cmdline=True,
                      help='ip address')
        port = IntOpt(default=9090, cmdline=True,
                      help='tcp port')
        keep_alive = BoolOpt(
            default=False,
            help='keep the connection alive when the request is over')

    # parse command line and config file
    CONF.version = '0.1'
    CONF('default.conf', check_required=True)
    CONF.setup_logging()
    CONF.dump()

    logging.debug('By default, this should not be seen.')
    logging.info('Nice to see you!')

    logging.info('default options: %s', CONF.options())
    logging.info('zk options: %s', CONF.zk.options())
    zk_options = {name: ZKConf.get(name) for name in ZKConf.options()}
    logging.info('zk options: %s', zk_options)

    logging.info('user: %s', ZKConf.user)
    logging.info('keep_alive: %s', ZKConf.get('keep_alive'))


if __name__ == '__main__':
    test()
