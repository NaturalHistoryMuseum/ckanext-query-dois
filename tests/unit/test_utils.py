import pytest
from ckan.tests import factories
from ckan.tests.helpers import call_action

from ckanext.query_dois.lib.utils import get_resource_and_package


@pytest.mark.usefixtures('clean_db')
@pytest.mark.filterwarnings('ignore::sqlalchemy.exc.SADeprecationWarning')
def test_get_resource_and_package():
    package = factories.Dataset()
    resource = factories.Resource(package_id=package['id'])

    shown_resource = call_action('resource_show', id=resource['id'])
    shown_package = call_action('package_show', id=package['id'])

    assert get_resource_and_package(resource['id']) == (shown_resource, shown_package)
