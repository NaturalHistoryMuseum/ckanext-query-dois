#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import copy
import hashlib
import json
import time
from collections import defaultdict

from ckan.plugins import toolkit


class DatastoreQuery(object):
    """
    This models datastore queries passed to datastore_search, not the DOIs created from
    them.
    """

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
            if param == 'version':
                requested_version = int(param_value)
            elif param == 'filters':
                filters = defaultdict(list)
                for filter_pair in param_value.split('|'):
                    filter_field, filter_value = filter_pair.split(':', 1)
                    filters[filter_field].append(filter_value)
                if requested_version is None:
                    popped_version = filters.pop('__version__', None)
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
            if param == 'version':
                requested_version = int(param_value)
            elif param == 'filters':
                filters = {}
                for filter_field, filter_value in param_value.items():
                    if not isinstance(filter_value, list):
                        filter_value = [filter_value]
                    filters[filter_field] = filter_value
                if requested_version is None:
                    popped_version = filters.pop('__version__', None)
                    if popped_version:
                        requested_version = int(popped_version[0])
                if filters:
                    query[param] = filters
            else:
                query[param] = param_value
        return query, requested_version

    def __init__(self, query_dict=None, data_dict=None):
        """
        Provide one of the 3 parameters depending on the format you have the query in.

        :param query_dict: a dict of query string parameters in the CKAN URL format - i.e. the
                           filters are split with colons and pipes etc
        :param data_dict: a dict of data dict parameters - i.e. the typical action data_dict format
        """
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
        """
        Create a unique hash for this query. To do this we have to ensure that the
        features like the order of filters is ignored to ensure that the meaning of the
        query is what we're capturing.

        :return: a unique hash of the query
        """
        query = {}
        for key, value in self.query.items():
            if key == 'filters':
                filters = {}
                for filter_field, filter_value in value.items():
                    # to ensure the order doesn't matter we have to convert everything to unicode
                    # and then sort it
                    filters[str(filter_field)] = sorted(map(str, filter_value))
                query['filters'] = filters
            else:
                query[str(key)] = str(value)

        # sort_keys=True is used otherwise the key ordering would change between python versions
        # and the hash wouldn't match even if the query was the same
        dumped_query = json.dumps(query, ensure_ascii=False, sort_keys=True).encode(
            'utf8'
        )
        return hashlib.sha1(dumped_query).hexdigest()

    def get_rounded_version(self, resource_id):
        """
        Round the requested version of this query down to the nearest actual version of
        the resource. See the versioned-search plugin for more details.

        :param resource_id: the id of the resource being searched
        :return: the rounded version or None if no versions are available for the given resource id
        """
        # first retrieve the rounded version to use
        data_dict = {'resource_id': resource_id, 'version': self.requested_version}
        return toolkit.get_action('datastore_get_rounded_version')({}, data_dict)

    def get_count(self, resource_id):
        """
        Retrieve the number of records matched by this query, resource id and version
        combination.

        :param resource_id: the resource id
        :return: an integer value
        """
        data_dict = copy.deepcopy(self.query)
        data_dict.update(
            {
                'resource_id': resource_id,
                # use the version parameter cause it's nicer than having to go in and modify the filters
                'version': self.get_rounded_version(resource_id),
                # we don't need the results, just the total
                'limit': 0,
            }
        )
        result = toolkit.get_action('datastore_search')({}, data_dict)
        return result['total']
