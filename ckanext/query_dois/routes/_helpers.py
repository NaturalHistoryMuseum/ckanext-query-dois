#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import copy
import itertools
import json
import operator
from collections import OrderedDict
from functools import partial
from urllib import urlencode

from ckan import model
from ckan.plugins import toolkit

from ..lib.stats import DOWNLOAD_ACTION, SAVE_ACTION
from ..lib.utils import get_resource_and_package
from ..model import QueryDOI, QueryDOIStat

column_param_mapping = (
    (u'doi', QueryDOIStat.doi),
    (u'identifier', QueryDOIStat.identifier),
    (u'domain', QueryDOIStat.domain),
    (u'action', QueryDOIStat.action),
)


def get_query_doi(doi):
    '''
    Retrieves a QueryDOI object from the database for the given DOI, if there is one, otherwise
    returns None.

    :param doi: the doi (full doi, prefix/suffix)
    :return: A QueryDOI object or None
    '''
    return model.Session.query(QueryDOI).filter(QueryDOI.doi == doi).first()


def get_authors(packages):
    '''
    Retrieves all the authors from the given packages, de-duplicates them (if necessary) and then
    returns them as a list.

    Note that this function takes a list of packages as it is multi-package and therefore
    multi-resource ready.

    :param packages: the packages
    :return: a list of author(s)
    '''
    # use an ordered dict in the absence of a sorted set
    authors = OrderedDict()
    for package in packages:
        author = package[u'author']
        # some author values will contain many authors with a separator, perhaps , or ;
        for separator in (u';', u','):
            if separator in author:
                authors.update({a: True for a in author.split(separator)})
                break
        else:
            # if the author value didn't contain a separator then we can just use the value as is
            authors[author] = True

    return list(authors.keys())


def encode_params(params, version=None, extras=None, for_api=False):
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


def generate_rerun_urls(resource, package, query, rounded_version):
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
    page_url = toolkit.url_for(u'resource.read', id=package[u'name'], resource_id=resource[u'id'])
    api_url = u'/api/action/datastore_search'
    api_extras = {
        u'resource_id': resource[u'id']
        }
    return {
        u'page': {
            u'original': page_url + u'?' + encode_params(query, version=rounded_version),
            u'current': page_url + u'?' + encode_params(query),
            },
        u'api': {
            u'original': api_url + u'?' + encode_params(query, version=rounded_version,
                                                        extras=api_extras, for_api=True),
            u'current': api_url + u'?' + encode_params(query, extras=api_extras,
                                                       for_api=True),
            }
        }


def get_download_url(package, resource, query, rounded_version):
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
        return url + u'&' + encode_params(query, version=rounded_version)
    except ImportError:
        return None


def get_stats(query_doi):
    '''
    Retrieve some simple stats about the query DOI - this includes the total downloads and the
    last download timestamp. Note that we are specifically looking for downloads here, no other
    actions are considered.

    :param query_doi: the QueryDOI object
    :return: a 3-tuple containing the total downloads, total saves and the last download timestamp
    '''
    # count how many download stats we have on this doi
    download_total = model.Session.query(QueryDOIStat) \
        .filter(QueryDOIStat.doi == query_doi.doi) \
        .filter(QueryDOIStat.action == DOWNLOAD_ACTION) \
        .count()
    # count how many save stats we have on this doi
    save_total = model.Session.query(QueryDOIStat) \
        .filter(QueryDOIStat.doi == query_doi.doi) \
        .filter(QueryDOIStat.action == SAVE_ACTION) \
        .count()
    # find the last stats object we have for this doi
    last = model.Session.query(QueryDOIStat) \
        .filter(QueryDOIStat.doi == query_doi.doi) \
        .filter(QueryDOIStat.action == DOWNLOAD_ACTION) \
        .order_by(QueryDOIStat.id.desc()) \
        .first()
    return download_total, save_total, last.timestamp if last is not None else None


