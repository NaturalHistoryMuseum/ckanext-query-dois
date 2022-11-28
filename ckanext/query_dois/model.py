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
    'query_doi',
    meta.metadata,
    Column('id', BigInteger, primary_key=True),
    # the full doi (prefix/suffix)
    Column('doi', UnicodeText, nullable=False, index=True, unique=True),
    # json column representing the resources in this query and their rounded versions, it is a
    # straight map from resource_id: version
    Column('resources_and_versions', JSONB, nullable=False),
    # the timestamp when the doi was created
    Column('timestamp', DateTime, nullable=False),
    # the query dict that produces the data for this doi
    Column('query', JSONB, nullable=False),
    # the hash for the query that produces the data for this doi - this is used in conjunction with
    # the version to check if the query has been run before
    Column('query_hash', UnicodeText, nullable=False, index=True),
    # the version initially requested by the user
    Column('requested_version', BigInteger, nullable=True),
    # record count at time of minting
    Column('count', BigInteger, nullable=False),
    # record the query version
    Column('query_version', UnicodeText, nullable=True),
    # record the resource counts
    Column('resource_counts', JSONB, nullable=True),
)


query_doi_stat_table = Table(
    'query_doi_stat',
    meta.metadata,
    Column('id', BigInteger, primary_key=True),
    # the doi this stat relates to
    Column('doi', UnicodeText, nullable=False, index=True),
    # record the action that produced this stat entry (for example, search or download)
    Column('action', UnicodeText),
    # the domain from the email address of the user using the doi
    Column('domain', UnicodeText),
    # the encrypted identifier from the email address of the user using the doi
    Column('identifier', UnicodeText),
    # timestamp of the stat
    Column('timestamp', DateTime, nullable=False),
)


class QueryDOI(DomainObject):
    """
    Object for holding query DOIs.
    """

    def get_resource_ids(self):
        return list(self.resources_and_versions.keys())

    def get_rounded_versions(self):
        return list(self.resources_and_versions.values())

    @staticmethod
    def on_resource(resource_id):
        """
        A convenience method to filter by a specific resource id.

        :param resource_id: the resource id
        :return: an sqlalchemy boolean expression
        """
        return QueryDOI.resources_and_versions.has_key(resource_id)


class QueryDOIStat(DomainObject):
    """
    Object for holding query DOIs stats.
    """

    def to_dict(self):
        """
        Returns the object as a dict for the stats API response.

        :return: a dict
        """
        return {
            'id': self.id,
            'doi': self.doi,
            'action': self.action,
            'domain': self.domain,
            'identifier': self.identifier,
            'timestamp': unicode(self.timestamp),
        }


meta.mapper(QueryDOI, query_doi_table)
meta.mapper(QueryDOIStat, query_doi_stat_table)
