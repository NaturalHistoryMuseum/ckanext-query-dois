import json

from sqlalchemy import Column, UnicodeText, DateTime, Table, BigInteger, types

from ckan.model import meta, DomainObject


class JsonType(types.UserDefinedType):
    '''
    A JSONB column type for PostgreSQL databases. This should be removed and replaced by an
    sqlalchemy core implementation when one becomes available in newer versions of CKAN.
    '''

    def get_col_spec(self):
        return u'jsonb'

    def is_mutable(self):
        return True

    def python_type(self):
        return dict

    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                return json.dumps(value)
            else:
                return None
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            else:
                return json.loads(value)

        return process


query_doi_table = Table(
    u'query_doi',
    meta.metadata,
    Column(u'id', BigInteger, primary_key=True),
    # the full doi (prefix/suffix)
    Column(u'doi', UnicodeText, nullable=False, index=True, unique=True),
    # json column representing the resources in this query and their rounded versions, it is a
    # straight map from resource_id: version
    Column(u'resources_and_versions', JsonType, nullable=False),
    # the timestamp when the doi was created
    Column(u'timestamp', DateTime, nullable=False),
    # the query dict that produces the data for this doi
    Column(u'query', JsonType, nullable=False),
    # the hash for the query that produces the data for this doi - this is used in conjunction with
    # the version to check if the query has been run before
    Column(u'query_hash', UnicodeText, nullable=False, index=True),
    # the version initially requested by the user
    Column(u'requested_version', BigInteger, nullable=False),
    # record count at time of minting
    Column(u'count', BigInteger, nullable=False),
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
        return QueryDOI.resources_and_versions.op(u'->>')(resource_id) != None


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
