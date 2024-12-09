"""
This file is only necessary if you want emails from the program as well as the
saved html file.

In order to create an email sender you would need to follow the steps here
https://developers.google.com/gmail/api/quickstart/python

The credentials.json file should be placed in the same directory as this file.

Attributions:
The important parts of this file come from this thread
https://stackoverflow.com/questions/37201250/sending-email-via-gmail-python

Answer by 'sugarpines' fixes message encoding issues.
"""

import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from settings import to_email, from_email

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
CLIENT_SECRET_FILE = 'credentials.json'


def get_credentials():
    # credential_dir = os.getcwd()
    # credential_path = os.path.join(credential_dir, 'token.json')
    credential_path = 'token.json'
    creds = None

    if os.path.exists(credential_path):
        creds = Credentials.from_authorized_user_file(credential_path, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(credential_path, 'w') as token:
            token.write(creds.to_json())

    return creds


def SendMessage(sender, to, subject, msgHtml, msgPlain):
    credentials = get_credentials()
    service = build('gmail', 'v1', credentials=credentials)
    message1 = CreateMessage(sender, to, subject, msgHtml, msgPlain)
    result = SendMessageInternal(service, "me", message1)
    return result


def SendMessageInternal(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        # print('Message Id: %s' % message['id'])
        return True, message
    except HttpError as error:
        # print('An error occurred: %s' % error)
        return False, error
    return None, "Not an HttpError? This shouldn't happen."


def CreateMessage(sender, to, subject, msgHtml, msgPlain):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    msg.attach(MIMEText(msgPlain, 'plain'))
    msg.attach(MIMEText(msgHtml, 'html'))
    raw = base64.urlsafe_b64encode(msg.as_bytes())
    raw = raw.decode()
    body = {'raw': raw}
    return body


def main(message):
    to = to_email
    sender = from_email
    subject = "Arxiv Update"
    msgHtml = message
    msgPlain = message
    return SendMessage(sender, to, subject, msgHtml, msgPlain)


if __name__ == '__main__':
    main('test email')
