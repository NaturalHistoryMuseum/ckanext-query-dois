#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import json
import logging
from contextlib import suppress

from ckan import plugins

from . import helpers, routes, cli
from .lib.doi import mint_doi, mint_multisearch_doi, find_existing_doi
from .lib.query import DatastoreQuery
from .lib.stats import DOWNLOAD_ACTION, record_stat
from .logic import auth, action
from .logic.utils import extract_resource_ids_and_versions

log = logging.getLogger(__name__)


class QueryDOIsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IBlueprint, inherit=True)
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IClick)
    # if the ckanpackager is available, we have a hook for it
    with suppress(ImportError):
        from ckanext.ckanpackager.interfaces import ICkanPackager

        plugins.implements(ICkanPackager)
    # if the versioned datastore downloader is available, we have a hook for it
    with suppress(ImportError):
        from ckanext.versioned_datastore.interfaces import IVersionedDatastoreDownloads

        plugins.implements(IVersionedDatastoreDownloads, inherit=True)

    # IBlueprint
    def get_blueprint(self):
        return routes.blueprints

    # IClick
    def get_commands(self):
        return cli.get_commands()

    # IAuthFunctions
    def get_auth_functions(self):
        return {
            'create_doi': auth.create_doi,
        }

    # IActions
    def get_actions(self):
        return {
            'create_doi': action.create_doi,
        }

    # IConfigurer
    def update_config(self, config):
        # add templates
        plugins.toolkit.add_template_directory(config, 'theme/templates')
        # add the resource groups
        plugins.toolkit.add_resource('theme/assets', 'ckanext-query-dois')

    # IVersionedDatastoreDownloads
    def download_modify_email_template_context(self, request, context):
        try:
            # if a DOI can be created it should already have been created in download_before_write
            doi = find_existing_doi(
                request.resource_ids_and_versions,
                request.query_hash,
                request.query_version,
            )

            # update the context with the doi
            context['doi'] = doi.doi

            # record a download stat against the DOI
            record_stat(doi, DOWNLOAD_ACTION, request.email_address)
        except:
            # if anything goes wrong we don't want to stop the download from going ahead, just
            # log the error and move on
            log.error('Failed to retrieve DOI and/or create stats', exc_info=True)

        # always return the context
        return context

    def download_before_write(self, request):
        try:
            # check to see if the download is something we can stick a DOI on (this will throw a
            # validation error if any of the resources aren't valid for DOI-ing
            extract_resource_ids_and_versions(
                req_resource_ids_and_versions=request.resource_ids_and_versions
            )

            # mint the DOI on datacite if necessary
            created, doi = mint_multisearch_doi(
                request.query, request.query_version, request.resource_ids_and_versions
            )
        except:
            # if anything goes wrong we don't want to stop the download from going ahead, just
            # log the error and move on
            log.error('Failed to mint/retrieve DOI', exc_info=True)

        # always return the request
        return request

    # ICkanPackager
    def before_package_request(
        self, resource_id, package_id, packager_url, request_params
    ):
        """
        This is called prior to the ckanpackager plugin starting it's creation of a
        download, therefore we can use it to mint DOIs and record a stat.

        :param resource_id: the resource id of the resource that is about to be packaged
        :param package_id: the package id of the resource that is about to be packaged
        :param packager_url: the target url for this packaging request
        :param request_params: a dict of parameters that will be sent with the request
        :return: the url and the params as a tuple
        """
        resource = plugins.toolkit.get_action('resource_show')({}, {'id': resource_id})
        package = plugins.toolkit.get_action('package_show')({}, {'id': package_id})
        # only handle DOIs for resources with data in the datastore and that aren't in private
        # packages
        if resource.get('datastore_active', False) and not package.get('private', True):
            try:
                # the request_params dict comes through with a lot of other parameters in it beyond
                # the query params, therefore we need to do some stripping out (otherwise the exact
                # same query will look different due to a different format choice or email address)
                allowed_keys = {'q', 'filters', 'version'}
                data_dict = {
                    k: v for k, v in request_params.items() if k in allowed_keys
                }

                # the packager converts the filters dict to JSON so we need to convert it back
                if 'filters' in data_dict:
                    data_dict['filters'] = json.loads(data_dict['filters'])

                # mint the DOI on datacite if necessary
                _minted, query_doi = mint_doi(
                    [resource_id], DatastoreQuery(data_dict=data_dict)
                )
                # record a download stat against the DOI
                record_stat(query_doi, DOWNLOAD_ACTION, request_params['email'])
                # add the doi to the ckanpackager params so that it can be reported in the email
                request_params['doi'] = query_doi.doi
            except:
                # if anything goes wrong we don't want to stop the download from going ahead, just
                # log the error and move on
                log.error(
                    'Failed to mint/retrieve DOI and/or create stats', exc_info=True
                )

        return packager_url, request_params

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'render_filter_value': helpers.render_filter_value,
            'get_most_recent_dois': helpers.get_most_recent_dois,
            'get_time_ago_description': helpers.get_time_ago_description,
            'get_landing_page_url': helpers.get_landing_page_url,
            'create_citation_text': helpers.create_citation_text,
            'create_multisearch_citation_text': helpers.create_multisearch_citation_text,
            'pretty_print_query': helpers.pretty_print_query,
        }
