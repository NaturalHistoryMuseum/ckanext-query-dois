import bisect
import copy
import hashlib
import json
import time
from collections import defaultdict

from sqlalchemy import Column, UnicodeText, DateTime, Table, BigInteger, types

from ckan.model import meta, DomainObject
from ckan.plugins import toolkit


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


class DatastoreQuery(object):
    '''
    Not a database table! This just models datastore queries passed to datastore_search, not the
    DOIs created from them. Perhaps it should live in lib, but it is modelling things so here makes
    some sense.
    '''

    @staticmethod
    def _parse_from_query_dict(query_dict):
        '''
        Parse a dict of query string parameters which represents the data dict for the
        datastore_search action in the URL format used by CKAN. The query_dict parameter is expected
        to look something like this (for example):

            {
                "q": "banana",
                "filters": "colour:yellow|length:200|colour:brown|type:tasty",
                etc
            }

        If a version is present, either as the version parameter or as the __version__ filter, it
        is extracted with preference given to the version parameter if both are provided.

        :param query_dict: the query string dict
        :return: the query dict (defaults to {} if nothing can be extracted from the query_dict) and
                 the requested version (defaults to None, if not provided in the query_dict)
        '''
        query = {}
        requested_version = None
        for param, param_value in query_dict.items():
            if param == u'version':
                requested_version = int(param_value)
            elif param == u'filters':
                filters = defaultdict(list)
                for filter_pair in param_value.split(u'|'):
                    filter_field, filter_value = filter_pair.split(u':', 1)
                    filters[filter_field].append(filter_value)
                if requested_version is None:
                    popped_version = filters.pop(u'__version__', None)
                    if popped_version:
                        requested_version = int(popped_version[0])
                if filters:
                    query[param] = filters
            else:
                query[param] = param_value
        return query, requested_version

    @staticmethod
    def _parse_from_data_dict(data_dict):
        '''
        Parse a dict of query string parameters which represents the data dict for the
        datastore_search action in data dict form it expects. The data_dict parameter is expected to
        look something like this (for example):

            {
                "q": "banana",
                "filters": {
                    "colour": ["yellow", "brown"],
                    "length": "200",
                    "type": ["tasty"],
                }
                etc
            }

        If a version is present, either as the version parameter or as the __version__ filter, it
        is extracted with preference given to the version parameter if both are provided.

        :param data_dict: the query string dict
        :return: the query dict (defaults to {} if nothing can be extracted from the query_dict) and
                 the requested version (defaults to None, if not provided in the query_dict)
        '''
        query = {}
        requested_version = None
        for param, param_value in data_dict.items():
            if param == u'version':
                requested_version = int(param_value)
            elif param == u'filters':
                filters = {}
                for filter_field, filter_value in param_value.items():
                    if not isinstance(filter_value, list):
                        filter_value = [filter_value]
                    filters[filter_field] = filter_value
                if requested_version is None:
                    popped_version = filters.pop(u'__version__', None)
                    if popped_version:
                        requested_version = int(popped_version[0])
                if filters:
                    query[param] = filters
            else:
                query[param] = param_value
        return query, requested_version

    def __init__(self, query_dict=None, data_dict=None):
        '''
        Provide one of the 3 parameters depending on the format you have the query in.

        :param query_dict: a dict of query string parameters in the CKAN URL format - i.e. the
                           filters are split with colons and pipes etc
        :param data_dict: a dict of data dict parameters - i.e. the typical action data_dict format
        '''
        if query_dict is not None:
            self.query, self.requested_version = self._parse_from_query_dict(query_dict)
        elif data_dict is not None:
            self.query, self.requested_version = self._parse_from_data_dict(data_dict)
        else:
            self.query = {}
            self.requested_version = None

        if self.requested_version is None:
            # default the requested time to now
            self.requested_version = int(time.time() * 1000)
        self.query_hash = self._generate_query_hash()

    def _generate_query_hash(self):
        '''
        Create a unique hash for this query. To do this we have to ensure that the features like the
        order of filters is ignored to ensure that the meaning of the query is what we're capturing.

        :return: a unique hash of the query
        '''
        query = {}
        for key, value in self.query.items():
            if key == u'filters':
                filters = {}
                for filter_field, filter_value in value.items():
                    # to ensure the order doesn't matter we have to convert everything to unicode
                    # and then sort it
                    filters[unicode(filter_field)] = sorted(map(unicode, filter_value))
                query[u'filters'] = filters
            else:
                query[unicode(key)] = unicode(value)

        # sort_keys=True is used otherwise the key ordering would change between python versions
        # and the hash wouldn't match even if the query was the same
        dumped_query = json.dumps(query, ensure_ascii=False, sort_keys=True).encode(u'utf8')
        return hashlib.sha1(dumped_query).hexdigest()

    def get_rounded_version(self, resource_id):
        '''
        Round the requested version of this query down to the nearest actual version of the
        resource. This is necessary because we work in a system where although you can just query at
        a timestamp you should round it down to the nearest known version. This guarantees that when
        you come back and search the data later you'll get the same data. If the version requested
        is older than the oldest version of the resource then the requested version itself is
        returned (this is just a choice I made, we could return 0 for example instead).

        An example: a version of resource A is created at t=2 and then a search is completed on it
        at t=5. If a new version is created at t=3 then the search at t=5 won't return the data it
        should. We could solve this problem in one of two ways:

            - limit new versions of resources to only be either older than the oldest saved search
            - rely on the current time when resource versions are created and searches are saved

        There are however issues with both of these approaches:

            - forcing new resource versions to exceed currently created search versions would
              require excessive a reasonable amount of work to figure out what the latest search
              version is and also crosses extension boundaries as the versioned-datastore extension
              would then rely on data in this extension's tables, rather than the other way round
            - we want to be able to create resource versions beyond the latest version in the system
              but before the current time to accommodate non-live data (i.e. data that comes from
              timestamped dumps). There are a few benefits to allowing this, for example it allows
              loading data where we create a number of resource versions at the same time but the
              versions themselves represent when the data was extacted from another system or indeed
              created rather than when it was loaded into CKAN.

        See the versioned_datastore doc for more information on this.

        :param resource_id: the id of the resource being searched
        :return: the rounded version or None if no versions are available for the given resource id
        '''
        action = toolkit.get_action(u'datastore_get_resource_versions')
        versions = sorted(r[u'version'] for r in action({}, {u'resource_id': resource_id}))

        if not versions:
            # something isn't right, just return None
            return None

        if self.requested_version < versions[0]:
            # use the requested version if it's lower than the lowest available version
            return self.requested_version
        elif self.requested_version >= versions[-1]:
            # cap the requested version to the latest version
            return versions[-1]
        else:
            # find the lowest, nearest version to the requested one
            position = bisect.bisect_right(versions, self.requested_version)
            return versions[position - 1]

    def get_count(self, resource_id):
        '''
        Retrieve the number of records matched by this query, resource id and version combination.
        :param resource_id: the resource id
        :return: an integer value
        '''
        data_dict = copy.deepcopy(self.query)
        data_dict.update({
            u'resource_id': resource_id,
            # use the version parameter cause it's nicer than having to go in and modify the filters
            u'version': self.get_rounded_version(resource_id),
        })
        result = toolkit.get_action(u'datastore_search')({}, data_dict)
        return result[u'total']


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
