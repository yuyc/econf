Introduction
==============

``econf`` make it easy to define config options and reference them.
The options can be provided through command line or config file.

Install
=========

::

    $ pip install http://github.com/wangst321/econf.git

How to Use
============

define options
----------------

First, import ``econf`` ::

    from econf import *

For default options, that belong to 'default' section::

    from econf import BaseConf

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

use options in your code
--------------------------

There are two ways to reference an option.
First, use the specific Conf Class::

    host, port = DefaultConf.host, DefaultConf.port

Second, use the general CONF::

    host, port = CONF.host, CONF.port
    zk_hosts = CONF.zk.hosts

parse cli options and config file
-----------------------------------

.. note::

    When the code executes, this step should always be in front of those
    statements, which reference options.

If a default config is supplied::

    from econf import CONF
    CONF('path/to/your/default.conf')

or,  ::

    from econf import CONF
    CONF()

Usually, this code is executed just before your service gonna start. ::

    def run():
        from econf import CONF
        CONF()

        my_service.init(CONF.host, CONF.port, ...)
        my_service.start()

