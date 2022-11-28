#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import itertools
from functools import partial

from ckan import model
from ckan.plugins import toolkit
from sqlalchemy import false


def get_resource_and_package(resource_id):
    """
    Given a resource ID, returns the resource's dict and the parent package's dict too.

    :param resource_id: the resource ID
    :return: a 2-tuple, containing the resource dict and the package dict
    """
    resource = toolkit.get_action('resource_show')({}, {'id': resource_id})
    package = toolkit.get_action('package_show')({}, {'id': resource['package_id']})
    return resource, package


def get_public_datastore_resources(only=None):
    """
    Retrieve all the public resource ids from the database that are also in the
    datastore. If the only parameter is provided, it is used to filter the return so
    that it only includes those in the only list.

    :param only: a list/set/whatever of resource ids to include in the returned set
    :return: a set of public resource ids
    """
    # retrieve all resource ids that are active, in an active package and in a public package
    query = (
        model.Session.query(model.Resource)
        .join(model.Package)
        .filter(model.Resource.state == 'active')
        .filter(model.Package.state == 'active')
        .filter(model.Package.private == false())
        .with_entities(model.Resource.id)
    )
    if only:
        query = query.filter(model.Resource.id.in_(list(only)))

    public_resource_ids = set()

    # cache this action (with context) so that we don't have to retrieve it over and over again
    is_datastore_resource = partial(
        toolkit.get_action('datastore_is_datastore_resource'), {}
    )
    for resource_id in query:
        if is_datastore_resource(dict(resource_id=resource_id)):
            public_resource_ids.add(resource_id)

    return public_resource_ids


def get_authors(resource_ids):
    """
    Given some resource ids, return a list of unique authors from the packages
    associated with them.

    :param resource_ids: the resource ids
    :return: a list of authors
    """
    query = (
        model.Session.query(model.Resource)
        .join(model.Package)
        .filter(model.Resource.id.in_(list(resource_ids)))
        .with_entities(model.Package.author)
    )
    return list(set(itertools.chain.from_iterable(query)))


def get_resource_counts(query, query_version, resource_ids_and_versions):
    """
    Given a set of query parameters, figure out how many records are found on each
    resource.

    :param query: the query dict
    :param query_version: the query version
    :param resource_ids_and_versions: the resource ids and their specific versions
    :return: a dict of resource ids to counts
    """
    counts = {}
    multisearch_action = partial(toolkit.get_action('datastore_multisearch'), {})
    for resource_id, version in resource_ids_and_versions.items():
        # find out how many records match the query in the specific resource
        search_data_dict = {
            'query': query,
            'query_version': query_version,
            'resource_ids': [resource_id],
            'version': version,
            'size': 0,
        }
        counts[resource_id] = multisearch_action(search_data_dict)['total']
    return counts
