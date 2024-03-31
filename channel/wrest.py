import json
import warnings
import websocket
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from utils.log import logger
from utils import const
import os
from bot.bot import Bot
from common.singleton import singleton
from config import conf
from utils.check import check_prefix, is_wx_account
from common.reply import ReplyType, Reply
from channel.message import Message
from utils.const import MessageType
from plugins.manager import PluginManager
from common.context import ContextType, Context
from plugins.event import EventType, Event
from channel.channel import Channel


@singleton
class WrestChannel(Channel):
    def __init__(self):
        warnings.filterwarnings("ignore")
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "1"

        self._addr = conf().get("wechat_addr", "127.0.0.1")
        self._port = conf().get("wechat_port", "7600")
        self.get_personal_info()
        self.update_contacts()
        self.ws = websocket.WebSocketApp(
            f"ws://{self._addr}:{self._port}/wcf/socket_receiver",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

    def startup(self):
        logger.info("App startup successfully!")
        self.ws.run_forever()

    def on_message(self, ws, message):
        raw_msg = json.loads(message)
        sdid = raw_msg.get('sender')
        rmid = raw_msg.get('roomid')
        wxid = rmid or raw_msg.get('sender')
        time = datetime.fromtimestamp(raw_msg.get('ts', 0))
        raw_msg = {
            'wxid': wxid,
            'id1': sdid,
            'id2': '',
            'sender_name': self.contacts.get(sdid, {}).get('name', ''),
            'group_name': self.contacts.get(rmid, {}).get('name', ''),
            'time': time.strftime("%Y-%m-%d %H:%M:%S"),
            **raw_msg,
        }
        msg_type = raw_msg.get('type')
        handlers = {
            MessageType.AT_MSG.value: self.handle_message,
            MessageType.TXT_MSG.value: self.handle_message,
            MessageType.PIC_MSG.value: self.handle_message,
            MessageType.RECV_PIC_MSG.value: self.handle_message,
            MessageType.RECV_TXT_MSG.value: self.handle_message,
            MessageType.RECV_TXT_CITE_MSG.value: self.handle_cite_message,
            MessageType.HEART_BEAT.value: self.noop,
        }
        if handler := handlers.get(msg_type):
            handler(raw_msg)
        else:
            logger.info('on_message: %s %s', msg_type, raw_msg)

    def noop(self, raw_msg):
        pass

    def handle_cite_message(self, raw_msg):
        xml_msg = (
            raw_msg["content"]["content"]
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )
        soup = BeautifulSoup(xml_msg, "lxml")
        cooked_msg = {
            "content": soup.select_one("title").text,
            "id": raw_msg["id"],
            "id1": raw_msg["content"]["id2"],
            "id2": "",
            "id3": "",
            "srvid": raw_msg["srvid"],
            "time": raw_msg["time"],
            "type": raw_msg["type"],
            "wxid": raw_msg["content"]["id1"],
        }
        self.handle_message(cooked_msg)

    def handle_message(self, raw_msg):
        # ignore message sent by self
        if raw_msg.get('is_self'):
            logger.info("message sent by self, ignore")
            return
        msg = Message(raw_msg, self.personal_info)
        logger.info(f"message received: {msg}")
        e = PluginManager().emit(
            Event(EventType.DID_RECEIVE_MESSAGE, {"channel": self, "message": msg})
        )
        if e.is_bypass:
            return self.send(e.reply, e.message)
        if e.message.is_group:
            self.handle_group(e.message)
        else:
            self.handle_single(e.message)

    def handle_group(self, msg: Message):
        session_independent = conf().get("chat_group_session_independent")
        context = Context()
        context.session_id = msg.sender_id if session_independent else msg.room_id
        if msg.is_at:
            query = msg.content.replace(f"@{msg.receiver_name}", "", 1).strip()
            context.query = query
            create_image_prefix = conf().get("create_image_prefix")
            match_prefix = check_prefix(query, create_image_prefix)
            if match_prefix:
                context.type = ContextType.CREATE_IMAGE
            self.handle_reply(msg, context)

    def handle_single(self, msg: Message):
        # ignore message sent by public/subscription account
        if not is_wx_account(msg.sender_id):
            logger.info("message sent by public/subscription account, ignore")
            return
        context = Context()
        context.session_id = msg.sender_id
        query = msg.content
        single_chat_prefix = conf().get("single_chat_prefix")
        if single_chat_prefix is not None and len(single_chat_prefix) > 0:
            match_chat_prefix = check_prefix(query, single_chat_prefix)
            if match_chat_prefix is not None:
                query = query.replace(match_chat_prefix, "", 1).strip()
            else:
                logger.info("your message is not start with single_chat_prefix, ignore")
                return
        context.query = query
        create_image_prefix = conf().get("create_image_prefix")
        match_image_prefix = check_prefix(query, create_image_prefix)
        if match_image_prefix:
            context.type = ContextType.CREATE_IMAGE
        self.handle_reply(msg, context)

    def decorate_reply(self, reply: Reply, msg: Message) -> Reply:
        if reply.type == ReplyType.TEXT:
            group_chat_reply_prefix = conf().get("group_chat_reply_prefix", "")
            group_chat_reply_suffix = conf().get("group_chat_reply_suffix", "")
            single_chat_reply_prefix = conf().get("single_chat_reply_prefix", "")
            single_chat_reply_suffix = conf().get("single_chat_reply_suffix", "")
            reply_text = reply.content
            if msg.is_group:
                reply_text = (
                    group_chat_reply_prefix + reply_text + group_chat_reply_suffix
                )
            else:
                reply_text = (
                    single_chat_reply_prefix + reply_text + single_chat_reply_suffix
                )
            reply.content = reply_text
        return reply

    def handle_reply(self, msg: Message, context: Context):
        e1 = PluginManager().emit(
            Event(
                EventType.WILL_GENERATE_REPLY,
                {"channel": self, "message": msg, "context": context},
            )
        )
        if e1.is_bypass:
            return self.send(e1.reply, e1.message)

        rawReply = Bot().reply(e1.context)

        e2 = PluginManager().emit(
            Event(
                EventType.WILL_DECORATE_REPLY,
                {
                    "channel": self,
                    "message": e1.message,
                    "context": e1.context,
                    "reply": rawReply,
                },
            )
        )
        if e2.is_bypass:
            return self.send(e2.reply, e2.message)

        reply = self.decorate_reply(rawReply, msg)

        e3 = PluginManager().emit(
            Event(
                EventType.WILL_SEND_REPLY,
                {
                    "channel": self,
                    "message": e2.message,
                    "context": e2.context,
                    "reply": reply,
                },
            )
        )
        self.send(e3.reply, e3.message)

    def send(self, reply: Reply, msg: Message):
        if reply is None:
            return
        wx_id = msg.room_id if msg.is_group else msg.sender_id
        if reply.type == ReplyType.IMAGE:
            self.request_api('wcf/send_img', json={
                'receiver': wx_id,
                'path': reply.content,
            })
        elif reply.type == ReplyType.VIDEO:
            sep = '&' if '?' in reply.content else '?'
            self.request_api('wcf/send_file', json={
                'receiver': wx_id,
                'path': f'{reply.content}{sep}_=video.mp4',
            })
        else:
            self.request_api('wcf/send_txt', json={
                'receiver': wx_id,
                'msg': reply.content,
            })

    def on_open(self, ws):
        logger.info("[Websocket] connected")

    def on_close(self, ws, *args):
        logger.info("[Websocket] disconnected %s", args)

    def on_error(self, ws, error):
        etb = error.__traceback__
        logger.error(f"[Websocket] Error: {etb}")

    def get_personal_info(self):
        info = self.request_api('wcf/self_info') or {}
        info.update({
            'wx_id': info.get('wxid', ''),
            'wx_name': info.get('name', ''),
        })
        logger.info('Wrest login info: %s', info)
        self.personal_info = info
        return info

    def update_contacts(self):
        contacts = self.request_api('wcf/contacts') or []
        logger.info('Load %s contacts', len(contacts))
        self.contacts = {
            v.get('wxid'): v
            for v in contacts
        }
        return self.contacts

    def request_api(self, api, **kwargs):
        res = requests.post(f'http://{self._addr}:{self._port}/{api}', **kwargs)
        try:
            dat = res.json() or {}
        except requests.exceptions.JSONDecodeError as exc:
            dat = {
                'response': res.text,
                'error': exc,
            }
            logger.warning('Request error: %s', [api, dat])
        return dat.get('Payload', dat)
