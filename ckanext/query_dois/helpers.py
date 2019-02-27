import json
from datetime import datetime

from sqlalchemy import or_

from ckan import model, plugins
from ckanext.query_dois.model import QueryDOI


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
    package = plugins.toolkit.get_action(u'package_show')({}, {u'id': package_id})
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
    return plugins.toolkit.url_for(u'query_doi_landing_page', data_centre=data_centre,
                                   identifier=identifier)
