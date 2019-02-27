import json
import logging

from ckan import plugins
from ckanext.query_dois import helpers
from ckanext.query_dois.lib.doi import mint_doi
from ckanext.query_dois.lib.stats import record_stat, DOWNLOAD_ACTION
from ckanext.query_dois.lib.query import DatastoreQuery

log = logging.getLogger(__name__)


class QueryDOIsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    # if the ckanpackager is available, we have a hook for it
    try:
        from ckanext.ckanpackager.interfaces import ICkanPackager
        plugins.implements(ICkanPackager)
    except ImportError:
        pass

    # IRoutes
    def before_map(self, mapper):
        mapper.connect(u'query_doi_landing_page', u'/doi/{data_centre}/{identifier}',
                       controller=u'ckanext.query_dois.controllers.landing_page:LandingPageController',
                       action=u'get')
        mapper.connect(u'query_doi_stats', u'/doi/stats',
                       controller=u'ckanext.query_dois.controllers.stats:StatsController',
                       action=u'get')
        return mapper

    # IConfigurer
    def update_config(self, config):
        # add the public directory
        plugins.toolkit.add_public_directory(config, u'theme/public')
        # add templates
        plugins.toolkit.add_template_directory(config, u'theme/templates')
        # add the resource groups
        plugins.toolkit.add_resource(u'theme/public', u'ckanext-query-dois')

    # ICkanPackager
    def before_package_request(self, resource_id, package_id, packager_url, request_params):
        '''
        This is called prior to the ckanpackager plugin starting it's creation of a download,
        therefore we can use it to mint DOIs and record a stat.

        :param resource_id: the resource id of the resource that is about to be packaged
        :param package_id: the package id of the resource that is about to be packaged
        :param packager_url: the target url for this packaging request
        :param request_params: a dict of parameters that will be sent with the request
        :return: the url and the params as a tuple
        '''
        resource = plugins.toolkit.get_action(u'resource_show')({}, {u'id': resource_id})
        package = plugins.toolkit.get_action(u'package_show')({}, {u'id': package_id})
        # only handle DOIs for resources with data in the datastore and that aren't in private
        # packages
        if resource.get(u'datastore_active', False) and not package.get(u'private', True):
            try:
                # the request_params dict comes through with a lot of other parameters in it beyond
                # the query params, therefore we need to do some stripping out (otherwise the exact
                # same query will look different due to a different format choice or email address)
                allowed_keys = {u'q', u'filters', u'version'}
                data_dict = {k: v for k, v in request_params.items() if k in allowed_keys}

                # the packager converts the filters dict to JSON so we need to convert it back
                if u'filters' in data_dict:
                    data_dict[u'filters'] = json.loads(data_dict[u'filters'])

                # mint the DOI on datacite if necessary
                _minted, query_doi = mint_doi([resource_id], DatastoreQuery(data_dict=data_dict))
                # record a download stat against the DOI
                record_stat(query_doi, DOWNLOAD_ACTION, request_params[u'email'])
                # add the doi to the ckanpackager params so that it can be reported in the email
                request_params[u'doi'] = query_doi.doi
            except:
                # if anything goes wrong we don't want to stop the download from going ahead, just
                # log the error and move on
                log.error(u'Failed to mint/retrieve DOI and/or create stats', exc_info=True)

        return packager_url, request_params

    # ITemplateHelpers
    def get_helpers(self):
        return {
            u'render_filter_value': helpers.render_filter_value,
            u'get_most_recent_dois': helpers.get_most_recent_dois,
            u'get_time_ago_description': helpers.get_time_ago_description,
            u'get_landing_page_url': helpers.get_landing_page_url,
        }
