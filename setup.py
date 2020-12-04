#!/usr/bin/env python
import os
from os import path
from setuptools import setup
import imp

MYDIR = path.abspath(os.path.dirname(__file__))
long_description = open(os.path.join(MYDIR, 'README.md')).read()

version = imp.load_source('version',
                          path.join('.', 'floe', 'version.py')).__version__

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
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Environment :: Web Environment',
        'Operating System :: POSIX',
    ],
    license='MIT',
    install_requires=[
        'falcon>=0.3.0',
        'requests',
    ],
    include_package_data=True,
    long_description=long_description,
    cmdclass={},
    ext_modules=[]
)
