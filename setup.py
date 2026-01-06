#!/usr/bin/env python
import os
import re
from os import path
from setuptools import setup

MYDIR = path.abspath(os.path.dirname(__file__))
long_description = open(os.path.join(MYDIR, 'README.md')).read()

with open(path.join(MYDIR, 'floe', 'version.py')) as f:
    version = re.search(r"__version__ = ['\"]([^'\"]+)['\"]", f.read()).group(1)

setup(
    name='floe',
    version=version,
    description='Floe',
    author='John Loehrer',
    author_email='john@happybits.co',
    url='https://github.com/happybits/floe',
    packages=['floe'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Environment :: Web Environment',
        'Operating System :: POSIX',
    ],
    license='MIT',
    python_requires='>=3.10',
    install_requires=[
        'falcon>=3.0.0,<5.0.0',
        'requests',
        'opentelemetry-api',
    ],
    include_package_data=True,
    long_description=long_description,
    cmdclass={},
    ext_modules=[]
)
