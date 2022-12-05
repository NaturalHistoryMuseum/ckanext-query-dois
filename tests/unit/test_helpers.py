import random
import string
from datetime import datetime

import pytest
from ckan.tests import factories
from ckanext.query_dois.lib.doi import create_database_entry
from ckanext.query_dois.helpers import get_doi_count, get_most_recent_dois
from ckanext.query_dois.model import QueryDOI


def make_doi(resource_id) -> QueryDOI:
    random_str = "".join(random.choice(string.ascii_lowercase) for _ in range(10))
    return create_database_entry(
        doi=random_str,
        query={},
        query_hash=random_str,
        resources_and_versions={resource_id: 4},
        timestamp=datetime.now(),
        record_count=1,
    )


@pytest.mark.usefixtures("clean_db", "setup_db")
class TestGetDOICount:
    def test_when_dois_have_been_made(self):
        # create 2 packages
        package_1 = factories.Dataset(name="package1")
        package_2 = factories.Dataset(name="package2")
        # create 2 resources per package
        resource_1 = factories.Resource(package_id=package_1["id"])
        resource_2 = factories.Resource(package_id=package_1["id"])
        resource_3 = factories.Resource(package_id=package_2["id"])
        resource_4 = factories.Resource(package_id=package_2["id"])

        dois = [
            make_doi(resource_1["id"]),
            make_doi(resource_1["id"]),
            make_doi(resource_2["id"]),
            make_doi(resource_2["id"]),
            make_doi(resource_2["id"]),
            make_doi(resource_3["id"]),
            make_doi(resource_4["id"]),
            make_doi(resource_4["id"]),
            make_doi(resource_4["id"]),
            make_doi(resource_4["id"]),
            make_doi(resource_4["id"]),
            make_doi(resource_4["id"]),
        ]
        assert get_doi_count(package_1["id"]) == 5
        assert get_doi_count(package_2["id"]) == 7

    def test_no_dois_have_been_made(self):
        # create 2 packages
        package_1 = factories.Dataset(name="package1")
        package_2 = factories.Dataset(name="package2")
        # create 2 resources per package
        resource_1 = factories.Resource(package_id=package_1["id"])
        resource_2 = factories.Resource(package_id=package_1["id"])
        resource_3 = factories.Resource(package_id=package_2["id"])
        resource_4 = factories.Resource(package_id=package_2["id"])
        # create a doi on a resource in package 2
        make_doi(resource_3["id"])
        assert get_doi_count(package_1["id"]) == 0

    def test_no_resources(self):
        # create a package
        package_1 = factories.Dataset(name="package1")
        # create no resources
        assert get_doi_count(package_1["id"]) == 0

    def test_package_not_exist(self):
        assert get_doi_count("fiowenfwuibefuiwbefuiwbef") == 0


@pytest.mark.usefixtures("clean_db", "setup_db")
class TestGetMostRecentDOIs:
    def test_no_package(self):
        assert len(get_most_recent_dois("efiownfwe", 5)) == 0

    def test_no_resources(self):
        package_1 = factories.Dataset(name="package1")
        assert len(get_most_recent_dois(package_1["id"], 5)) == 0

    def test_no_dois(self):
        package_1 = factories.Dataset(name="package1")
        resource_1 = factories.Resource(package_id=package_1["id"])
        assert len(get_most_recent_dois(package_1["id"], 5)) == 0

    def test_dois_less_than_limit(self):
        package_1 = factories.Dataset(name="package1")
        resource_1 = factories.Resource(package_id=package_1["id"])
        resource_2 = factories.Resource(package_id=package_1["id"])
        make_doi(resource_1["id"])
        make_doi(resource_2["id"])
        assert len(get_most_recent_dois(package_1["id"], 5)) == 2

    def test_dois_more_than_limit(self):
        package_1 = factories.Dataset(name="package1")
        resource_1 = factories.Resource(package_id=package_1["id"])
        for _ in range(10):
            make_doi(resource_1["id"])
        assert len(get_most_recent_dois(package_1["id"], 5)) == 5
