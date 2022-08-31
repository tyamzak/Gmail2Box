from boxsdk import JWTAuth, Client
from logging import getLogger, StreamHandler, DEBUG
import logging
import json
import os

with open('config.json','r',encoding='utf8') as f:
    js = json.load(f)
    GMAIL_IRAISYO_STR = js["GMAIL_IRAISYO_STR"]
    BOX_USER_ID = js["BOX_USER_ID"]
    ROOT_FOLDER_NAME = js["ROOT_FOLDER_NAME"]
    CHANNEL_FOLDER_NAME = js["CHANNEL_FOLDER_NAME"]

################BOXJWTクライアントを作成する#########################################jwt
# auth = JWTAuth.from_settings_file(r'909811339_24cvqapp_config.json')
auth = JWTAuth.from_settings_file(r'box_jwt_auth_config.json')

client = Client(auth)
service_account = client.user().get()

#別のユーザーとして処理を実行する
user_to_impersonate = client.user(user_id=BOX_USER_ID)
user_client = client.as_user(user_to_impersonate)

##################################################################################

def get_tmp_folder():
    SAVEFOLDER = "/tmp"
    import platform
    pf = platform.system()
    if pf == 'Windows':
        if not os.path.exists("save_folder"):
            os.mkdir("save_folder")
        SAVEFOLDER = 'save_folder'
    elif pf == 'Darwin':
        SAVEFOLDER = "/tmp"
    elif pf == 'Linux':
        SAVEFOLDER = "/tmp"
    return SAVEFOLDER

def find_and_create_folder(parent_folder_id:str, child_name:str, bl_folder_create=True) -> str:

    """_summary_
    フォルダの作成(親フォルダid:str,子フォルダ名:str) -> str
    特定の名前のフォルダがあるかどうかの確認
    なかったらフォルダを作成してfolder idを返す
    bl_folder_createがFalseの場合、なかったらFalseを返す

    Args:
        parent_folder_id (str): _Parent's Box folder id_
        child_name (str): _Child's Box folder name_
        bl_folder_create: create folder in case not exist
    Returns:
        str: folder id or False
    """

    items = user_client.folder(folder_id=parent_folder_id).get_items()
    for item in items:
        if (item.name == child_name) and (item.type == "folder"):
            print(f'{item.type.capitalize()} {item.id} named "{item.name} was found"')
            return item.id

    #フォルダが無かった場合

    if bl_folder_create:
        subfolder = user_client.folder(parent_folder_id).create_subfolder(child_name)
        print(f'Created subfolder with ID {subfolder.id}')
        return subfolder.id
    else:
        return False


def get_items_from_box_folder(channel_folder_name:str,date_folder_name:str,root_folder_name:str, bl_folder_create:bool=True)->dict:
    """グローバル変数のbox_itemsを更新していく
        BOX内にroot-チャンネル名-日付-(アイテム)というフォルダ構造を作成し、
        既に存在する場合は、最下層フォルダ内のファイル情報を格納する
    Args:
        channel_folder_name (str): Slackのチャンネル名のフォルダ
        date_folder_name (str, optional): 最下層の日付フォルダの名前. Defaults to "".
        root_folder_name (str, optional): ルートフォルダの名前. Defaults to 'SlackUpload'.
        bl_folder_create (bool, optional): フォルダが存在しなかった場合に、フォルダを作成するかどうか
    Returns:
        dict: box_itemsを返す
    """
    global box_items
    global DATEFOLDERNAME
    if not date_folder_name:
        date_folder_name = DATEFOLDERNAME

    #保存用の最上位フォルダ
    if not root_folder_name in box_items.keys():
        id_slackupload = find_and_create_folder(0,root_folder_name,bl_folder_create)
        if id_slackupload:
            box_items[root_folder_name] = {"id":id_slackupload, "items" : {}}

    if not channel_folder_name in box_items[root_folder_name]["items"].keys():
        id_channelname = find_and_create_folder(box_items[root_folder_name]["id"] ,channel_folder_name,bl_folder_create)
        if id_channelname:
            box_items[root_folder_name]["items"][channel_folder_name] = {"id":id_channelname, "items" : {}}

    if not date_folder_name in box_items[root_folder_name]["items"][channel_folder_name]["items"].keys():
        id_date = find_and_create_folder(box_items[root_folder_name]["items"][channel_folder_name]["id"],date_folder_name,bl_folder_create)
        if id_date:
            box_items[root_folder_name]["items"][channel_folder_name]["items"][date_folder_name] = {"id":id_date, "items" : {}}

    #フォルダ内アイテムを格納

    try:
        folder_items = user_client.folder(folder_id=box_items[root_folder_name]["items"][channel_folder_name]["items"][date_folder_name]["id"]).get_items()
        if folder_items:
            for item in folder_items:
                print(f'{item.type.capitalize()} {item.id} is named "{item.name}"')
                box_items[root_folder_name]["items"][channel_folder_name]["items"][date_folder_name]["items"][item.name] = item.id

        return box_items
    except Exception as e:
        print(e.message)
        return False

