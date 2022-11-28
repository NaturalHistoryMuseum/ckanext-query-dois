#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

from ckan.plugins import toolkit
from ckanext.datastore.logic.schema import json_validator

# grab all the validator functions upfront
boolean_validator = toolkit.get_validator('boolean_validator')
ignore_missing = toolkit.get_validator('ignore_missing')
int_validator = toolkit.get_validator('int_validator')
email_validator = toolkit.get_validator('email_validator')


def list_of_strings(delimiter=','):
    """
    Creates a converter/validator function which when given a value return a list or
    raises an error if a list can't be created from the value. If the value passed in is
    a list already it is returned with no modifications, if it's a string then the
    delimiter is used to split the string and the result is returned. If the value is
    neither a list or a string then an error is raised.

    :param delimiter: the string to delimit the value on, if it's a string. Defaults to a comma
    :return: a list
    """

    def validator(value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return value.split(delimiter)
        raise toolkit.Invalid('Invalid list of strings')

    return validator


def create_doi():
    return {
        'email_address': [email_validator],
        'query': [ignore_missing, json_validator],
        'query_version': [ignore_missing, str],
        'version': [ignore_missing, int_validator],
        'resource_ids': [ignore_missing, list_of_strings()],
        'resource_ids_and_versions': [ignore_missing, json_validator],
    }
