from pydantic import BaseModel
from utils.api import get_sender_name


class Message(BaseModel):
    room_id: str = None
    sender_id: str = None
    sender_name: str = None
    receiver_id: str = None
    receiver_name: str = None
    content: str = None
    type: int = None  # MessageType value
    is_group: bool = False
    is_at: bool = False
    create_time: str = None
    _raw_msg: dict = None

    def __init__(self, msg, info, channel=None):
        super().__init__()
        self._raw_msg = msg
        self.channel = channel
        self.receiver_id = info["wx_id"]
        self.receiver_name = info["wx_name"]
        self.content = msg["content"]
        if isinstance(self.content, str):
            self.content = self.content.strip()
        self.type = msg["type"]
        self.refermsg = msg.get('refermsg') or {}
        self.create_time = msg["time"]
        if "@chatroom" in msg["wxid"]:
            self.is_group = True
            self.room_id = msg["wxid"]
            self.sender_id = msg["id1"]
            self.is_at = f"@{self.receiver_name}" in self.content
        else:
            self.is_group = False
            self.sender_id = msg["wxid"]
        self.sender_name = msg.get('sender_name')
        if self.sender_name is None:
            self.sender_name = get_sender_name(self.room_id, self.sender_id)

    def __str__(self):
        return f"Message(room_id={self.room_id}, sender_id={self.sender_id}, sender_name={self.sender_name}, receiver_id={self.receiver_id}, receiver_name={self.receiver_name}, content={self.content}, type={self.type}, is_group={self.is_group}, create_time={self.create_time}, is_at={self.is_at})"

    def get_refer_extra(self):
        if not self.refermsg:
            return None
        if not self.channel:
            return None
        return self.channel.get_refer_extra(self.refermsg)

    def get_refer_image(self, save_dir):
        if not self.refermsg:
            return None
        if not self.channel:
            return None
        return self.channel.get_refer_image(self.refermsg, save_dir)
