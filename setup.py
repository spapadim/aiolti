#!/usr/bin/env python
# Copyright 2009-2014 MIT ODL Engineering
#           2020 Spiros Papadimitriou
#
# This file is part of PyLTI/aioLTI.
#

from __future__ import print_function

import os
import sys

if sys.version_info < (3, 8):
    error = "ERROR: aioLTI requires Python 3.8+ ... exiting."
    print(error, file=sys.stderr)
    sys.exit(1)

try:
    from setuptools import setup, find_packages
    from setuptools.command.test import test as testcommand

    class PyTest(testcommand):
        user_options = testcommand.user_options[:]
        user_options += [
            ('coverage', 'C', 'Produce a coverage report for aioLTI'),
            ('pep8', 'P', 'Produce a pep8 report for aioLTI'),
            ('flakes', 'F', 'Produce a flakes report for aioLTI'),

        ]
        coverage = None
        pep8 = None
        flakes = None
        test_suite = False
        test_args = []

        def initialize_options(self):
            testcommand.initialize_options(self)

        def finalize_options(self):
            testcommand.finalize_options(self)
            self.test_suite = True
            self.test_args = []
            if self.coverage:
                self.test_args.append('--cov')
                self.test_args.append('aiolti')
            if self.pep8:
                self.test_args.append('--pep8')
            if self.flakes:
                self.test_args.append('--flakes')

        def run_tests(self):
            # import here, cause outside the eggs aren't loaded
            import pytest
            errno = pytest.main(self.test_args)
            sys.exit(errno)

    extra = dict(test_suite="aiolti.tests",
                 tests_require=["pytest-cov>=2.3.0", "pytest-pep8>=1.0.6",
                                "pytest-flakes>=1.0.1", "pytest>=2.9.2",
                                "httpretty>=0.8.3", "quart>=0.13.0",
                                "oauthlib>=0.6.3", "semantic_version>=2.3.1",
                                "mock==1.0.1"],
                 cmdclass={"test": PyTest},
                 install_requires=["oauth2>=1.9.0.post1", "httplib2>=0.9", "six>=1.10.0"],
                 include_package_data=True,
                 zip_safe=False)
except ImportError as err:
    import string
    from distutils.core import setup

    def convert_path(pathname):
        """
        Local copy of setuptools.convert_path used by find_packages (only used
        with distutils which is missing the find_packages feature)
        """
        if os.sep == '/':
            return pathname
        if not pathname:
            return pathname
        if pathname[0] == '/':
            raise ValueError("path '%s' cannot be absolute" % pathname)
        if pathname[-1] == '/':
            raise ValueError("path '%s' cannot end with '/'" % pathname)
        paths = string.split(pathname, '/')
        while '.' in paths:
            paths.remove('.')
        if not paths:
            return os.curdir
        return os.path.join(*paths)

    def find_packages(where='.', exclude=()):
        """
        Local copy of setuptools.find_packages (only used with distutils which
        is missing the find_packages feature)
        """
        out = []
        stack = [(convert_path(where), '')]
        while stack:
            where, prefix = stack.pop(0)
            for name in os.listdir(where):
                fn = os.path.join(where, name)
                isdir = os.path.isdir(fn)
                has_init = os.path.isfile(os.path.join(fn, '__init__.py'))
                if '.' not in name and isdir and has_init:
                    out.append(prefix + name)
                    stack.append((fn, prefix + name + '.'))
        for pat in list(exclude) + ['ez_setup', 'distribute_setup']:
            from fnmatch import fnmatchcase

            out = [item for item in out if not fnmatchcase(item, pat)]
        return out

    print("Non-Fatal Error:", err, "\n")
    print("Setup encountered an error while importing setuptools (see above).")
    print("Proceeding anyway with manual replacements for setuptools.find_packages.")
    print("Try installing setuptools if you continue to have problems.\n\n")

    extra = dict()

VERSION = __import__('aiolti').__version__

README = open('README.rst').read()

setup(
    name='aioLTI',
    version=VERSION,
    packages=find_packages(),
    package_data={'aiolti.templates': ['web/*.*', 'web/css/*', 'web/js/*']},
    license='BSD',
    author='MIT ODL Engineering',
    author_email='spapadim@gmail.com',
    url="http://github.com/spapadim/aiolti",
    description="Fork of PyLTI by MITODL modified for asyncio",
    long_description=README,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
    ],
    **extra
)
