#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import logging
import random
import string
from ckan import model
from ckan.common import asbool
from ckan.plugins import toolkit
from datacite import DataCiteMDSClient, schema41
from datacite.errors import DataCiteError, DataCiteNotFoundError
from datetime import datetime

from .utils import get_resource_and_package, get_authors, get_resource_counts
from ..model import QueryDOI

log = logging.getLogger(__name__)

# this is a test prefix available for all minters to use for testing purposes
TEST_PREFIX = '10.5072'


def is_test_mode():
    """
    Should we use the test datacite MDS API?

    :return: True if we should, False if not. Defaults to True.
    """
    return asbool(toolkit.config.get('ckanext.query_dois.test_mode', True))


def get_prefix():
    """
    Gets the prefix to use for the DOIs we mint.

    :return: the prefix to use for the new DOIs
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

    :return: a DataCite client object
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
    :return: the full, unique DOI
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


def find_existing_doi(resources_and_versions, query_hash, query_version=None):
    """
    Returns a QueryDOI object representing the same search, or returns None if one
    doesn't exist.

    :param resources_and_versions: the resource ids being queried mapped to the versions they're
                                   being queried at
    :param query_hash: the hash of the query
    :param query_version: the query version
    :return: a QueryDOI object or None
    """
    return (
        model.Session.query(QueryDOI)
        .filter(
            QueryDOI.resources_and_versions == resources_and_versions,
            QueryDOI.query_hash == query_hash,
            QueryDOI.query_version == query_version,
        )
        .first()
    )


def create_doi_on_datacite(client, doi, authors, timestamp, count):
    """
    Mints the given DOI on datacite using the client.

    :param client: the MDS datacite client
    :param doi: the doi (full, prefix and suffix)
    :param authors: the authors to associate with the DOI
    :param timestamp: the datetime when the DOI was created
    :param count: the number of records contained in the DOI's data
    """
    # create the data for datacite
    data = {
        'identifier': {
            'identifier': doi,
            'identifierType': 'DOI',
        },
        'creators': [{'creatorName': author} for author in authors],
        'titles': [
            {
                'title': toolkit.config.get('ckanext.query_dois.doi_title').format(
                    count=count
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
    doi,
    query,
    query_hash,
    resources_and_versions,
    timestamp,
    record_count,
    requested_version=None,
    query_version=None,
    resource_counts=None,
):
    """
    Inserts the database row for the query DOI.

    :param doi: the doi (full, prefix and suffix)
    :param query: the query dict
    :param query_hash: the query hash
    :param resources_and_versions: the resource ids mapped to their rounded versions (as a dict)
    :param timestamp: the datetime the DOI was created
    :param record_count: the number of records contained in the DOI's data
    :param requested_version: the version requested by the user, if provided
    :param query_version: the query version, if provided
    :param resource_counts: the resource counts, if provided
    :return: the QueryDOI object
    """
    query_doi = QueryDOI(
        doi=doi,
        resources_and_versions=resources_and_versions,
        timestamp=timestamp,
        query=query,
        query_hash=query_hash,
        requested_version=requested_version,
        count=record_count,
        query_version=query_version,
        resource_counts=resource_counts,
    )
    query_doi.save()
    return query_doi


def mint_doi(resource_ids, datastore_query):
    """
    Mint a DOI on datacite using their API and create a new QueryDOI object, saving it
    to the database. If we already have a query which would produce identical data to
    the one passed then we return the existing QueryDOI object and don't mint or insert
    anything.

    :param resource_ids: a list or resource ids against which the query should be run. Note that as
                         this extension doesn't support multi-resource search yet an exception will
                         be thrown if the length of this list isn't 1.
    :param datastore_query: the DatastoreQuery object containing the query information
    :return: a boolean indicating whether a new DOI was minted and the QueryDOI object representing
             the query's DOI
    """
    # currently we only deal with single resource searches
    if len(resource_ids) != 1:
        raise NotImplemented(
            "This plugin currently doesn't support multi-resource searches"
        )
    resource_id = resource_ids[0]
    rounded_version = datastore_query.get_rounded_version(resource_id)
    resources_and_versions = {resource_id: rounded_version}

    existing_doi = find_existing_doi(resources_and_versions, datastore_query.query_hash)
    if existing_doi is not None:
        return False, existing_doi

    # collect up some details we're going to need to mint the DOI
    timestamp = datetime.now()
    resource, package = get_resource_and_package(resource_id)
    record_count = datastore_query.get_count(resource_id)
    client = get_client()

    # generate a new DOI to store this query against
    doi = generate_doi(client)
    create_doi_on_datacite(client, doi, [package['author']], timestamp, record_count)
    query_doi = create_database_entry(
        doi,
        datastore_query.query,
        datastore_query.query_hash,
        resources_and_versions,
        timestamp,
        record_count,
        requested_version=datastore_query.requested_version,
    )
    return True, query_doi


def mint_multisearch_doi(query, query_version, resource_ids_and_versions):
    """
    Mint a DOI on datacite using their API and create a new QueryDOI object, saving it
    to the database. If we already have a query which would produce identical data to
    the one passed then we return the existing QueryDOI object and don't mint or insert
    anything.

    This function handles DOIs created for the versioned datastore's multisearch action.

    :param query: the query dict
    :param query_version: the query schema version
    :param resource_ids_and_versions: a dict of resource ids -> versions
    :return: a boolean indicating whether a new DOI was minted and the QueryDOI object representing
             the query's DOI
    """
    # first off, ask the versioned datastore extension to create a hash of the query
    hash_data_dict = dict(query=query, query_version=query_version)
    query_hash = toolkit.get_action('datastore_hash_query')({}, hash_data_dict)

    # now check if there are any dois already for this query
    existing_doi = find_existing_doi(
        resource_ids_and_versions, query_hash, query_version
    )
    if existing_doi is not None:
        return False, existing_doi

    # collect up some details we're going to need to mint the DOI
    timestamp = datetime.now()
    authors = get_authors(resource_ids_and_versions.keys())
    # find out how many records match the query
    search_data_dict = {
        'query': query,
        'query_version': query_version,
        'resource_ids_and_versions': resource_ids_and_versions,
        'size': 0,
    }
    record_count = toolkit.get_action('datastore_multisearch')({}, search_data_dict)[
        'total'
    ]
    # find out how many records come from each resource
    resource_counts = get_resource_counts(
        query, query_version, resource_ids_and_versions
    )
    # the list call is used here so that we can modify the resource_ids_and_versions dict as we
    # iterate over it without causing an error
    for resource_id in list(resource_ids_and_versions.keys()):
        if resource_counts[resource_id] == 0:
            del resource_ids_and_versions[resource_id]
            del resource_counts[resource_id]

    if not resource_ids_and_versions:
        raise toolkit.ValidationError(
            'The DOI must be associated with at least one record'
        )

    # generate a new DOI to store this query against
    client = get_client()
    doi = generate_doi(client)
    create_doi_on_datacite(client, doi, authors, timestamp, record_count)
    query_doi = create_database_entry(
        doi,
        query,
        query_hash,
        resource_ids_and_versions,
        timestamp,
        record_count,
        query_version=query_version,
        resource_counts=resource_counts,
    )
    return True, query_doi
