import socket

from ckan.lib import mailer

# TODO: put this in the config/interface so that it can be overridden
# TODO: add html version of the body
default_save_body = '''
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
        mailer.mail_recipient(
            recipient_email=email_address,
            recipient_name='DOI Requester',
            subject='Query DOI created',
            body=default_save_body.format(doi.doi),
        )
        return True
    except (mailer.MailerException, socket.error):
        # the error will be logged automatically by CKAN's mailing functions
        return False
