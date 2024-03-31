from channel.wechat import WeChatChannel
from channel.wrest import WrestChannel
from config import load_config, conf
from utils.log import logger
from utils.print import color_print
from plugins.manager import PluginManager


if __name__ == "__main__":
    try:
        # load config
        load_config()

        # print banner
        color_print("WeChat GPTBot")

        # load plugins
        PluginManager().load_plugins()

        # start wechat channel
        WrestChannel().startup()
    except Exception as e:
        logger.error("App startup failed!")
        logger.exception(e)
