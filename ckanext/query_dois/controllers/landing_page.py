#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import copy
import itertools
import json
from urllib import urlencode

from jinja2.filters import do_truncate
from webhelpers.html.builder import literal

from ckan import plugins, model
from ckan.lib.helpers import url_for
from ckanext.query_dois.lib.stats import DOWNLOAD_ACTION
from ckanext.query_dois.lib.utils import get_resource_and_package
from ckanext.query_dois.model import QueryDOI, QueryDOIStat


class LandingPageController(plugins.toolkit.BaseController):
    '''
    Landing page for query DOIs. This is the page the DOIs actually point to.
    '''

    def _get_query_doi(self, doi):
        '''
        Retrieves a QueryDOI object from the database for the given DOI, if there is one, otherwise
        returns None.

        :param doi: the doi (full doi, prefix/suffix)
        :return: A QueryDOI object or None
        '''
        return model.Session.query(QueryDOI).filter(QueryDOI.doi == doi).first()

    def _get_authors(self, packages, max_length=50):
        '''
        Retrieves all the authors from the given packages, de-duplicates and truncates them (if
        necessary) and then returns an ordered list of them.

        Note that this function takes a list of packages as it is multi-package and therefore
        multi-resource ready.

        :param packages: the packages
        :param max_length: the maximum length the author string can be without being truncated
        :return: a list of shortened author(s) HTML strings, each providing the full author(s) text
                 on hover
        '''
        authors = set()
        for package in packages:
            author = package[u'author']
            if len(author) <= max_length:
                authors.add(author)
            else:
                for separator in [u';', u',']:
                    if separator in author:
                        # use the separator to split the authors, then join only the first 4 back up
                        shortened = u';'.join(author.split(separator)[:4])
                        break
                else:
                    # otherwise use the jinja truncate function (may split author names)
                    shortened = do_truncate(author, length=max_length, end=u'')

                authors.add(
                    u'{} <abbr title="{}" style="cursor: pointer;">et al.</abbr>'.format(shortened,
                                                                                         author))
        return literal(u', '.join(sorted(authors)))

    def _encode_params(self, params, version=None, extras=None, for_api=False):
        '''
        Encodes the parameters for a query in the CKAK resource view format and returns as a query
        string.

        :param params: a dict of parameters, such as a DatastoreQuery's query dict
        :param version: the version to add into the query string (default: None)
        :param extras: an optional dict of extra parameters to add as well as the ones found in the
                       params dict (default: None)
        :param for_api: whether the query string is for a CKAN resource view or an API get as it
                        changes the format (default: False)
        :return: a query string of the query parameters (no ? at the start but will include & if
                 needed)
        '''
        query_string = {}
        extras = [] if extras is None else extras.items()
        # build the query string from the dicts we have first
        for param, value in itertools.chain(params.items(), extras):
            # make sure to ignore all version data in the dicts
            if param == u'version':
                continue
            if param == u'filters':
                value = copy.deepcopy(value)
                if version is None:
                    value.pop(u'__version__', None)
            query_string[param] = value

        # now add the version in if needed
        if version is not None:
            query_string.setdefault(u'filters', {})[u'__version__'] = version

        # finally format any nested dicts correctly (this is for the filters field basically)
        for param, value in query_string.items():
            if isinstance(value, dict):
                if for_api:
                    # the API takes the data in JSON format so we just need to serialise it
                    value = json.dumps(value)
                else:
                    # if the data is going in a query string for a resource view it needs to be
                    # encoded in a special way
                    parts = []
                    for sub_key, sub_value in value.items():
                        if not isinstance(sub_value, list):
                            sub_value = [sub_value]
                        parts.extend(u'{}:{}'.format(sub_key, v) for v in sub_value)
                    value = u'|'.join(parts)
                query_string[param] = value

        return urlencode(query_string)

    def _generate_rerun_urls(self, resource, package, query, rounded_version):
        '''
        Generate a dict containing all the "rerun" URLs needed to allow the user to revisit the data
        either through the website or through the API. The dict returned will look like following:

            {
                "page": {
                    "original": ...
                    "current": ...
                },
                "api": {
                    "original": ...
                    "current": ...
                }
            }

        :param resource: the resource dict
        :param package: the package dict
        :param query: the query dict
        :param rounded_version: the version rounded down to the nearest available on the resource
        :return: a dict of urls
        '''
        page_url = url_for(controller=u'package', action=u'resource_read', id=package[u'name'],
                           resource_id=resource[u'id'])
        api_url = u'/api/action/datastore_search'
        api_extras = {u'resource_id': resource[u'id']}
        return {
            u'page': {
                u'original': page_url + u'?' + self._encode_params(query, version=rounded_version),
                u'current': page_url + u'?' + self._encode_params(query),
            },
            u'api': {
                u'original': api_url + u'?' + self._encode_params(query, version=rounded_version,
                                                                  extras=api_extras, for_api=True),
                u'current': api_url + u'?' + self._encode_params(query, extras=api_extras,
                                                                 for_api=True),
            }
        }

    def _get_download_url(self, package, resource, query, rounded_version):
        '''
        Returns the URL for the CKANPackager's download endpoint, or None if the CKANPackager is not
        in use.

        :param package: the package dict
        :param resource: the resource dict
        :param query: the query dict
        :param rounded_version: the version rounded down to the nearest available on the resource
        :return: the URL for packaging the resource up with the CKANPackager or None if the
                 CKANPackager is not installed
        '''
        try:
            from ckanext.ckanpackager.lib.utils import url_for_package_resource
            url = url_for_package_resource(package[u'id'], resource[u'id'], use_request=False)
            return url + u'&' + self._encode_params(query, version=rounded_version)
        except ImportError:
            return None

    def _get_stats(self, query_doi):
        '''
        Retrieve some simple stats about the query DOI - this includes the total downloads and the
        last download timestamp. Note that we are specifically looking for downloads here, no other
        actions are considered.

        :param query_doi: the QueryDOI object
        :return: a 2-tuple containing the total downloads and the last download timestamp
        '''
        # count how many download stats we have on this doi
        total = model.Session.query(QueryDOIStat)\
            .filter(QueryDOIStat.doi == query_doi.doi)\
            .filter(QueryDOIStat.action == DOWNLOAD_ACTION)\
            .count()
        # find the last stats object we have for this doi
        last = model.Session.query(QueryDOIStat)\
            .filter(QueryDOIStat.doi == query_doi.doi) \
            .filter(QueryDOIStat.action == DOWNLOAD_ACTION) \
            .order_by(QueryDOIStat.id.desc())\
            .first()
        return total, last.timestamp if last is not None else None

    def get(self, data_centre, identifier):
        '''
        Renders the landing page for the given DOI.

        :param data_centre: the data centre prefix
        :param identifier: the DOI identifier
        :return: the rendered landing page
        '''
        doi = u'{}/{}'.format(data_centre, identifier)
        query_doi = self._get_query_doi(doi)
        if query_doi is None:
            raise plugins.toolkit.abort(404, plugins.toolkit._(u'DOI not recognised'))

        # currently we only deal with single resource query DOIs
        resource_id = query_doi.get_resource_ids()[0]
        rounded_version = query_doi.get_rounded_versions()[0]

        resource, package = get_resource_and_package(resource_id)
        downloads, last_download_timestamp = self._get_stats(query_doi)
        context = {
            u'query_doi': query_doi,
            u'doi': doi,
            u'resource': resource,
            u'package': package,
            # this is effectively an integration point with the ckanext-doi extension. If there is
            # demand we should open this up so that we can support other dois on packages extensions
            u'package_doi': package[u'doi'] if package.get(u'doi_status', False) else None,
            u'authors': self._get_authors([package]),
            u'version': rounded_version,
            u'reruns': self._generate_rerun_urls(resource, package, query_doi.query,
                                                 rounded_version),
            u'download_url': self._get_download_url(package, resource, query_doi.query,
                                                    rounded_version),
            u'downloads': downloads,
            u'last_download_timestamp': last_download_timestamp,
        }

        return plugins.toolkit.render(u'query_dois/landing_page.html', context)
