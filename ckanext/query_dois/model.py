#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import json

from sqlalchemy import Column, UnicodeText, DateTime, Table, BigInteger, types

from ckan.model import meta, DomainObject
from sqlalchemy.dialects.postgresql import JSONB


query_doi_table = Table(
    u'query_doi',
    meta.metadata,
    Column(u'id', BigInteger, primary_key=True),
    # the full doi (prefix/suffix)
    Column(u'doi', UnicodeText, nullable=False, index=True, unique=True),
    # json column representing the resources in this query and their rounded versions, it is a
    # straight map from resource_id: version
    Column(u'resources_and_versions', JSONB, nullable=False),
    # the timestamp when the doi was created
    Column(u'timestamp', DateTime, nullable=False),
    # the query dict that produces the data for this doi
    Column(u'query', JSONB, nullable=False),
    # the hash for the query that produces the data for this doi - this is used in conjunction with
    # the version to check if the query has been run before
    Column(u'query_hash', UnicodeText, nullable=False, index=True),
    # the version initially requested by the user
    Column(u'requested_version', BigInteger, nullable=True),
    # record count at time of minting
    Column(u'count', BigInteger, nullable=False),
    # record the query version
    Column(u'query_version', UnicodeText, nullable=True),
    # record the resource counts
    Column(u'resource_counts', JSONB, nullable=True),
)


query_doi_stat_table = Table(
    u'query_doi_stat',
    meta.metadata,
    Column(u'id', BigInteger, primary_key=True),
    # the doi this stat relates to
    Column(u'doi', UnicodeText, nullable=False, index=True),
    # record the action that produced this stat entry (for example, search or download)
    Column(u'action', UnicodeText),
    # the domain from the email address of the user using the doi
    Column(u'domain', UnicodeText),
    # the encrypted identifier from the email address of the user using the doi
    Column(u'identifier', UnicodeText),
    # timestamp of the stat
    Column(u'timestamp', DateTime, nullable=False),
)


class QueryDOI(DomainObject):
    '''
    Object for holding query DOIs.
    '''

    def get_resource_ids(self):
        return list(self.resources_and_versions.keys())

    def get_rounded_versions(self):
        return list(self.resources_and_versions.values())

    @staticmethod
    def on_resource(resource_id):
        '''
        A convenience method to filter by a specific resource id.

        :param resource_id: the resource id
        :return: an sqlalchemy boolean expression
        '''
        return QueryDOI.resources_and_versions.has_key(resource_id)


class QueryDOIStat(DomainObject):
    '''
    Object for holding query DOIs stats.
    '''

    def to_dict(self):
        '''
        Returns the object as a dict for the stats API response.

        :return: a dict
        '''
        return {
            u'id': self.id,
            u'doi': self.doi,
            u'action': self.action,
            u'domain': self.domain,
            u'identifier': self.identifier,
            u'timestamp': unicode(self.timestamp),
        }


meta.mapper(QueryDOI, query_doi_table)
meta.mapper(QueryDOIStat, query_doi_stat_table)
