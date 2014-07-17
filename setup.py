#!/usr/bin/env python
import os
import sys

from distutils.core import setup

from jinja2schema import __version__


if sys.argv[-1] in ('submit', 'publish'):
    os.system('python setup.py sdist upload')
    sys.exit()


setup(
    name='jinja2schema',
    version=__version__,
    description='Type inference for Jinja2 templates.',
    long_description=open('README.rst').read(),
    license=open('LICENSE').read(),
    author='Anton Romanovich',
    author_email='anthony.romanovich@gmail.com',
    url='https://jinja2schema.readthedocs.org',
    packages=['jinja2schema'],
    package_data={'': ['LICENSE']},
    include_package_data=True,
    install_requires=['Jinja2>=2.2'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: HTML'
    ],
)
