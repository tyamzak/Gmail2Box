from __future__ import print_function


import os.path
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def get_message_list(message_json, dtfrom,dtto):
    import datetime

    MessageList = []

    # 該当するメールが存在しない場合は、処理中断
    if message_json == []:
        print("Message is not found")
        return False
    # メッセージIDを元に、メールの詳細情報を取得
    for message in message_json:

        #日付が該当するかチェック
        from dateutil.parser import parse
        from dateutil.tz import gettz
        msgdate = parse(message['date'])
        if dtfrom <= msgdate < dtto:


            row = {}
            row["ID"] = message["id"]
            # if 'data' in MessageDetail['payload']['body']:
            #     b64_message = MessageDetail['payload']['body']['data']
            # # Such as text/html
            # elif MessageDetail['payload']['parts'] is not None:
            #     b64_message = MessageDetail['payload']['parts'][0]['body']['data']
            # message = self.base64_decode(b64_message)
            row['message'] = message['body']

            MessageList.append(row)

    return MessageList






# from crypt import methods

import functions_framework

@functions_framework.http
def hello_get(request):
# def main(): # ローカル用途    
    import json
    import os
    reqjs = request.json
    print('request received')
    with open('config.json','r',encoding='utf8') as f:
        js = json.load(f)
        LABEL_BEFORE = js["LABEL_BEFORE"]
        LABEL_UNTIL = js["LABEL_UNTIL"]

        #TS_YESTERDAYのタイムスタンプからdatefoldernameを作成する
    import datetime
    t_delta = datetime.timedelta(hours=9)
    JST = datetime.timezone(t_delta, 'JST')

    past_index = 0
    
    # api = GmailAPI()
    # labelid_before = api.get_labels_from_name(LABEL_BEFORE)
    # labelid_until = api.get_labels_from_name(LABEL_UNTIL)
    
    #昨日以降分を実施 ワークフローの集計も実施していく
    import boxmodule
    while True:
        now = datetime.datetime.now(JST)
        dt_to = datetime.datetime(now.year,now.month,now.day,0,0,0,tzinfo=JST) - datetime.timedelta(days=past_index)
        dt_from  = datetime.datetime(now.year,now.month,now.day,0,0,0,tzinfo=JST) - datetime.timedelta(days= 1 + past_index)
        date_folder_name = datetime.datetime(dt_from.year,dt_from.month,dt_from.day,0,0,0,tzinfo=JST).strftime('%Y%m%d')
        # str_to = dt_to.strftime('%Y-%m-%d')
        # str_from = dt_from.strftime('%Y-%m-%d')

        # ここでHTTPリクエストでもらったデータを使用する

        lis = get_message_list(reqjs,dt_from,dt_to)
        if lis:
            print(date_folder_name)
            print(lis)
            boxmodule.make_workflow_csv(lis,dt_from.timestamp())

        # res = api.apply_labels_to_massage_list(labelid_before,labelid_until,lis)
        past_index += 1
        if (datetime.datetime(now.year,now.month,now.day,0,0,0,tzinfo=JST) - datetime.timedelta(days= 1 + past_index)) < \
            datetime.datetime(2022,7,28,0,0,0,tzinfo=JST):
            print('all days are completed')
            return "done"