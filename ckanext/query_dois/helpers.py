import json


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
