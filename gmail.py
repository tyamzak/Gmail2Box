from __future__ import print_function
import imp
from mimetypes import init
from msilib.schema import Class

import os.path
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# class GmailItem:
#     def __init__(self):
#         self.id = ""
#         self.message = ""

class GmailAPI:
    # If modifying these scopes, delete the file token.json.


    def __init__(self,):
        """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        self.creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=self.creds)
    def get_labels_from_name(self, labelname, datefrom, dateto):

        try:
            # Call the Gmail API
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            if not labels:
                print('No labels found.')
                return
            print('Labels:')
            for label in labels:
                
                if label['name'] == labelname:
                    print(label['name'])
                    return label['id']

        except HttpError as error:
            # TODO(developer) - Handle errors from gmail API.
            print(f'An error occurred: {error}')

        return
    # def get_message_list(self, DateFrom, DateTo, MessageFrom, MessageTo):
    def get_message_list(self, labelname:str):

        # APIに接続
        # self.service = self.connect_gmail()
        LabelIDs = []
        LabelIDs.append(labelname)
        MessageList = []


        # メールIDの一覧を取得する(最大100件)
        messageIDlist = self.service.users().messages().list(userId="me", maxResults=100, labelIds=LabelIDs).execute()
        # 該当するメールが存在しない場合は、処理中断
        if messageIDlist["resultSizeEstimate"] == 0:
            print("Message is not found")
            return MessageList
        # メッセージIDを元に、メールの詳細情報を取得
        for message in messageIDlist["messages"]:
            row = {}
            row["ID"] = message["id"]
            MessageDetail = self.service.users().messages().get(userId="me", id=message["id"]).execute()
                    # Such as text/plain
            if 'data' in MessageDetail['payload']['body']:
                b64_message = MessageDetail['payload']['body']['data']
            # Such as text/html
            elif MessageDetail['payload']['parts'] is not None:
                b64_message = MessageDetail['payload']['parts'][0]['body']['data']
            message = self.base64_decode(b64_message)
            row['message'] = message


            MessageList.append(row)

        return MessageList

    def base64_decode(self,b64_message):
        message = base64.urlsafe_b64decode(
            b64_message + '=' * (-len(b64_message) % 4)).decode(encoding='utf-8')
        return message
    
    def apply_labels_to_massage_list(self,removelabel,applylabel,MessageList):
        for message in MessageList:
            message["id"]
        self.service.users().messages().modify(id=message["id"],addLabelIds=applylabel,removeLabelIds=removelabel)
        return True

def main():
    import json
    import os

    with open('config.json','r',encoding='utf8') as f:
        js = json.load(f)
        LABEL_BEFRORE = js["LABEL_BEFORE"]
        LABEL_AFTER = js["LABEL_AFTER"]
        ROOT_FOLDER_NAME = js["ROOT_FOLDER_NAME"]
        CHANNEL_FOLDER_NAME = js["CHANNEL_FOLDER_NAME"]
    api = GmailAPI()
    labelid = api.get_labels_from_name('Boxアップロード待ち','2022-07-28','2022-07-29')
    lis = api.get_message_list(labelid)

    import boxmodule
    boxmodule.make_workflow_csv(lis,)

    res = api.apply_labels_to_massage_list()
    print('test')

if __name__ == '__main__':
    main()