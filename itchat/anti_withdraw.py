#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2017-03-12 12:51
# @Author  : Zhang Du
# @File    : anti_withdraw.py

import os
import re
import shutil
import time
import itchat
from itchat.content import *
import traceback

# {msg_id:(msg_from,msg_to,msg_time,msg_time_touser,msg_type,msg_content,msg_url)}
msg_dict = {}

#ClearTimeOutMsg用于清理消息字典，把超时消息清理掉
#为减少资源占用，此函数只在有新消息动态时调用
def ClearTimeOutMsg():
    if msg_dict.__len__() > 0:
        for msgid in list(msg_dict): #由于字典在遍历过程中不能删除元素，故使用此方法
            if time.time() - msg_dict.get(msgid, None)["msg_time"] > 130.0: #超时两分钟
                item = msg_dict.pop(msgid)
                #print("超时的消息：", item['msg_content'])
                #可下载类消息，并删除相关文件
                if item['msg_type'] == "Picture" \
                        or item['msg_type'] == "Recording" \
                        or item['msg_type'] == "Video" \
                        or item['msg_type'] == "Attachment":
                    print("要删除的文件：", item['msg_content'])
                    os.remove(item['msg_content'])

#将接收到的消息存放在字典中，当接收到新消息时对字典中超时的消息进行清理
#没有注册note（通知类）消息，通知类消息一般为：红包 转账 消息撤回提醒等，不具有撤回功能
@itchat.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS], isFriendChat=True)
def Revocation(msg):
    mytime = time.localtime()  # 这儿获取的是本地时间
    #获取用于展示给用户看的时间 2017/03/03 13:23:53
    msg_time_touser = mytime.tm_year.__str__() \
                      + "/" + mytime.tm_mon.__str__() \
                      + "/" + mytime.tm_mday.__str__() \
                      + " " + mytime.tm_hour.__str__() \
                      + ":" + mytime.tm_min.__str__() \
                      + ":" + mytime.tm_sec.__str__()

    msg_id = msg['MsgId'] #消息ID
    msg_time = msg['CreateTime'] #消息时间
    # if msg['isAt']:
    #     msg_from = msg['FromUserName']
    #     #itchat.send(u'@%s\u2005I received: %s' % (msg['ActualNickName'], msg['Content']), msg['FromUserName'])
    # else:
    msg_from = itchat.search_friends(userName = msg['FromUserName'])['NickName'] #消息发送人昵称
    msg_type = msg['Type'] #消息类型
    msg_content = None #根据消息类型不同，消息内容不同
    msg_url = None #分享类消息有url
    #图片 语音 附件 视频，可下载消息将内容下载暂存到当前目录
    if msg['Type'] == 'Text':
        msg_content = msg['Text']
    elif msg['Type'] == 'Picture':
        msg_content = msg['FileName']
        msg['Text'](msg['FileName'])
    elif msg['Type'] == 'Card':
        msg_content = msg['RecommendInfo']['NickName'] + r" 的名片"
    elif msg['Type'] == 'Map':
        x, y, location = re.search("<location x=\"(.*?)\" y=\"(.*?)\".*label=\"(.*?)\".*", msg['OriContent']).group(1,
                                                                                                                    2,
                                                                                                                    3)
        if location is None:
            msg_content = r"纬度->" + x.__str__() + " 经度->" + y.__str__()
        else:
            msg_content = r"" + location
    elif msg['Type'] == 'Sharing':
        msg_content = msg['Text']
        msg_url = msg['Url']
    elif msg['Type'] == 'Recording':
        msg_content = msg['FileName']
        msg['Text'](msg['FileName'])
    elif msg['Type'] == 'Attachment':
        msg_content = r"" + msg['FileName']
        msg['Text'](msg['FileName'])
    elif msg['Type'] == 'Video':
        msg_content = msg['FileName']
        msg['Text'](msg['FileName'])
    elif msg['Type'] == 'Friends':
        msg_content = msg['Text']

    #更新字典
    # {msg_id:(msg_from,msg_time,msg_time_touser,msg_type,msg_content,msg_url)}
    msg_dict.update(
        {msg_id: {"msg_from": msg_from, "msg_time": msg_time, "msg_time_touser": msg_time_touser, "msg_type": msg_type,
                  "msg_content": msg_content, "msg_url": msg_url, "msg_group_name": ""}})
    print("FriendChat! ", "msg_from:", msg_from, "msg_content:", msg_content, "msg_id:", msg_id)
    #清理字典
    ClearTimeOutMsg()

