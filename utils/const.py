from enum import IntEnum

# server
IP = "127.0.0.1"
PORT = "5555"
SERVER = f"ws://{IP}:{PORT}"

# "SUCCSESSED" should be a typo in the hook server😂
SUCCESS = "SUCCSESSED"


# https://github.com/opentdp/wrest-chat/blob/8935382142ee590e255717fda1f2ccae851ac4af/wclient/README.md?plain=1#L179
class MessageType(IntEnum):
    RECV_TXT_MSG = 1
    RECV_PIC_MSG = 3
    RECV_LINK_MSG = 4
    RECV_VLINK_MSG = 5
    RECV_FILE_MSG = 6
    RECV_TXT_CITE_MSG = 49
    PIC_MSG = 500
    AT_MSG = 550
    TXT_MSG = 555
    USER_LIST = 5000
    GET_USER_LIST_SUCCESS = 5001
    GET_USER_LIST_FAIL = 5002
    ATTACH_FILE = 5003
    HEART_BEAT = 5005
    CHATROOM_MEMBER = 5010
    CHATROOM_MEMBER_NICK = 5020
    PERSONAL_INFO = 6500
    PERSONAL_DETAIL = 6550
    DEBUG_SWITCH = 6000
    DESTROY_ALL = 9999
    JOIN_ROOM = 10000
