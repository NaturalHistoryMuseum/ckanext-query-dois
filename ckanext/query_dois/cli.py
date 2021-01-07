#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK
import click

from ckan import model
from .model import query_doi_table, query_doi_stat_table


def get_commands():
    return [query_dois]


@click.group()
def query_dois():
    '''
    Query DOIs CLI.
    '''
    pass


@query_dois.command(name=u'initdb')
def init_db():
    '''
    Creates the `query_doi` and `query_doi_stat` tables used by this extension.
    '''
    # create the 2 tables if they don't already exist
    for table in (query_doi_table, query_doi_stat_table):
        if not table.exists(model.meta.engine):
            table.create(model.meta.engine)
            click.secho(u'Created "{}" table'.format(table), fg=u'green')
        else:
            click.secho(u'Table "{}" already exists, skipping...'.format(table), fg=u'green')
