# !/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

from ckanext.query_dois.lib.utils import get_resource_and_package
from ckanext.query_dois.model import QueryDOI, QueryDOIStat
from flask import Blueprint, jsonify

from ckan import model
from ckan.plugins import toolkit
from . import _helpers

blueprint = Blueprint(name=u'query_doi', import_name=__name__, url_prefix=u'/doi')


@blueprint.route('/<data_centre>/<identifier>')
def landing_page(data_centre, identifier):
    '''
    Renders the landing page for the given DOI.

    :param data_centre: the data centre prefix
    :param identifier: the DOI identifier
    :return: the rendered landing page
    '''
    doi = u'{}/{}'.format(data_centre, identifier)
    query_doi = _helpers.get_query_doi(doi)
    if query_doi is None:
        raise toolkit.abort(404, toolkit._(u'DOI not recognised'))

    # currently we only deal with single resource query DOIs
    resource_id = query_doi.get_resource_ids()[0]
    rounded_version = query_doi.get_rounded_versions()[0]

    resource, package = get_resource_and_package(resource_id)
    downloads, last_download_timestamp = _helpers.get_stats(query_doi)
    context = {
        u'query_doi': query_doi,
        u'doi': doi,
        u'resource': resource,
        u'package': package,
        # this is effectively an integration point with the ckanext-doi extension. If there is
        # demand we should open this up so that we can support other dois on packages extensions
        u'package_doi': package[u'doi'] if package.get(u'doi_status', False) else None,
        u'authors': _helpers.get_authors([package]),
        u'version': rounded_version,
        u'reruns': _helpers.generate_rerun_urls(resource, package, query_doi.query,
                                                rounded_version),
        u'download_url': _helpers.get_download_url(package, resource, query_doi.query,
                                                   rounded_version),
        u'downloads': downloads,
        u'last_download_timestamp': last_download_timestamp,
        }

    return toolkit.render(u'query_dois/landing_page.html', context)


@blueprint.route(u'')
def doi_stats():
    '''
    Returns statistics in JSON format depending on the request parameters. The return will be a
    list with a dict representing the QueryDOI as each element.

    This endpoint currently only supports filtering on the resource_id.

    :return: a JSON stringified list of dicts
    '''
    query = model.Session.query(QueryDOI)

    # by default order by id desc to get the latest first
    query = query.order_by(QueryDOI.id.desc())

    resource_id = toolkit.request.params.get(u'resource_id', None)
    if resource_id:
        query = query.filter(QueryDOI.on_resource(resource_id))

    # apply the offset and limit, with sensible defaults
    query = query.offset(toolkit.request.params.get(u'offset', 0))
    query = query.limit(toolkit.request.params.get(u'limit', 100))

    # return the data as a JSON dumped list of dicts
    return jsonify([stat.as_dict() for stat in query])


@blueprint.route(u'/stats')
def action_stats():
    '''
    Returns action statistics in JSON format depending on the request parameters. The return will be
    a list with a dict representing the QueryDOIStat as each element.

    :return: a JSON stringified list of dicts
    '''
    query = model.Session.query(QueryDOIStat)

    # by default order by id desc to get the latest first
    query = query.order_by(QueryDOIStat.id.desc())

    # apply any parameters as filters
    for param_name, column in _helpers.column_param_mapping:
        param_value = toolkit.request.params.get(param_name, None)
        if param_value:
            query = query.filter(column == param_value)

    resource_id = toolkit.request.params.get(u'resource_id', None)
    if resource_id:
        query = query \
            .join(QueryDOI, QueryDOI.doi == QueryDOIStat.doi) \
            .filter(QueryDOI.on_resource(resource_id))

    # apply the offset and limit, with sensible defaults
    query = query.offset(toolkit.request.params.get(u'offset', 0))
    query = query.limit(toolkit.request.params.get(u'limit', 100))

    # return the data as a JSON dumped list of dicts
    return jsonify([stat.as_dict() for stat in query])