def render_datastore_search_doi_page(query_doi):
    '''
    Renders a DOI landing page for a datastore_search based query DOI.

    :param query_doi: the query DOI
    :return: the rendered page
    '''
    # currently we only deal with single resource query DOIs
    resource_id = query_doi.get_resource_ids()[0]
    rounded_version = query_doi.get_rounded_versions()[0]

    resource, package = get_resource_and_package(resource_id)
    # we ignore the saves count as it will always be 0 for a datastore_search DOI
    downloads, _saves, last_download_timestamp = get_stats(query_doi)
    context = {
        u'query_doi': query_doi,
        u'doi': query_doi.doi,
        u'resource': resource,
        u'package': package,
        # this is effectively an integration point with the ckanext-doi extension. If there is
        # demand we should open this up so that we can support other dois on packages extensions
        u'package_doi': package[u'doi'] if package.get(u'doi_status', False) else None,
        u'authors': get_authors([package]),
        u'version': rounded_version,
        u'reruns': generate_rerun_urls(resource, package, query_doi.query, rounded_version),
        u'download_url': get_download_url(package, resource, query_doi.query, rounded_version),
        u'downloads': downloads,
        u'last_download_timestamp': last_download_timestamp,
    }

    return toolkit.render(u'query_dois/single_landing_page.html', context)


def get_package_and_resource_info(resource_ids):
    '''
    Retrieve basic info about the packages and resources from the list of resource ids.

    :param resource_ids: a list of resource ids
    :return: two dicts, one of package info and one of resource info
    '''
    raction = partial(toolkit.get_action(u'resource_show'), {})
    paction = partial(toolkit.get_action(u'package_show'), {})

    packages = {}
    resources = {}
    for resource_id in resource_ids:
        resource = raction(dict(id=resource_id))
        package_id = resource[u'package_id']
        resources[resource_id] = {
            u'name': resource[u'name'],
            u'package_id': package_id,
        }
        if package_id not in packages:
            package = paction(dict(id=package_id))
            packages[package_id] = {
                u'title': package[u'title'],
                u'resource_ids': []
            }
        packages[package_id][u'resource_ids'].append(resource_id)

    return packages, resources


def create_slugs(query_doi):
    '''
    Create two slugs, one for the original query and one for the query at the current version (to
    achieve this we just leave out any version information from the slug).

    :param query_doi: a query doi object
    :return: a slug for the original query and a slug for the current query
    '''
    original_slug_data_dict = {
        u'query': query_doi.query,
        u'query_version': query_doi.query_version,
        u'resource_ids_and_versions': query_doi.resources_and_versions,
    }
    original_slug = toolkit.get_action(u'datastore_create_slug')({}, original_slug_data_dict)

    current_slug_data_dict = {
        u'query': query_doi.query,
        u'query_version': query_doi.query_version,
        u'resource_ids': query_doi.get_resource_ids(),
    }
    current_slug = toolkit.get_action(u'datastore_create_slug')({}, current_slug_data_dict)
    return original_slug[u'slug'], current_slug[u'slug']


def render_multisearch_doi_page(query_doi):
    '''
    Renders a DOI landing page for a datastore_multisearch based query DOI.

    :param query_doi: the query DOI
    :return: the rendered page
    '''
    packages, resources = get_package_and_resource_info(query_doi.get_resource_ids())
    downloads, saves, last_download_timestamp = get_stats(query_doi)
    # order by count
    sorted_resource_counts = sorted(query_doi.resource_counts.items(), key=operator.itemgetter(1),
                                    reverse=True)
    original_slug, current_slug = create_slugs(query_doi)

    context = {
        u'query_doi': query_doi,
        u'resource_count': len(resources),
        u'package_count': len(packages),
        u'resources': resources,
        u'packages': packages,
        u'downloads': downloads,
        u'saves': saves,
        u'last_download_timestamp': last_download_timestamp,
        u'sorted_resource_counts': sorted_resource_counts,
        u'original_slug': original_slug,
        u'current_slug': current_slug,
    }
    return toolkit.render(u'query_dois/multisearch_landing_page.html', context)
