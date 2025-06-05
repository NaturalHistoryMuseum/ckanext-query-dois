#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

from ckan.plugins import toolkit

from ckanext.query_dois.lib.doi import mint_multisearch_doi
from ckanext.query_dois.lib.emails import send_saved_search_email
from ckanext.query_dois.lib.query import Query
from ckanext.query_dois.lib.stats import SAVE_ACTION, record_stat
from ckanext.query_dois.logic import schema as schema_lib


def create_doi(context, data_dict):
    """
    Creates a DOI using the given parameters and returns it.

    :param email_address: the email address of the DOI requester
    :type email_address: string
    :param query: the query to associate with the DOI
    :type query: dict
    :param query_version: the query schema version for the query
    :type query_version: string
    :param version: the version to search the data at
    :type version: int, number of milliseconds (not seconds!) since UNIX epoch
    :param resource_ids: the resource ids to search
    :type resource_ids: list of strings
    :param doi: the doi that was created (prefix/suffix)
    :type doi: string
    :param is_new: whether the doi was newly created or whether an existing DOI for the
        query parameters already existed
    :type is_new: bool
    :param email_sent: whether the email was sent successfully or not
    :type email_sent: bool
    :rtype: dict
    """
    # validate the data dict first
    schema = context.get('schema', schema_lib.create_doi())
    data_dict, errors = toolkit.navl_validate(data_dict, schema, context)
    if errors:
        raise toolkit.ValidationError(errors)

    email_address = data_dict['email_address']
    query = Query.create(
        data_dict['resource_ids'],
        data_dict.get('version'),
        data_dict.get('query'),
        data_dict.get('query_version'),
    )

    # create a new DOI or retrieve an existing one
    created, doi = mint_multisearch_doi(query)
    # record a stat for this action
    record_stat(doi, SAVE_ACTION, email_address)
    # send the email to the requesting user
    email_sent = send_saved_search_email(email_address, doi)

    return {'is_new': created, 'doi': doi.doi, 'email_sent': email_sent}
