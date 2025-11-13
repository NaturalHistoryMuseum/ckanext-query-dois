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
from dataclasses import asdict, dataclass
from typing import Optional
from urllib.parse import urlencode

from ckan import model
from ckan.plugins import toolkit

from ..lib.stats import DOWNLOAD_ACTION, SAVE_ACTION
from ..lib.utils import get_resource_and_package
from ..model import QueryDOI, QueryDOIStat

column_param_mapping = (
    ('doi', QueryDOIStat.doi),
    ('identifier', QueryDOIStat.identifier),
    ('domain', QueryDOIStat.domain),
    ('action', QueryDOIStat.action),
)


@dataclass
class InaccessibleResource:
    id: Optional[str] = None
    name: Optional[str] = None
    package_id: Optional[str] = None
    package_name: Optional[str] = None
    package_title: Optional[str] = None
    record_count: int = 0

    @property
    def is_unknown(self):
        return self.name is None

    def as_dict(self):
        return asdict(self)


def get_query_doi(doi):
    """
    Retrieves a QueryDOI object from the database for the given DOI, if there is one,
    otherwise returns None.

    :param doi: the doi (full doi, prefix/suffix)
    :returns: A QueryDOI object or None
    """
    return model.Session.query(QueryDOI).filter(QueryDOI.doi == doi).first()


def get_authors(packages):
    """
    Retrieves all the authors from the given packages, de-duplicates them (if necessary)
    and then returns them as a list.

    Note that this function takes a list of packages as it is multi-package and
    therefore multi-resource ready.

    :param packages: the packages
    :returns: a list of author(s)
    """
    # use an ordered dict in the absence of a sorted set
    authors = OrderedDict()
    for package in packages:
        author = package['author']
        # some author values will contain many authors with a separator, perhaps , or ;
        for separator in (';', ','):
            if separator in author:
                authors.update({a: True for a in author.split(separator)})
                break
        else:
            # if the author value didn't contain a separator then we can just use the value as is
            authors[author] = True

    return list(authors.keys())


def encode_params(params, version=None, extras=None, for_api=False):
    """
    Encodes the parameters for a query in the CKAK resource view format and returns as a
    query string.

    :param params: a dict of parameters, such as a DatastoreQuery's query dict
    :param version: the version to add into the query string (default: None)
    :param extras: an optional dict of extra parameters to add as well as the ones found
        in the params dict (default: None)
    :param for_api: whether the query string is for a CKAN resource view or an API get
        as it changes the format (default: False)
    :returns: a query string of the query parameters (no ? at the start but will include
        & if needed)
    """
    query_string = {}
    extras = [] if extras is None else extras.items()
    # build the query string from the dicts we have first
    for param, value in itertools.chain(params.items(), extras):
        # make sure to ignore all version data in the dicts
        if param == 'version':
            continue
        if param == 'filters':
            value = copy.deepcopy(value)
            if version is None:
                value.pop('__version__', None)
        query_string[param] = value

    # now add the version in if needed
    if version is not None:
        query_string.setdefault('filters', {})['__version__'] = version

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
                    parts.extend('{}:{}'.format(sub_key, v) for v in sub_value)
                value = '|'.join(parts)
            query_string[param] = value

    return urlencode(query_string)


def generate_rerun_urls(resource, package, query, rounded_version=None):
    """
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
    :returns: a dict of urls
    """
    page_url = toolkit.url_for(
        'resource.read', id=package['name'], resource_id=resource['id']
    )
    api_url = '/api/action/datastore_search'
    api_extras = {'resource_id': resource['id']}
    url_dict = {
        'page': {
            'current': page_url + '?' + encode_params(query),
        }
    }
    if rounded_version is not None:
        url_dict['page']['original'] = (
            page_url + '?' + encode_params(query, version=rounded_version)
        )
        url_dict['api'] = {
            'current': api_url
            + '?'
            + encode_params(query, extras=api_extras, for_api=True),
            'original': api_url
            + '?'
            + encode_params(
                query, version=rounded_version, extras=api_extras, for_api=True
            ),
        }
    return url_dict


