#!/usr/bin/env python
import os
import sys

from distutils.core import setup

from jinja2schema import __version__


if sys.argv[-1] in ("submit", "publish"):
    os.system("python setup.py sdist upload")
    sys.exit()


setup(
    name="jinja2schema",
    version=__version__,
    description="Type inference for Jinja2 templates.",
    long_description=open('README.rst').read(),
    license=open('LICENSE').read(),
    author="Anton Romanovich",
    author_email="anthony.romanovich@gmail.com",
    url="https://jinja2schema.readthedocs.org",
    packages=['jinja2schema'],
    package_data={'': ['LICENSE']},
    include_package_data=True,
    install_requires=['Jinja2>=2.2'],
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Topic :: Software Development :: Libraries' ,
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Development Status :: 4 - Beta',
    ],
)
