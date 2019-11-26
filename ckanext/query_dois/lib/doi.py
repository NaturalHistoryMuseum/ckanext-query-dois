#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import logging
import random
import string

from ckanext.query_dois.lib.utils import get_resource_and_package
from ckanext.query_dois.model import QueryDOI
from datacite import DataCiteMDSClient, schema41
from datacite.errors import DataCiteError, DataCiteNotFoundError
from datetime import datetime
from paste.deploy.converters import asbool

from ckan import model
from ckan.plugins import toolkit

log = logging.getLogger(__name__)

# this is a test prefix available for all minters to use for testing purposes
TEST_PREFIX = u'10.5072'


def is_test_mode():
    '''
    Should we use the test datacite MDS API?

    :return: True if we should, False if not. Defaults to True.
    '''
    return asbool(toolkit.config.get(u'ckanext.query_dois.test_mode', True))


def get_prefix():
    '''
    Gets the prefix to use for the DOIs we mint.

    :return: the prefix to use for the new DOIs
    '''
    prefix = toolkit.config.get(u'ckanext.query_dois.prefix')

    if prefix == None:
        raise TypeError(u'You must set the ckanext.query_dois.prefix config value')

    if prefix == TEST_PREFIX:
        raise ValueError(
            u'The test prefix ' + TEST_PREFIX + u' has been retired, use a prefix defined in your '
                                                u'datacite test account')

    return prefix


def get_client():
    '''
    Get a datacite MDS API client, configured for use.

    :return:
    '''
    kwargs = dict(username=toolkit.config.get(u'ckanext.query_dois.datacite_username'),
        password=toolkit.config.get(u'ckanext.query_dois.datacite_password'),
        prefix=get_prefix(),
        test_mode=is_test_mode(),)
    # datacite 1.0.1 isn't updated for the test prefix deprecation yet so this is a temp fix
    if is_test_mode():
        kwargs.update({u'url': u'https://mds.test.datacite.org'})
    return DataCiteMDSClient(**kwargs)


def generate_doi(client):
    '''
    Generate a new DOI which isn't currently in use. The database is checked for previous usage, as
    is Datacite itself. Use whatever value is retuned from this function quickly to avoid double
    use as this function uses no locking.

    :param client: an instance of the DataCiteMDSClient class
    :return: the full, unique DOI
    '''
    # the list of valid characters is larger than just lowercase and the digits but we don't need
    # that many options and URLs with just alphanumeric characters in them are nicer. We just use
    # lowercase characters to avoid any issues with case being ignored
    valid_characters = string.ascii_lowercase + string.digits

    attempts = 5

    while attempts > 0:
        # generate a random 8 character identifier and prepend qd. to make it easier to identify
        # DOIs from this extension
        identifier = u'qd.{}'.format(u''.join(random.choice(valid_characters) for _ in range(8)))
        # form the doi using the prefix
        doi = u'{}/{}'.format(get_prefix(), identifier)

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
            log.warn(u'Error whilst checking new DOIs with DataCite. DOI: {}, error: {}'
                     .format(doi, e.message))
            attempts -= 1
            continue

        # if we've made it this far the doi isn't in the database and it's not in datacite already
        return doi
    else:
        raise Exception(u'Failed to generate a DOI')


def find_existing_doi(resources_and_versions, query_hash):
    '''
    Returns a QueryDOI object representing the same search, or returns None if one doesn't exist.

    :param resources_and_versions: the resource ids being queried mapped to the versions they're
                                   being queried at
    :param query_hash: the hash of the query
    :return: a QueryDOI object or None
    '''
    return model.Session.query(QueryDOI) \
        .filter(QueryDOI.resources_and_versions == resources_and_versions,
                QueryDOI.query_hash == query_hash).first()


def _create_doi_on_datacite(client, doi, package, timestamp, record_count):
    '''
    Mints the given DOI on datacite using the client.

    :param client: the MDS datacite client
    :param doi: the doi (full, prefix and suffix)
    :param package: the package dict
    :param timestamp: the datetime when the DOI was created
    :param record_count: the number of records contained in the DOI's data
    '''
    # create the data for datacite
    data = {
        u'identifier': {
            u'identifier': doi,
            u'identifierType': u'DOI',
            },
        u'creators': [{
                          u'creatorName': package[u'author']
                          }],
        u'titles': [
            {
                u'title': toolkit.config.get(u'ckanext.query_dois.doi_title').format(
                    count=record_count)
                }
            ],
        u'publisher': toolkit.config.get(u'ckanext.query_dois.publisher'),
        u'publicationYear': unicode(timestamp.year),
        u'resourceType': {
            u'resourceTypeGeneral': u'Dataset'
            }
        }

    # use an assert here because the data should be valid every time, otherwise it's something the
    # developer is going to have to fix
    assert schema41.validate(data)

    # create the metadata on datacite
    client.metadata_post(schema41.tostring(data))

    # create the URL the DOI will point to, i.e. the landing page
    data_centre, identifier = doi.split(u'/')
    landing_page_url = toolkit.url_for(u'query_doi.landing_page', data_centre=data_centre,
                                       identifier=identifier)
    site = toolkit.config.get(u'ckan.site_url')
    if site[-1] == u'/':
        site = site[:-1]
    # mint the DOI
    client.doi_post(doi, site + landing_page_url)


def _create_database_entry(doi, resources_and_versions, timestamp, datastore_query, record_count):
    '''
    Inserts the database row for the query DOI.

    :param doi: the doi (full, prefix and suffix)
    :param resources_and_versions: the resource ids mapped to their rounded versions (as a dict)
    :param timestamp: the datetime the DOI was created
    :param datastore_query: the DatastoreQuery object
    :param record_count: the number of records contained in the DOI's data
    :return:
    '''
    # create database row
    query_doi = QueryDOI(
        doi=doi,
        resources_and_versions=resources_and_versions,
        timestamp=timestamp,
        query=datastore_query.query,
        query_hash=datastore_query.query_hash,
        requested_version=datastore_query.requested_version,
        count=record_count,
        )
    query_doi.save()
    return query_doi


def mint_doi(resource_ids, datastore_query):
    '''
    Mint a DOI on datacite using their API and create a new QueryDOI object, saving it to the
    database. If we already have a query which would produce identical data to the one passed then
    we return the existing QueryDOI object and don't mint or insert anything.

    :param resource_ids: a list or resource ids against which the query should be run. Note that as
                         this extension doesn't support multi-resource search yet an exception will
                         be thrown if the length of this list isn't 1.
    :param datastore_query: the DatastoreQuery object containing the query information
    :return: a boolean indicating whether a new DOI was minted and the QueryDOI object representing
             the query's DOI
    '''
    # currently we only deal with single resource searches
    if len(resource_ids) != 1:
        raise NotImplemented(u"This plugin currently doesn't support multi-resource searches")
    resource_id = resource_ids[0]
    rounded_version = datastore_query.get_rounded_version(resource_id)
    resources_and_versions = {
        resource_id: rounded_version
        }

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
    _create_doi_on_datacite(client, doi, package, timestamp, record_count)
    query_doi = _create_database_entry(doi, resources_and_versions, timestamp, datastore_query,
                                       record_count)
    return True, query_doi