def get_stats(query_doi):
    """
    Retrieve some simple stats about the query DOI - this includes the total downloads and the
    last download timestamp. Note that we are specifically looking for downloads here, no other
    actions are considered.

    :param query_doi: the QueryDOI object
    :returns: a 3-tuple containing the total downloads, total saves and the last download timestamp
    """
    # count how many download stats we have on this doi
    download_total = (
        model.Session.query(QueryDOIStat)
        .filter(QueryDOIStat.doi == query_doi.doi)
        .filter(QueryDOIStat.action == DOWNLOAD_ACTION)
        .count()
    )
    # count how many save stats we have on this doi
    save_total = (
        model.Session.query(QueryDOIStat)
        .filter(QueryDOIStat.doi == query_doi.doi)
        .filter(QueryDOIStat.action == SAVE_ACTION)
        .count()
    )
    # find the last stats object we have for this doi
    last = (
        model.Session.query(QueryDOIStat)
        .filter(QueryDOIStat.doi == query_doi.doi)
        .filter(QueryDOIStat.action == DOWNLOAD_ACTION)
        .order_by(QueryDOIStat.id.desc())
        .first()
    )
    return download_total, save_total, last.timestamp if last is not None else None


def render_datastore_search_doi_page(query_doi):
    """
    Renders a DOI landing page for a datastore_search based query DOI.

    :param query_doi: the query DOI
    :returns: the rendered page
    """
    # currently we only deal with single resource query DOIs
    resource_id = query_doi.get_resource_ids()[0]
    rounded_version = query_doi.get_rounded_versions()[0]

    try:
        resource, package = get_resource_and_package(resource_id)
        is_inaccessible = False
        in_datastore = resource.get('datastore_active', False)
    except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
        resource = None
        package = None
        in_datastore = False
        is_inaccessible = True

    # we ignore the saves count as it will always be 0 for a datastore_search DOI
    downloads, _saves, last_download_timestamp = get_stats(query_doi)
    usage_stats = {
        'downloads': downloads,
        'last_download_timestamp': last_download_timestamp,
    }

    # warnings
    warnings = []
    if is_inaccessible:
        warnings = [
            toolkit._(
                'All resources associated with this search have been deleted, moved, '
                'or are no longer available in their previous format.'
            )
        ]
    elif not in_datastore:
        warnings = [
            toolkit._(
                'All records associated with this search have been removed from the '
                'search index. The data may still exist, but they are no longer '
                'versioned and cannot be filtered.'
            )
        ]

    context = {
        'query_doi': query_doi,
        'doi': query_doi.doi,
        'resource': resource,
        'package': package,
        'version': rounded_version,
        'usage_stats': usage_stats,
        'is_inaccessible': is_inaccessible,
        'in_datastore': in_datastore,
        'warnings': warnings,
        # these are defaults for if the resource is inaccessible
        'package_doi': None,
        'authors': toolkit._('Unknown'),
        'reruns': {},
    }

    if not is_inaccessible:
        context.update(
            {
                # this is effectively an integration point with the ckanext-doi
                # extension. If there is demand we should open this up so that we can
                # support other dois on packages extensions
                'package_doi': (
                    package['doi'] if package.get('doi_status', False) else None
                ),
                'authors': get_authors([package]),
                'reruns': generate_rerun_urls(
                    resource,
                    package,
                    query_doi.query,
                    rounded_version if in_datastore else None,
                ),
            }
        )

    return toolkit.render('query_dois/single_landing_page.html', context)


def get_package_and_resource_info(resource_ids):
    """
    Retrieve basic info about the packages and resources from the list of resource ids.

    :param resource_ids: a list of resource ids
    :returns: two dicts, one of package info and one of resource info
    """
    raction = toolkit.get_action('resource_show')
    paction = toolkit.get_action('package_show')

    packages = {}
    resources = {}
    inaccessible_resources = []
    for resource_id in resource_ids:
        try:
            resource = raction({}, dict(id=resource_id))
        except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
            inaccessible_resources.append(InaccessibleResource(id=resource_id))
            continue

        package_id = resource['package_id']
        if package_id not in packages:
            # we don't want to save this *yet* in case all the resources are
            # inaccessible, but we want the package details
            pkg_dict = paction({}, dict(id=package_id))
            package = {
                'title': pkg_dict['title'],
                'name': pkg_dict['name'],
                'resource_ids': [],
            }
        else:
            package = packages.get(package_id)

        # for query DOIs, non-datastore counts as inaccessible, but we can still get
        # the name and package details
        if not resource.get('datastore_active', False):
            inaccessible_resources.append(
                InaccessibleResource(
                    id=resource_id,
                    name=resource['name'],
                    package_id=package_id,
                    package_name=package['name'],
                    package_title=package['title'],
                )
            )
            continue

        # now we can save everything
        resources[resource_id] = {
            'name': resource['name'],
            'package_id': package_id,
        }
        package['resource_ids'].append(resource_id)
        packages[package_id] = package

    return packages, resources, inaccessible_resources


