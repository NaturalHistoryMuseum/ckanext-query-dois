#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

from ckan import model

from ckan.lib.cli import CkanCommand
from ckanext.query_dois.model import query_doi_table, query_doi_stat_table


class QueryDOIsInitDBCommand(CkanCommand):
    '''
    Creates the `query_doi` and `query_doi_stat` tables used by this extension.

    paster --plugin=ckanext-query-dois initdb -c /etc/ckan/default/development.ini
    '''

    summary = __doc__.split(u'\n')[0]
    usage = __doc__

    def command(self):
        self._load_config()
        # create the 2 tables if they don't already exist
        for table in (query_doi_table, query_doi_stat_table):
            if not table.exists(model.meta.engine):
                table.create(model.meta.engine)
