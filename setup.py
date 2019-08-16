#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

from setuptools import setup, find_packages

version = u'0.1'

setup(
    name=u'ckanext-query-dois',
    version=version,
    description=u'Query DOIs',
    long_description=u'Allows the creation of DOIs for queries on resources',
    classifiers=[],
    keywords=u'',
    author=[u'Josh Humphries'],
    author_email=u'data@nhm.ac.uk',
    url=u'https://github.com/NaturalHistoryMuseum/ckanext-query-dois',
    license=u'',
    packages=find_packages(exclude=[u'ez_setup', u'list', u'tests']),
    namespace_packages=[u'ckanext', u'ckanext.query_dois'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        u'datacite==1.0.1',
        u'bcrypt==3.1.4',
    ],
    entry_points= \
        u'''
        [ckan.plugins]
        query_dois=ckanext.query_dois.plugin:QueryDOIsPlugin
        [paste.paster_command]
        initdb=ckanext.query_dois.commands:QueryDOIsInitDBCommand
        ''',
)