def create_current_slug(query_doi: QueryDOI, ignore_resources=None) -> str:
    """
    Creates a slug for the given query DOI at the current version, this is done with a
    nav slug which has no version.

    :param query_doi: the QueryDOI
    :param ignore_resources: a list of resource IDs to ignore
    :returns: a slug
    """
    resource_ids = query_doi.get_resource_ids()
    if ignore_resources:
        resource_ids = [r for r in resource_ids if r not in ignore_resources]

    slug_data_dict = {
        'query': query_doi.query,
        'query_version': query_doi.query_version,
        'resource_ids': resource_ids,
        'nav_slug': True,
    }
    current_slug = toolkit.get_action('vds_slug_create')({}, slug_data_dict)
    return current_slug['slug']


def render_multisearch_doi_page(query_doi: QueryDOI):
    """
    Renders a DOI landing page for a datastore_multisearch based query DOI.

    :param query_doi: the query DOI
    :returns: the rendered page
    """
    packages, resources, inaccessible_resources = get_package_and_resource_info(
        query_doi.get_resource_ids()
    )
    inaccessible_count = len(inaccessible_resources)

    # usage stats
    downloads, saves, last_download_timestamp = get_stats(query_doi)
    usage_stats = {
        'downloads': downloads,
        'saves': saves,
        'last_download_timestamp': last_download_timestamp,
    }

    # current details
    sorted_resource_counts = sorted(
        [(k, v) for k, v in query_doi.resource_counts.items() if k in resources],
        key=operator.itemgetter(1),
        reverse=True,
    )
    current_details = {
        'resource_count': len(resources),
        'package_count': len(packages),
        'sorted_resource_counts': sorted_resource_counts,
        'record_count': query_doi.count
        if inaccessible_count == 0
        else sum([v for k, v in sorted_resource_counts]),
    }

    # saved details
    if inaccessible_count == 0:
        saved_details = {
            'resource_count': len(resources),
            'record_count': query_doi.count,
            'missing_resources': 0,
            'missing_records': 0,
        }
    else:
        saved_details = {
            'resource_count': len(query_doi.resource_counts),
            'record_count': query_doi.count,
            'missing_resources': inaccessible_count,
            'missing_records': query_doi.count - current_details['record_count'],
        }

    # warnings
    warnings = []
    if len(resources) == 0:
        current_slug = None
        warnings = [
            toolkit._(
                'All resources associated with this search have been deleted, moved, '
                'or are no longer available in their previous format.'
            )
        ]
    else:
        current_slug = create_current_slug(
            query_doi, ignore_resources=[r.id for r in inaccessible_resources]
        )
        if inaccessible_count > 0:
            warnings.append(
                toolkit._(
                    'Some resources have been deleted, moved, or are no longer '
                    'available. Affected resources: '
                )
                + str(inaccessible_count)
            )

    # inaccessible resources
    unknown = {'resource_count': 0, 'record_count': 0}
    known = []
    for res in inaccessible_resources:
        if res.is_unknown:
            unknown['resource_count'] += 1
            unknown['record_count'] += query_doi.resource_counts[res.id]
        else:
            res.record_count = query_doi.resource_counts[res.id]
            known.append(res.as_dict())
    inaccessible_resource_details = known
    if unknown['resource_count'] > 0:
        inaccessible_resource_details.append(
            InaccessibleResource(
                id=None,
                name=' '.join(
                    [toolkit._('Unknown resources'), f'({unknown["resource_count"]})']
                ),
                package_title=toolkit._('Unknown package'),
                record_count=unknown['record_count'],
            ).as_dict()
        )

    context = {
        'query_doi': query_doi,
        'original_slug': query_doi.doi,
        'current_slug': current_slug,
        'usage_stats': usage_stats,
        'resources': resources,
        'packages': packages,
        'details': current_details,
        'saved_details': saved_details,
        'has_changed': inaccessible_count > 0,
        'is_inaccessible': len(resources) == 0,
        'warnings': warnings,
        'inaccessible_resources': inaccessible_resource_details,
    }
    return toolkit.render('query_dois/multisearch_landing_page.html', context)
