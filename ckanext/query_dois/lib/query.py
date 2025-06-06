#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import itertools
import time
from dataclasses import dataclass
from functools import cached_property, partial
from typing import Dict, List, Optional

from ckan import model
from ckan.plugins import toolkit
from sqlalchemy import false


def find_invalid_resources(resource_ids: List[str]) -> List[str]:
    """
    Given a list of resource IDs, return a list of resource IDs which are invalid.
    Resources are invalid if they are any of the following:

        - not datastore active resources (checked with vds_resource_check)
        - not active
        - not in an active package
        - not in a public package

    :param resource_ids: the resource IDs to check
    :returns: a list of resource IDs which failed the tests
    """
    invalid_resource_ids = set()

    # cache this action (with context) so that we don't have to retrieve it over and
    # over again
    is_datastore_resource = partial(toolkit.get_action('vds_resource_check'), {})

    # retrieve all resource ids passed to this function that are also active, in an
    # active package and in a public package
    query = (
        model.Session.query(model.Resource)
        .join(model.Package)
        .filter(model.Resource.id.in_(list(resource_ids)))
        .filter(model.Resource.state == 'active')
        .filter(model.Package.state == 'active')
        .filter(model.Package.private == false())
        .with_entities(model.Resource.id)
    )
    # go through each resource ID we found and check if they are datastore resources
    for row in query:
        if not is_datastore_resource(dict(resource_id=row.id)):
            invalid_resource_ids.add(row.id)

    return sorted(invalid_resource_ids)


@dataclass(frozen=True)
class Query:
    """
    Class representing a query against the versioned datastore.
    """

    resource_ids: List[str]
    version: int
    query: dict
    query_version: str

    @cached_property
    def query_hash(self) -> str:
        """
        :returns: a unique hash made from the query and query version
        """
        return toolkit.get_action('vds_multi_hash')(
            {}, {'query': self.query, 'query_version': self.query_version}
        )

    @cached_property
    def authors(self) -> List[str]:
        """
        Given some resource ids, return a list of unique authors from the packages
        associated with them.

        :returns: a list of authors
        """
        query = (
            model.Session.query(model.Resource)
            .join(model.Package)
            .filter(model.Resource.id.in_(self.resource_ids))
            .with_entities(model.Package.author)
        )
        return list(set(itertools.chain.from_iterable(query)))

    @cached_property
    def resources_and_versions(self) -> Dict[str, int]:
        """
        Returns a dict containing the resource IDs as keys and their rounded versions as
        values. The rounded versions are acquired via the vds_version_round action.

        :returns: a dict of resource IDs to rounded versions
        """
        action = toolkit.get_action('vds_version_round')
        return {
            resource_id: action(
                {}, {'resource_id': resource_id, 'version': self.version}
            )
            for resource_id in sorted(self.resource_ids)
        }

    @cached_property
    def counts(self) -> Dict[str, int]:
        """
        Returns a dict containing the resource IDs as keys and the number of records
        which match this query in the resource as the values.

        :returns: a dict of resource ids to counts
        """
        data_dict = {
            'query': self.query,
            'query_version': self.query_version,
            'resource_ids': self.resource_ids,
            'version': self.version,
        }
        return toolkit.get_action('vds_multi_count')({}, data_dict)['counts']

    @cached_property
    def count(self) -> int:
        """
        The total number of records matching this query.

        :returns: an integer
        """
        return sum(self.counts.values())

    @classmethod
    def create(
        cls,
        resource_ids: List[str],
        version: Optional[int] = None,
        query: Optional[dict] = None,
        query_version: Optional[str] = None,
    ) -> 'Query':
        """
        Creates a Query object using the given parameters. The resource_ids are the only
        required parameters, everything else is optional and will be defaulted to
        sensible values if needed.

        :param resource_ids: the resource IDs
        :param version: the version to query at (if missing, defaults to now)
        :param query: the query to run (if missing, defaults to any empty query)
        :param query_version: the version of the query (if missing, defaults to the
            latest query schema version)
        :returns: a Query object
        """
        invalid_resource_ids = find_invalid_resources(resource_ids)
        if invalid_resource_ids:
            # not all of them were public/active
            raise toolkit.ValidationError(
                f'Some of the resources requested are private or not active, DOIs can '
                f'only be created using public, active resources. Invalid resources: '
                f'{", ".format(invalid_resource_ids)}'
            )

        # sort them to ensure comparisons work consistently
        resource_ids = sorted(resource_ids)
        # default the version to now if not provided
        version = version if version is not None else int(time.time() * 1000)
        query = query or {}
        query_version = query_version or toolkit.get_action('vds_schema_latest')({}, {})

        return cls(resource_ids, version, query, query_version)

    @classmethod
    def create_from_download_request(cls, download_request):
        """
        Given a download request from the vds, turn it into our representation of a
        query.

        :param download_request: a DownloadRequest object from vds
        """
        return Query.create(
            download_request.core_record.resource_ids_and_versions,
            download_request.core_record.get_version(),
            download_request.core_record.query,
            download_request.core_record.query_version,
        )
