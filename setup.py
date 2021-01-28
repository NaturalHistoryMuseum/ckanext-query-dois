#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

from setuptools import find_packages, setup

__version__ = u'1.0.1'

with open(u'README.md', u'r') as f:
    __long_description__ = f.read()

setup(
    name=u'ckanext-query-dois',
    version=__version__,
    description=u'A CKAN extension that creates DOIs for queries on resources.',
    long_description=__long_description__,
    classifiers=[
        u'Development Status :: 3 - Alpha',
        u'Framework :: Flask',
        u'Programming Language :: Python :: 2.7'
    ],
    keywords=u'CKAN data query-dois',
    author=u'Natural History Museum',
    author_email=u'data@nhm.ac.uk',
    url=u'https://github.com/NaturalHistoryMuseum/ckanext-query-dois',
    license=u'GNU GPLv3',
    packages=find_packages(exclude=[u'tests']),
    namespace_packages=[u'ckanext', u'ckanext.query_dois'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # required by datacite (well jsonschema) but must be at this version to work on python2
        'pyrsistent==0.16.1',
        'datacite==1.0.1',
        'bcrypt==3.1.4',
        'dicthash==0.0.2',
        u'contextlib2>=0.6.0.post1',
    ],
    entry_points= \
        u'''
        [ckan.plugins]
            query_dois=ckanext.query_dois.plugin:QueryDOIsPlugin
        ''',
    )
