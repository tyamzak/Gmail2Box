import logging
import os
import time
import pprint
import sys
from boxsdk import JWTAuth, Client

from logging import getLogger, StreamHandler, DEBUG
import datetime
import json
STARTTIME = time.time()
COMPLETED_ID = ""
COMPLETED_DATE_SET = set()

with open('config.json','r',encoding='utf8') as f:
    js = json.load(f)
    # slack_token = js["SLACK_TOKEN"]
    BOX_USER_ID = js["BOX_USER_ID"]
    SLACK_CHANNEL_NAMES = js["SLACK_CHANNEL_NAMES"]
    TIMEOUT = float(js["TIMEOUT"])




logging.basicConfig()
logger = getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
t_delta = datetime.timedelta(hours=9)
JST = datetime.timezone(t_delta, 'JST')
now = datetime.datetime.now(JST)
TS_TODAY = datetime.datetime(now.year,now.month,now.day,0,0,0,tzinfo=JST).timestamp()
# TS_YESTERDAY = datetime.datetime(now.year,now.month,now.day - 1,0,0,0,tzinfo=JST).timestamp()
#デフォルトは昨日分アップロードなので、昨日分のフォルダを作る
# DATEFOLDERNAME = datetime.datetime(now.year,now.month,now.day - 1,0,0,0,tzinfo=JST).strftime('%Y%m%d')
ROOT_FOLDER_NAME = 'SlackUpload'

# グローバル　Dict構造　フォルダ名 : {"id":フォルダID, "items" : [] } "itemsの下層に別フォルダが入る"
box_items = dict()

################BOXJWTクライアントを作成する#########################################jwt
# auth = JWTAuth.from_settings_file(r'909811339_24cvqapp_config.json')
auth = JWTAuth.from_settings_file(r'box_jwt_auth_config.json')

client = Client(auth)
service_account = client.user().get()
logger.info('Box Service Account user ID is {0}'.format(service_account.id))
#別のユーザーとして処理を実行する
user_to_impersonate = client.user(user_id=BOX_USER_ID)
user_client = client.as_user(user_to_impersonate)





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
            # print(f'{item.type.capitalize()} {item.id} named "{item.name} was found"')
            return item.id

    #フォルダが無かった場合

    if bl_folder_create:
        subfolder = user_client.folder(parent_folder_id).create_subfolder(child_name)
        # print(f'Created subfolder with ID {subfolder.id}')
        return subfolder.id
    else:
        return False


###################################boxファイルのリストアップ##################################
def get_items_from_box_folder(channel_folder_name:str,date_folder_name:str="",root_folder_name:str='SlackUpload', bl_folder_create:bool=True)->dict:
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
                # print(f'{item.type.capitalize()} {item.id} is named "{item.name}"')
                box_items[root_folder_name]["items"][channel_folder_name]["items"][date_folder_name]["items"][item.name] = item.id

        return box_items
    except Exception as e:
        # print(type(e))
        # print(e)
        return box_items

def folder_delete(folder_id):
    res = user_client.folder(folder_id).delete()
    if res:
        print('deleted')
    else:
        print('failed')


def main():

    # #昨日以前分を実施
    past_index = 0
    while True:

        for cnlname in SLACK_CHANNEL_NAMES:
            DATEFOLDERNAME = (datetime.datetime(now.year,now.month,now.day,0,0,0,tzinfo=JST) - datetime.timedelta(days= 1 + past_index)).strftime('%Y%m%d')
            res = get_items_from_box_folder(channel_folder_name=cnlname, date_folder_name=DATEFOLDERNAME,bl_folder_create=False)
            # print(res)

            try:
                if len(res['SlackUpload']['items'][cnlname]['items'][DATEFOLDERNAME]['items'])==0:
                    print("削除対象  " + cnlname + "  " + DATEFOLDERNAME)
                    folder_delete(res['SlackUpload']['items'][cnlname]['items'][DATEFOLDERNAME]['id'])
            except KeyError:
                pass

        past_index += 1
        if past_index > 210:
            print('7 month searched and deleted. completed.')
            break
            


if __name__ == "__main__":
    main()