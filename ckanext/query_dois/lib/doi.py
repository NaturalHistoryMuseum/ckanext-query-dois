#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import logging
import random
import string
from datetime import datetime
from typing import Optional, Tuple

from ckan import model
from ckan.common import asbool
from ckan.plugins import toolkit
from datacite import DataCiteMDSClient, schema41
from datacite.errors import DataCiteError, DataCiteNotFoundError

from ckanext.query_dois.lib.query import Query
from ckanext.query_dois.model import QueryDOI

log = logging.getLogger(__name__)

# this is a test prefix available for all minters to use for testing purposes
TEST_PREFIX = '10.5072'


def is_test_mode():
    """
    Should we use the test datacite MDS API?

    :returns: True if we should, False if not. Defaults to True.
    """
    return asbool(toolkit.config.get('ckanext.query_dois.test_mode', True))


def get_prefix():
    """
    Gets the prefix to use for the DOIs we mint.

    :returns: the prefix to use for the new DOIs
    """
    prefix = toolkit.config.get('ckanext.query_dois.prefix')

    if prefix is None:
        raise TypeError('You must set the ckanext.query_dois.prefix config value')

    if prefix == TEST_PREFIX:
        raise ValueError(
            f'The test prefix {TEST_PREFIX} has been retired, use a prefix defined in '
            f'your datacite test account'
        )

    return prefix


def get_client():
    """
    Get a datacite MDS API client, configured for use.

    :returns: a DataCite client object
    """
    kwargs = dict(
        username=toolkit.config.get('ckanext.query_dois.datacite_username'),
        password=toolkit.config.get('ckanext.query_dois.datacite_password'),
        prefix=get_prefix(),
        test_mode=is_test_mode(),
    )
    # datacite 1.0.1 isn't updated for the test prefix deprecation yet so this is a temp fix
    if is_test_mode():
        kwargs.update({'url': 'https://mds.test.datacite.org'})
    return DataCiteMDSClient(**kwargs)


def generate_doi(client):
    """
    Generate a new DOI which isn't currently in use. The database is checked for
    previous usage, as is Datacite itself. Use whatever value is retuned from this
    function quickly to avoid double use as this function uses no locking.

    :param client: an instance of the DataCiteMDSClient class
    :returns: the full, unique DOI
    """
    # the list of valid characters is larger than just lowercase and the digits but we don't need
    # that many options and URLs with just alphanumeric characters in them are nicer. We just use
    # lowercase characters to avoid any issues with case being ignored
    valid_characters = string.ascii_lowercase + string.digits

    attempts = 5

    while attempts > 0:
        # generate a random 8 character identifier and prepend qd. to make it easier to identify
        # DOIs from this extension
        identifier = f'qd.{"".join(random.choice(valid_characters) for _ in range(8))}'
        # form the doi using the prefix
        doi = f'{get_prefix()}/{identifier}'

        # check this doi doesn't exist in the table
        if model.Session.query(QueryDOI).filter(QueryDOI.doi == doi).count():
            continue

        # check against the datacite service
        try:
            client.metadata_get(doi)
            # if a doi is found, we need to try again
            continue
        except DataCiteNotFoundError:
            # if no doi is found, we're good!
            pass
        except DataCiteError as e:
            log.warning(
                f'Error whilst checking new DOIs with DataCite. DOI: {doi}, error: {e}'
            )
            attempts -= 1
            continue

        # if we've made it this far the doi isn't in the database and it's not in datacite already
        return doi
    else:
        raise Exception('Failed to generate a DOI')


def find_existing_doi(query: Query) -> Optional[QueryDOI]:
    """
    Returns a QueryDOI object representing the query, or returns None if one doesn't
    exist.

    :param query: a Query object
    :returns: a QueryDOI object or None
    """
    return (
        model.Session.query(QueryDOI)
        .filter(
            QueryDOI.query_hash == query.query_hash,
            QueryDOI.query_version == query.query_version,
            QueryDOI.resources_and_versions == query.resources_and_versions,
        )
        .first()
    )


def create_doi_on_datacite(
    client: DataCiteMDSClient, doi: str, timestamp: datetime, query: Query
):
    """
    Mints the given DOI on datacite using the client.

    :param client: the MDS datacite client
    :param doi: the doi (full, prefix and suffix)
    :param timestamp: the datetime when the DOI was created
    :param query: a Query object
    """
    # create the data for datacite
    data = {
        'identifier': {
            'identifier': doi,
            'identifierType': 'DOI',
        },
        'creators': [{'creatorName': author} for author in query.authors],
        'titles': [
            {
                'title': toolkit.config.get('ckanext.query_dois.doi_title').format(
                    count=query.count
                )
            }
        ],
        'publisher': toolkit.config.get('ckanext.query_dois.publisher'),
        'publicationYear': str(timestamp.year),
        'resourceType': {'resourceTypeGeneral': 'Dataset'},
    }

    # use an assert here because the data should be valid every time, otherwise it's something the
    # developer is going to have to fix
    assert schema41.validate(data)

    # create the metadata on datacite
    client.metadata_post(schema41.tostring(data))

    # create the URL the DOI will point to, i.e. the landing page
    data_centre, identifier = doi.split('/')
    landing_page_url = toolkit.url_for(
        'query_doi.landing_page', data_centre=data_centre, identifier=identifier
    )
    site = toolkit.config.get('ckan.site_url')
    if site[-1] == '/':
        site = site[:-1]
    # mint the DOI
    client.doi_post(doi, site + landing_page_url)


def create_database_entry(
    doi: str,
    query: Query,
    timestamp: datetime,
):
    """
    Inserts the database row for the query DOI.

    :param doi: the doi (full, prefix and suffix)
    :param query: the query
    :param timestamp: the datetime the DOI was created
    :returns: the QueryDOI object
    """
    query_doi = QueryDOI(
        doi=doi,
        timestamp=timestamp,
        resources_and_versions=query.resources_and_versions,
        requested_version=query.version,
        query=query.query,
        query_version=query.query_version,
        query_hash=query.query_hash,
        count=query.count,
        resource_counts=query.counts,
    )
    query_doi.save()
    return query_doi


def mint_multisearch_doi(query: Query) -> Tuple[bool, QueryDOI]:
    """
    Mint a DOI on datacite using their API and create a new QueryDOI object, saving it
    to the database. If we already have a query which would produce identical data to
    the one passed then we return the existing QueryDOI object and don't mint or insert
    anything.

    This function handles DOIs created for the versioned datastore's multisearch action.

    :param query: the query
    :returns: a boolean indicating whether a new DOI was minted and the QueryDOI object
        representing the query's DOI
    """
    # check if there are any dois already for this query
    existing_doi = find_existing_doi(query)
    if existing_doi is not None:
        return False, existing_doi

    # generate a new DOI to store this query against
    timestamp = datetime.now()
    client = get_client()
    doi = generate_doi(client)
    create_doi_on_datacite(client, doi, timestamp, query)
    query_doi = create_database_entry(doi, query, timestamp)
    return True, query_doi