#收到note类消息，判断是不是撤回并进行相应操作
@itchat.msg_register([NOTE], isFriendChat=True)
def SaveMsg(msg):
    # print(msg)
    #创建可下载消息内容的存放文件夹，并将暂存在当前目录的文件移动到该文件中
    if not os.path.exists(".\\Revocation\\"):
        os.mkdir(".\\Revocation\\")

    # print(msg['Content'])
    if re.search(r"\<replacemsg\>\<\!\[CDATA\[.+ recalled a message\.\]\]\>\<\/replacemsg\>", msg['Content']) != None:
        old_msg_id = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
        old_msg = msg_dict.get(old_msg_id, {})
        # print(old_msg_id, old_msg)
        msg_send = r"您的好友：" \
                   + old_msg.get('msg_from', "") \
                   + r"  在 [" + old_msg.get('msg_time_touser', "") \
                   + r"], 撤回了一条 ["+old_msg['msg_type']+"] 消息, 内容如下:" \
                   + old_msg.get('msg_content', "")
        if old_msg['msg_type'] == "Sharing":
            msg_send += r", 链接: " \
                        + old_msg.get('msg_url', "")
        elif old_msg['msg_type'] == 'Picture' \
                or old_msg['msg_type'] == 'Recording' \
                or old_msg['msg_type'] == 'Video' \
                or old_msg['msg_type'] == 'Attachment':
            msg_send += r", 存储在当前目录下Revocation文件夹中"
            shutil.move(old_msg['msg_content'], r".\\Revocation\\")
        print("Message send to my phone: ", msg_send)
        itchat.send(msg_send, toUserName='filehelper') #将撤回消息的通知以及细节发送到文件助手

        msg_dict.pop(old_msg_id)
        ClearTimeOutMsg()

# # 在注册时增加isGroupChat=True将判定为群聊回复
@itchat.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS], isGroupChat = True)
def groupchat_reply(msg):
    try:
        mytime = time.localtime()  # 这儿获取的是本地时间
        # 获取用于展示给用户看的时间 2017/03/03 13:23:53
        msg_time_touser = mytime.tm_year.__str__() \
                          + "/" + mytime.tm_mon.__str__() \
                          + "/" + mytime.tm_mday.__str__() \
                          + " " + mytime.tm_hour.__str__() \
                          + ":" + mytime.tm_min.__str__() \
                          + ":" + mytime.tm_sec.__str__()

        msg_id = msg['MsgId']  # 消息ID
        msg_time = msg['CreateTime']  # 消息时间
        # if msg['isAt']:
        #     msg_from = msg['FromUserName']
        #     #itchat.send(u'@%s\u2005I received: %s' % (msg['ActualNickName'], msg['Content']), msg['FromUserName'])
        # else:
        try:
            msg_from = msg['ActualNickName'] # 消息发送人昵称
        except KeyError:
            msg_from = "你自己"
        except:
            traceback.print_exc()
        msg_type = msg['Type']  # 消息类型
        msg_content = None  # 根据消息类型不同，消息内容不同
        msg_url = None  # 分享类消息有url
        # 图片 语音 附件 视频，可下载消息将内容下载暂存到当前目录
        if msg['Type'] == 'Text':
            msg_content = msg['Text']
        elif msg['Type'] == 'Picture':
            msg_content = msg['FileName']
            msg['Text'](msg['FileName'])
        elif msg['Type'] == 'Card':
            msg_content = msg['RecommendInfo']['NickName'] + r" 的名片"
        elif msg['Type'] == 'Map':
            x, y, location = re.search("<location x=\"(.*?)\" y=\"(.*?)\".*label=\"(.*?)\".*", msg['OriContent']).group(
                1,
                2,
                3)
            if location is None:
                msg_content = r"纬度->" + x.__str__() + " 经度->" + y.__str__()
            else:
                msg_content = r"" + location
        elif msg['Type'] == 'Sharing':
            msg_content = msg['Text']
            msg_url = msg['Url']
        elif msg['Type'] == 'Recording':
            msg_content = msg['FileName']
            msg['Text'](msg['FileName'])
        elif msg['Type'] == 'Attachment':
            msg_content = r"" + msg['FileName']
            msg['Text'](msg['FileName'])
        elif msg['Type'] == 'Video':
            msg_content = msg['FileName']
            msg['Text'](msg['FileName'])
        elif msg['Type'] == 'Friends':
            msg_content = msg['Text']

        # 更新字典
        # {msg_id:(msg_from,msg_time,msg_time_touser,msg_type,msg_content,msg_url)}
        msg_dict.update(
            {msg_id: {"msg_from": msg_from, "msg_time": msg_time, "msg_time_touser": msg_time_touser,
                      "msg_type": msg_type,
                      "msg_content": msg_content, "msg_url": msg_url, "msg_group_name": msg['GroupChatName']}})
        print("GroupChat! ","msg_from:", msg_from, "msg_content:", msg_content, "msg_id:", msg_id,
                "msg['GroupChatName'] = ", msg['GroupChatName'])
        # 清理字典
        ClearTimeOutMsg()
    except:
        traceback.print_exc()


