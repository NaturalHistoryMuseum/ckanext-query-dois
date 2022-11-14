#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import itertools
from datetime import datetime
from functools import partial

from ckan import model
from ckan.plugins import toolkit
from sqlalchemy import false


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
    for row in query:
        if is_datastore_resource(dict(resource_id=row.id)):
            public_resource_ids.add(row.id)

    return public_resource_ids


def get_invalid_resources(resource_ids):
    '''

    :param resource_ids:
    :return:
    '''
    resource_ids = set(resource_ids)
    public_resource_ids = get_public_datastore_resources(only=resource_ids)
    return resource_ids - public_resource_ids


def extract_resource_ids_and_versions(
    req_version=None, req_resource_ids=None, req_resource_ids_and_versions=None
):
    if req_resource_ids_and_versions is not None:
        req_resource_ids = set(req_resource_ids_and_versions.keys())
    else:
        req_resource_ids = (
            set(req_resource_ids) if req_resource_ids is not None else set()
        )

    resource_ids = get_public_datastore_resources(only=req_resource_ids)
    bad_resources = req_resource_ids - resource_ids
    if bad_resources:
        # resources were requested, but not all of them were public/active
        raise toolkit.ValidationError(
            f'Some of the resources requested are private or not active, '
            f'DOIs can only be created using public, active resources. '
            f'Invalid resources: {", ".format(bad_resources)}'
        )
    elif len(resource_ids) == 0:
        # no resources available
        raise toolkit.ValidationError('No public resources are available')

    version = req_version if req_version is not None else to_timestamp(datetime.now())
    # round all the versions down for each resource
    if req_resource_ids_and_versions is not None:
        iterator = req_resource_ids_and_versions.items()
    else:
        iterator = zip(resource_ids, itertools.repeat(version))

    round_version_action = partial(
        toolkit.get_action('datastore_get_rounded_version'), {}
    )
    resource_ids_and_versions = {}
    for resource_id, resource_version in iterator:
        data_dict = {'resource_id': resource_id, 'version': resource_version}
        rounded_version = round_version_action(data_dict)
        # this isn't really something that should happen, but if it does it just means there's no
        # data in the resource's datastore index, leave it out of the return dict
        if rounded_version is not None:
            resource_ids_and_versions[resource_id] = rounded_version
    return resource_ids_and_versions


def to_timestamp(moment: datetime) -> int:
    """
    Converts the given moment to a UNIX epoch in milliseconds.

    :param moment: a datetime object
    :return: integer UNIX epoch in milliseconds
    """
    ts = moment.timestamp()
    # multiply by 1000 to get the time in milliseconds and use int to remove any decimal places
    return int(ts * 1000)
