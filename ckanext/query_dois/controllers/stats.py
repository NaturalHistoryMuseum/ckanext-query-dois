import json

from ckan import model, plugins
from ckan.common import request, response
from ckanext.query_dois.model import QueryDOIStat, QueryDOI

# mapping of param names to QueryDOIStat columns
column_param_mapping = (
    (u'doi', QueryDOIStat.doi),
    (u'identifier', QueryDOIStat.identifier),
    (u'domain', QueryDOIStat.domain),
    (u'action', QueryDOIStat.action),
)


class StatsController(plugins.toolkit.BaseController):

    def get(self):
        '''
        Returns statistics in JSON format depending on the request parameters. The return will be a
        list with a dict representing the QueryDOIStat as each element.

        :return: a JSON stringified list of dicts
        '''
        query = model.Session.query(QueryDOIStat)

        # order by id ascending to avoid causing pagination issues
        query = query.order_by(QueryDOIStat.id.asc())

        # apply any parameters as filters
        for param_name, column in column_param_mapping:
            param_value = request.params.get(param_name, None)
            if param_value:
                query = query.filter(column == param_value)

        resource_id = request.params.get(u'resource_id', None)
        if resource_id:
            query = query\
                .join(QueryDOI, QueryDOI.doi == QueryDOIStat.doi)\
                .filter(QueryDOI.resource_ids.like(u'%{}%'.format(resource_id)))

        # apply the offset and limit, with sensible defaults
        query = query.offset(request.params.get(u'offset', 0))
        query = query.limit(request.params.get(u'limit', 100))

        # return the data as a JSON dumped list of dicts
        response.headers[u'Content-type'] = u'application/json'
        return json.dumps([stat.as_dict() for stat in query])