def make_workflow_csv(gmail_messages, TS_YESTERDAY,TS_TODAY):
   
    #依頼書の格納リスト

    iraisyolist = []
    # if not SLACK_IRAISYO_STR:
    #     SLACK_IRAISYO_STR = '*依頼書*を送信しました'


    #フィードバックの格納リスト
    feedbacklist = []
    #フィードバック認識する文字列
    # if not SLACK_FEEDBACK_STR:
    #     SLACK_FEEDBACK_STR = '*フィードバック*を送信しました' 

    for message in gmail_messages:

        if GMAIL_IRAISYO_STR in message['text']:
            #認識文字列の検索　=> 項目検索中　=>　項目の値取得中　=>　項目検索中
            state = 0
            key = ''
            value = ''
            dictforiraicsv = dict()

            #項目の取得
            for line in message['text'].split("/r"):
                #認識文字列の検索
                if state == 0:
                    if GMAIL_IRAISYO_STR in line:
                        state = 1
                #項目検索中
                elif state == 1:
                    if ':' in line:
                        string_splitted = line.split(':')
                        key = line[0]
                        dictforiraicsv[key] =line[1]
                        state = 2
                #項目の値取得中
                elif state == 2:
                    if line != '':
                        dictforiraicsv[key] = dictforiraicsv[key] + line
                    # else:
                        key = ''
                        value = ''
                        state = 1
            iraisyolist.append(dictforiraicsv)


    #iraisyolistもしくはfeedbacklistが空だった場合は終了する
    if not iraisyolist:
        return False

    import pandas as pd

    #channel_idからchannel_folder_nameを作成する

    #TS_YESTERDAYのタイムスタンプからdatefoldernameを作成する
    import datetime
    t_delta = datetime.timedelta(hours=9)
    JST = datetime.timezone(t_delta, 'JST')
    filedate = datetime.datetime.fromtimestamp(TS_YESTERDAY,tz=JST)
    date_folder_name = datetime.datetime(filedate.year,filedate.month,filedate.day,0,0,0,tzinfo=JST).strftime('%Y%m%d')

    if not box_items:
        box_items = get_items_from_box_folder(channel_folder_name=CHANNEL_FOLDER_NAME,date_folder_name=date_folder_name,root_folder_name=ROOT_FOLDER_NAME)


    if not CHANNEL_FOLDER_NAME in box_items[ROOT_FOLDER_NAME]["items"].keys():
        box_items = get_items_from_box_folder(channel_folder_name=CHANNEL_FOLDER_NAME,date_folder_name=date_folder_name,root_folder_name=ROOT_FOLDER_NAME)


    #date_folder_nameの存在確認を行う
    if not date_folder_name in box_items[ROOT_FOLDER_NAME]["items"][CHANNEL_FOLDER_NAME]["items"].keys():
        #存在しなければ、取得もしくは作成を行う
        box_items = get_items_from_box_folder(channel_folder_name=CHANNEL_FOLDER_NAME,date_folder_name=date_folder_name,root_folder_name=ROOT_FOLDER_NAME)



    id_datefolder = box_items['SlackUpload']['items'][CHANNEL_FOLDER_NAME]['items'][date_folder_name]['id']

    #TODO ファイルの存在確認を行う
    
    if not "iraisyo.csv" in box_items[ROOT_FOLDER_NAME]['items'][CHANNEL_FOLDER_NAME]['items'][date_folder_name]['items'].keys():
        # Google Cloud Function用
        if iraisyolist:
            ircsv = pd.DataFrame(iraisyolist)
            ircsv.to_csv(get_tmp_folder() + '/' + 'iraisyo.csv',index=False, header=True)
            new_file = user_client.folder(folder_id=id_datefolder).upload(get_tmp_folder() + '/' + 'iraisyo.csv')
            print(f'File "{new_file.name}" uploaded to Box with file ID {new_file.id}')

    return True