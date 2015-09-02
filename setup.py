#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()


from econf import __version__

setup(
    name='econf',
    version=__version__,
    description="easy to define and reference config options",
    long_description=readme,
    author="WangST",
    author_email='shaotian.wang@ele.me',
    url='http://github.com/wangst321/econf.git',
    packages=['econf'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
)
