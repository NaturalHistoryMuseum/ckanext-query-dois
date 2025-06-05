#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import logging

from ckan import plugins
from ckan.plugins import toolkit

from . import cli, helpers, routes
from .lib.doi import find_existing_doi, mint_multisearch_doi
from .lib.query import Query
from .lib.stats import DOWNLOAD_ACTION, record_stat
from .logic import action, auth

log = logging.getLogger(__name__)


class QueryDOIsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IBlueprint, inherit=True)
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IClick)
    # if the versioned datastore downloader is available, we have a hook for it
    try:
        from ckanext.versioned_datastore.interfaces import IVersionedDatastoreDownloads

        plugins.implements(IVersionedDatastoreDownloads, inherit=True)
        versioned_datastore_available = True
    except ImportError:
        versioned_datastore_available = False

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
    def download_after_init(self, request):
        try:
            query = Query.create_from_download_request(request)
            # mint the DOI on datacite if necessary
            mint_multisearch_doi(query)
        except toolkit.ValidationError:
            log.warning(
                'Could not create DOI for download, it contains private resources'
            )
        except:
            # if anything unexpected goes wrong we don't want to stop the download from
            # completing; just log the error and move on
            log.error('Failed to mint/retrieve DOI', exc_info=True)

    def download_modify_notifier_template_context(self, request, context):
        try:
            query = Query.create_from_download_request(request)
            # if a DOI can be created it should already have been created in
            # download_after_init
            doi = find_existing_doi(query)
            if doi:
                # update the context with the doi
                context['doi'] = doi.doi
        except:
            # if anything goes wrong we don't want to stop the download; just log the
            # error and move on
            log.error('Failed to retrieve DOI', exc_info=True)

        # always return the context
        return context

    def download_modify_manifest(self, manifest, request):
        try:
            query = Query.create_from_download_request(request)
            # if a DOI can be created it should already have been created in
            # download_after_init
            doi = find_existing_doi(query)
            if doi:
                # add the doi to the manifest
                manifest['query-doi'] = doi.doi
        except:
            # if anything goes wrong we don't want to stop the download from completing;
            # just log the error and move on
            log.error('Failed to retrieve DOI', exc_info=True)

        # always return the manifest
        return manifest

    def download_after_run(self, request):
        try:
            query = Query.create_from_download_request(request)
            # if a DOI can be created it should already have been created in
            # download_modify_manifest
            doi = find_existing_doi(query)
            if doi and request.state == 'complete':
                # record a download stat against the DOI
                record_stat(doi, DOWNLOAD_ACTION, identifier=request.id)
        except:
            # just log the error and move on
            log.error('Failed to retrieve DOI and/or create stats', exc_info=True)

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
            'get_doi_count': helpers.get_doi_count,
            'versioned_datastore_available': self.versioned_datastore_available,
        }
