# !/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK


from ckan import model
from ckan.plugins import toolkit
from flask import Blueprint, jsonify

from . import _helpers
from ..model import QueryDOI, QueryDOIStat

blueprint = Blueprint(name='query_doi', import_name=__name__, url_prefix='/doi')


@blueprint.route('/<data_centre>/<identifier>')
def landing_page(data_centre, identifier):
    """
    Renders the landing page for the given DOI.

    :param data_centre: the data centre prefix
    :param identifier: the DOI identifier
    :return: the rendered landing page
    """
    doi = '{}/{}'.format(data_centre, identifier)
    query_doi = _helpers.get_query_doi(doi)
    if query_doi is None:
        raise toolkit.abort(404, toolkit._('DOI not recognised'))

    if query_doi.query_version is not None:
        return _helpers.render_multisearch_doi_page(query_doi)
    else:
        return _helpers.render_datastore_search_doi_page(query_doi)


@blueprint.route('')
def doi_stats():
    """
    Returns statistics in JSON format depending on the request parameters. The return
    will be a list with a dict representing the QueryDOI as each element.

    This endpoint currently only supports filtering on the resource_id.

    :return: a JSON stringified list of dicts
    """
    query = model.Session.query(QueryDOI)

    # by default order by id desc to get the latest first
    query = query.order_by(QueryDOI.id.desc())

    resource_id = toolkit.request.params.get('resource_id', None)
    if resource_id:
        query = query.filter(QueryDOI.on_resource(resource_id))

    # apply the offset and limit, with sensible defaults
    query = query.offset(toolkit.request.params.get('offset', 0))
    query = query.limit(toolkit.request.params.get('limit', 100))

    # return the data as a JSON dumped list of dicts
    return jsonify([stat.as_dict() for stat in query])


@blueprint.route('/stats')
def action_stats():
    """
    Returns action statistics in JSON format depending on the request parameters. The
    return will be a list with a dict representing the QueryDOIStat as each element.

    :return: a JSON stringified list of dicts
    """
    query = model.Session.query(QueryDOIStat)

    # by default order by id desc to get the latest first
    query = query.order_by(QueryDOIStat.id.desc())

    # apply any parameters as filters
    for param_name, column in _helpers.column_param_mapping:
        param_value = toolkit.request.params.get(param_name, None)
        if param_value:
            query = query.filter(column == param_value)

    resource_id = toolkit.request.params.get('resource_id', None)
    if resource_id:
        query = query.join(QueryDOI, QueryDOI.doi == QueryDOIStat.doi).filter(
            QueryDOI.on_resource(resource_id)
        )

    # apply the offset and limit, with sensible defaults
    query = query.offset(toolkit.request.params.get('offset', 0))
    query = query.limit(toolkit.request.params.get('limit', 100))

    # return the data as a JSON dumped list of dicts
    return jsonify([stat.as_dict() for stat in query])
