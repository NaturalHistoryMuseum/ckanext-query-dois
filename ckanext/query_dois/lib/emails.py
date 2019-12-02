import socket

from ckan.lib import mailer

# TODO: put both of these in the config/interface so that they can be overridden
default_download_body = u'''
A DOI has been created for this data: https://doi.org/{} (this may take a few hours to be active).
Please ensure you reference this DOI when citing this data.
For more information, follow the DOI link.
'''.strip()

default_save_body = u'''
Hello,

As requested, a DOI has successfully been created for your search.
The DOI will become available at https://doi.org/{}, though this can sometimes take a few hours.

Please ensure that you cite this DOI whenever you use this data! Follow the DOI link for more
details.

Best wishes,
The NHM Data Portal Bot
'''.strip()


def send_saved_search_email(email_address, doi):
    # send the DOI to the user in an email
    try:
        mailer.mail_recipient(recipient_email=email_address, recipient_name=u'DOI Requester',
                              subject=u'Query DOI created', body=default_save_body.format(doi.doi))
        return True
    except (mailer.MailerException, socket.error):
        # the error will be logged automatically by CKAN's mailing functions
        return False
