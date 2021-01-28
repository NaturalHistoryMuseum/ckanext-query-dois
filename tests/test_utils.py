import pytest
from ckan.tests import factories
from ckan.tests.helpers import call_action

from ckanext.query_dois.lib.utils import get_resource_and_package


@pytest.mark.usefixtures(u'clean_db')
@pytest.mark.filterwarnings(u'ignore::sqlalchemy.exc.SADeprecationWarning')
def test_get_resource_and_package():
    # TODO: this is a dumb test but we need at least one test to have the tests not just constantly
    #       fail, so here we are
    package = factories.Dataset()
    resource = factories.Resource(package_id=package[u'id'])

    shown_resource = call_action(u'resource_show', id=resource[u'id'])
    shown_package = call_action(u'package_show', id=package[u'id'])

    assert get_resource_and_package(resource[u'id']) == (shown_resource, shown_package)
