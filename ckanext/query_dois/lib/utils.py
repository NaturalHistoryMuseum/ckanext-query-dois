#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

from ckan.plugins import toolkit


def get_resource_and_package(resource_id):
    """
    Given a resource ID, returns the resource's dict and the parent package's dict too.

    :param resource_id: the resource ID
    :returns: a 2-tuple, containing the resource dict and the package dict
    """
    resource = toolkit.get_action('resource_show')({}, {'id': resource_id})
    package = toolkit.get_action('package_show')({}, {'id': resource['package_id']})
    return resource, package