#收到note类消息，判断是不是撤回并进行相应操作
@itchat.msg_register([NOTE], isGroupChat = True)
def SaveMsg(msg):
    # print(msg)
    #创建可下载消息内容的存放文件夹，并将暂存在当前目录的文件移动到该文件中
    if not os.path.exists(".\\Revocation\\"):
        os.mkdir(".\\Revocation\\")

    # print('Groupchat Note message! ', "msg['Content'] = ", msg['Content'])
    if re.search(r"\<replacemsg\>\<\!\[CDATA\[.+ recalled a message\.\]\]\>\<\/replacemsg\>", msg['Content']) != None:
        # old_msg_id = re.search(";msgid\&gt;(.*?)\&lt;\/msgid\&gt", msg['Content']).group(1)
        old_msg_id = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
        old_msg = msg_dict.get(old_msg_id, {})
        msg_send = r"您的好友：" \
                   + old_msg.get('msg_from', "") \
                   + r"  在 [" + old_msg.get('msg_time_touser', "") \
                   + r"]于\"" + old_msg.get('msg_group_name', "") + "\"" \
                   + r", 撤回了一条 [" + old_msg['msg_type'] + "] 消息, 内容如下:" \
                   + old_msg.get('msg_content', "")
        if old_msg['msg_type'] == "Sharing":
            msg_send += r", 链接: " \
                        + old_msg.get('msg_url', "")
        elif old_msg['msg_type'] == 'Picture' \
                or old_msg['msg_type'] == 'Recording' \
                or old_msg['msg_type'] == 'Video' \
                or old_msg['msg_type'] == 'Attachment':
            msg_send += r", 存储在当前目录下Revocation文件夹中"
            shutil.move(old_msg['msg_content'], r".\\Revocation\\")

        print("Message send to my phone: ", msg_send)
        itchat.send(msg_send, toUserName='filehelper')  # 将撤回消息的通知以及细节发送到文件助手

        msg_dict.pop(old_msg_id)
        ClearTimeOutMsg()
    elif re.search(r";!\[CDATA\[You've recalled a message\.\]\]", msg['Content']) != None:
        old_msg_id = re.search(";msgid\&gt;(.*?)\&lt;\/msgid\&gt", msg['Content']).group(1)
        old_msg = msg_dict.get(old_msg_id, {})

        msg_send = r"您的好友：" \
                   + old_msg.get('msg_from', "") \
                   + r"  在 [" + old_msg.get('msg_time_touser', "") \
                   + "]于\"" + old_msg.get('msg_group_name', "") + "\"" \
                   + r", 撤回了一条 [" + old_msg['msg_type'] + "] 消息, 内容如下:" \
                   + old_msg.get('msg_content', "")
        if old_msg['msg_type'] == "Sharing":
            msg_send += r", 链接: " \
                        + old_msg.get('msg_url', "")
        elif old_msg['msg_type'] == 'Picture' \
                or old_msg['msg_type'] == 'Recording' \
                or old_msg['msg_type'] == 'Video' \
                or old_msg['msg_type'] == 'Attachment':
            msg_send += r", 存储在当前目录下Revocation文件夹中"
            shutil.move(old_msg['msg_content'], r".\\Revocation\\")
        print("Message send to my phone: ", msg_send)
        itchat.send(msg_send, toUserName='filehelper')  # 将撤回消息的通知以及细节发送到文件助手

        msg_dict.pop(old_msg_id)
        ClearTimeOutMsg()
    else:
        pass


itchat.auto_login(hotReload=True)
itchat.run()