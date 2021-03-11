#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

from setuptools import find_packages, setup

__version__ = '2.0.2'

with open('README.md', 'r') as f:
    __long_description__ = f.read()

setup(
    name='ckanext-query-dois',
    version=__version__,
    description='A CKAN extension that creates DOIs for queries on resources.',
    long_description=__long_description__,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    keywords='CKAN data query-dois',
    author='Natural History Museum',
    author_email='data@nhm.ac.uk',
    url='https://github.com/NaturalHistoryMuseum/ckanext-query-dois',
    license='GNU GPLv3',
    packages=find_packages(exclude=['tests']),
    namespace_packages=['ckanext', 'ckanext.query_dois'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'datacite==1.0.1',
        'bcrypt==3.1.4',
        'dicthash==0.0.2',
    ],
    entry_points= \
        '''
        [ckan.plugins]
            query_dois=ckanext.query_dois.plugin:QueryDOIsPlugin
        ''',
    )
