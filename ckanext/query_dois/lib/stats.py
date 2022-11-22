#!/usr/bin/env python
# encoding: utf-8
#
# This file is part of ckanext-query-dois
# Created by the Natural History Museum in London, UK

import base64
from datetime import datetime

import bcrypt
from ckanext.query_dois.model import QueryDOIStat

# action types
DOWNLOAD_ACTION = 'download'
SAVE_ACTION = 'save'


def anonymize_email(email_address):
    """
    Split the email address into it's identity and domain parts, then return the secure
    hash of the identity and the domain. Bcrypt is used to securely hash the identity,
    using the domain as the salt.

    :param email_address: the email address
    :return: a 2-tuple of the email address and the domain
    """
    if email_address is None:
        return None, None

    email_address = email_address.lower()
    # figure out the domain from the email address
    try:
        domain = email_address[email_address.index('@') + 1 :]
    except ValueError:
        # no @ found, just use the whole string
        domain = email_address

    # create a custom salt by base64 encoding the domain and then trimming the whole thing to 22
    # characters (which is bcrypt's required salt length). Note that we fill the right side of the
    # domain with dots to ensure it's at least 18 characters in length. This is necessary as we need
    # to ensure that the base64 encode result is at least 22 characters long and 18 is the minimum
    # input length necessary to create a base64 encoding result of at least 22 characters.
    salt = b'$2b$12$' + base64.b64encode(domain.zfill(18).encode('utf-8'))[:22]
    return bcrypt.hashpw(email_address.encode('utf-8'), salt), domain


def record_stat(query_doi, action, email_address):
    """
    Creates a new QueryDOIStat object and saves it to the database.

    :param query_doi: the QueryDOI object against which the stat should be stored
    :param action: the action that occurred to trigger this stat (for example: "download")
    :param email_address: the email address of the user performing the action
    :return: a new QueryDOIStat object
    """
    identifier, domain = anonymize_email(email_address)
    stat = QueryDOIStat(
        doi=query_doi.doi,
        action=action,
        domain=domain,
        identifier=identifier,
        timestamp=datetime.now(),
    )
    stat.save()
    return stat
