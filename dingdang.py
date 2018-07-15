#!/usr/bin/env python2
# -*- coding: utf-8-*-

from __future__ import print_function
import os
import sys
import logging
import argparse
import threading
import traceback
from client import tts
from client import stt
from client import dingdangpath
from client import diagnose
from client import WechatBot
from client.conversation import Conversation
from client import config
from client import statistic

# Add dingdangpath.LIB_PATH to sys.path
sys.path.append(dingdangpath.LIB_PATH)

parser = argparse.ArgumentParser(description='Dingdang Voice Control Center')
parser.add_argument('--local', action='store_true',
                    help='Use text input instead of a real microphone')
parser.add_argument('--no-network-check', action='store_true',
                    help='Disable the network connection check')
parser.add_argument('--diagnose', action='store_true',
                    help='Run diagnose and exit')
parser.add_argument('--debug', action='store_true', help='Show debug messages')
parser.add_argument('--info', action='store_true', help='Show info messages')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Directly print logs rather than writing to log file')
args = parser.parse_args()

if args.local:
    from client.local_mic import Mic
else:
    from client.mic import Mic


class Dingdang(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        config.init()

        stt_engine_slug = config.get('stt_engine', 'sphinx')
        stt_engine_class = stt.get_engine_by_slug(stt_engine_slug)

        slug = config.get('stt_passive_engine', stt_engine_slug)
        stt_passive_engine_class = stt.get_engine_by_slug(slug)

        tts_engine_slug = config.get('tts_engine',
                                     tts.get_default_engine_slug())
        tts_engine_class = tts.get_engine_by_slug(tts_engine_slug)

        # Initialize Mic
        self.mic = Mic(
            tts_engine_class.get_instance(),
            stt_passive_engine_class.get_passive_instance(),
            stt_engine_class.get_active_instance())

    def start_wxbot(self):
        print(u"请扫描如下二维码登录微信")
        print(u"登录成功后，可以与自己的微信账号（不是文件传输助手）交互")
        self.wxBot.run(self.mic)

    def run(self):
        salutation = (u"%s，我能为您做什么?" % config.get("first_name", u'主人'))

        persona = config.get("robot_name", 'DINGDANG')
        conversation = Conversation(persona, self.mic)

        statistic.report(0)

        # create wechat robot
        if config.get('wechat', False):
            self.wxBot = WechatBot.WechatBot(conversation.brain)
            self.wxBot.DEBUG = True
            self.wxBot.conf['qr'] = 'tty'
            conversation.wxbot = self.wxBot
            t = threading.Thread(target=self.start_wxbot)
            t.start()

        self.mic.say(salutation, cache=True)
        conversation.handleForever()


if __name__ == "__main__":

    print('''
*******************************************************"
*             叮当 - 中文语音对话机器人               *
*          (c) 2017 潘伟洲 <m@hahack.com>             *
*   https://github.com/wzpan/dingdang-robot.git       *
*******************************************************

如需查看log，可以执行 `tail -f 叮当所在目录/temp/dingdang.log`

''')

    if args.verbose:
        logging.basicConfig(
            format='%(asctime)s %(filename)s[line:%(lineno)d] '
                   + '%(levelname)s: %(message)s',
            level=logging.INFO)
    else:
        logging.basicConfig(
            filename=os.path.join(
                dingdangpath.TEMP_PATH, "dingdang.log"
            ),
            filemode="w",
            format='%(asctime)s %(filename)s[line:%(lineno)d] '
                   + '%(levelname)s: %(message)s',
            level=logging.INFO)

    logger = logging.getLogger()
    logger.getChild("client.stt").setLevel(logging.INFO)

    if args.debug:
        logger.setLevel(logging.DEBUG)
    elif args.info:
        logger.setLevel(logging.INFO)

    if not args.no_network_check and not diagnose.check_network_connection():
        logger.warning("Network not connected. This may prevent Dingdang " +
                       "from running properly.")

    if args.diagnose:
        failed_checks = diagnose.run()
        sys.exit(0 if not failed_checks else 1)

    try:
        app = Dingdang()
    except Exception:
        logger.exception("Error occured!")
        sys.exit(1)

    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("dingdang get Keyboard Interrupt, exit.")
        print("dingdang exit.")
    except Exception:
        logger.exception("dingdang quit unexpectedly!")
        if not args.verbose:
            msg = traceback.format_exc()
            print("** dingdang quit unexpectedly! ** ")
            print(msg)
        sys.exit(1)
