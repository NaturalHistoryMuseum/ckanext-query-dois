#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import json

from ckanext.query_dois.model import QueryDOI
from datetime import datetime
from sqlalchemy import or_
from webhelpers.html.tags import link_to

from ckan import model
from ckan.plugins import toolkit


def render_filter_value(field, filter_value):
    '''
    Renders the given filter value for the given field. This should be called for each filter value
    rather than by passing a list or filter values.

    :param field: the field name
    :param filter_value: the filter value for the field
    :return: the value to display
    '''
    if field == u'__geo__':
        return json.loads(filter_value)[u'type']
    else:
        return filter_value


def get_most_recent_dois(package_id, number):
    '''
    Retrieve the most recent DOIs that have been minted on queries against the resources in the
    given package.

    :param package_id: the package's ID
    :param number: the number of DOIs to return
    :return: a list of QueryDOI objects
    '''
    package = toolkit.get_action(u'package_show')({}, {
        u'id': package_id
        })
    ors = [QueryDOI.on_resource(resource[u'id']) for resource in package[u'resources']]
    if not ors:
        return []
    return list(model.Session.query(QueryDOI)
                .filter(or_(*ors))
                .order_by(QueryDOI.id.desc()).limit(number))


# a tuple describing various ways of informing the user something happened a certain number of time
# units ago
time_resolutions = (
    (60, u'seceond', 1),
    (60 * 60, u'minute', 60),
    (60 * 60 * 24, u'hour', 60 * 60),
    (60 * 60 * 24 * 7, u'day', 60 * 60 * 24),
    (60 * 60 * 24 * 28, u'week', 60 * 60 * 24 * 7),
    (60 * 60 * 24 * 365, u'month', 60 * 60 * 24 * 28),
    (float(u'inf'), u'year', 60 * 60 * 24 * 365),
    )


def get_time_ago_description(query_doi):
    '''
    Given a QueryDOI object, return a short description of how long ago it was minted. The
    resolutions are described above in the time_resolutions tuple.

    :param query_doi: the QueryDOI object
    :return: a unicode string describing how long ago the DOI was minted
    '''
    seconds = (datetime.now() - query_doi.timestamp).total_seconds()
    for limit, unit, divisor in time_resolutions:
        if seconds < limit:
            value = int(seconds / divisor)
            plural = u's' if value > 1 else u''
            return u'{} {}{} ago'.format(value, unit, plural)


def get_landing_page_url(query_doi):
    '''
    Given a QueryDOI object, return the landing URL for it.

    :param query_doi: a QueryDOI object
    :return: the landing page URL
    '''
    data_centre, identifier = query_doi.doi.split(u'/')
    return toolkit.url_for(u'query_doi.landing_page', data_centre=data_centre,
                           identifier=identifier)


def create_citation_text(query_doi, creation_timestamp, resource_name, package_title,
                         package_doi=None, publisher=None, html=False):
    '''
    Creates the citation text for the given query doi and the given additional related arguments.

    :param query_doi: the query's DOI, this should just be the prefix/suffix, e.g. 10.xxxx/xxxxxx,
                      not the full URL
    :param creation_timestamp: a datetime object representing the exact moment the DOI was created
    :param resource_name: the name of the resource the DOI references
    :param package_title: the title of the package the resource the DOI references is in
    :param package_doi: the DOI of the package, if there is one (defaults to None)
    :param publisher: the publisher to use in the citation (defaults to None in which case the
                      ckanext.query_dois.publisher config value is used
    :param html: whether to include a tags around URLs in the returned string. Defaults to False
                 which does not add a tags and therefore the returned string is just pure text
    :return: a citation string for the given query DOI and associated data
    '''
    # default the publisher's value if needed
    if publisher is None:
        publisher = toolkit.config.get(u'ckanext.query_dois.publisher')

    # this is the citation's base form. This form is derived from the recommended RDA citation
    # format for evolving data when citing with a query. For more information see:
    # https://github.com/NaturalHistoryMuseum/ckanext-query-dois/issues/2
    citation_text = u'{publisher} ({year}). Data Portal Query on "{resource_name}" created at ' \
                    u'{creation_datetime} PID {query_doi}. Subset of "{dataset_name}" (dataset)'

    # these are the parameters which will be used on the above string
    params = {
        u'publisher': publisher,
        u'year': creation_timestamp.year,
        u'resource_name': resource_name,
        u'creation_datetime': creation_timestamp,
        u'query_doi': u'https://doi.org/{}'.format(query_doi),
        u'dataset_name': package_title,
        }

    # if we have a DOI for the package, include it
    if package_doi is not None:
        citation_text += u' PID {dataset_doi}.'
        params[u'dataset_doi'] = u'https://doi.org/{}'.format(package_doi)

    if html:
        # there are currently two fields which should be converted to a tags
        for field in (u'query_doi', u'dataset_doi'):
            doi_url = params.get(field, None)
            # the dataset_doi field is optional, hence the if here
            if doi_url is not None:
                params[field] = link_to(label=doi_url, url=doi_url, target=u'_blank')

    return citation_text.format(**params)
