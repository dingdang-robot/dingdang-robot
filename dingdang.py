#!/usr/bin/env python2
# -*- coding: utf-8-*-

from __future__ import print_function
import os
import sys
import logging
import yaml
import argparse
import threading
from client import tts
from client import stt
from client import dingdangpath
from client import diagnose
from client import WechatBot
from client.conversation import Conversation
import subprocess

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
parser.add_argument('--verbose', action='store_true',
                    help='Directly print logs rather than writing to log file')
args = parser.parse_args()

if args.local:
    from client.local_mic import Mic
else:
    from client.mic import Mic


class Dingdang(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)

        # Create config dir if it does not exist yet
        if not os.path.exists(dingdangpath.CONFIG_PATH):
            try:
                os.makedirs(dingdangpath.CONFIG_PATH)
            except OSError:
                self._logger.error("Could not create config dir: '%s'",
                                   dingdangpath.CONFIG_PATH, exc_info=True)
                raise

        # Check if config dir is writable
        if not os.access(dingdangpath.CONFIG_PATH, os.W_OK):
            self._logger.critical("Config dir %s is not writable. Dingdang " +
                                  "won't work correctly.",
                                  dingdangpath.CONFIG_PATH)

        config_file = dingdangpath.config('profile.yml')
        # Read config
        self._logger.debug("Trying to read config file: '%s'", config_file)
        try:
            with open(config_file, "r") as f:
                self.config = yaml.safe_load(f)
        except OSError:
            self._logger.error("Can't open config file: '%s'", config_file)
            raise

        try:
            stt_engine_slug = self.config['stt_engine']
        except KeyError:
            stt_engine_slug = 'sphinx'
            logger.warning("stt_engine not specified in profile, defaulting " +
                           "to '%s'", stt_engine_slug)
        stt_engine_class = stt.get_engine_by_slug(stt_engine_slug)

        try:
            slug = self.config['stt_passive_engine']
            stt_passive_engine_class = stt.get_engine_by_slug(slug)
        except KeyError:
            stt_passive_engine_class = stt_engine_class

        try:
            tts_engine_slug = self.config['tts_engine']
        except KeyError:
            tts_engine_slug = tts.get_default_engine_slug()
            logger.warning("tts_engine not specified in profile, defaulting " +
                           "to '%s'", tts_engine_slug)
        tts_engine_class = tts.get_engine_by_slug(tts_engine_slug)

        # Initialize Mic
        self.mic = Mic(
            self.config,
            tts_engine_class.get_instance(),
            stt_passive_engine_class.get_passive_instance(),
            stt_engine_class.get_active_instance())

    def start_wxbot(self):
        print("请扫描如下二维码登录微信")
        print("登录成功后，可以与自己的微信账号（不是文件传输助手）交互")
        self.wxBot.run(self.mic)

    def run(self):
        if 'first_name' in self.config:
            salutation = (u"%s 我能为您做什么?"
                          % self.config["first_name"])
        else:
            salutation = "主人，我能为您做什么?"

        persona = 'DINGDANG'
        if 'robot_name' in self.config:
            persona = self.config["robot_name"]
        conversation = Conversation(persona, self.mic, self.config)

        # create wechat robot
        if self.config['wechat']:
            self.wxBot = WechatBot.WechatBot(conversation.brain)
            self.wxBot.DEBUG = True
            self.wxBot.conf['qr'] = 'tty'
            conversation.wxbot = self.wxBot
            t = threading.Thread(target=self.start_wxbot)
            t.start()

        self.mic.say(salutation, cache=True)
        conversation.handleForever()


if __name__ == "__main__":
    subprocess.call('jack_control start', shell=True)

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
            format='%(asctime)s %(filename)s[line:%(lineno)d] \
        %(levelname)s %(message)s',
            level=logging.INFO)
    else:
        logging.basicConfig(
            filename=os.path.join(
                dingdangpath.TEMP_PATH, "dingdang.log"
            ),
            filemode="w",
            format='%(asctime)s %(filename)s[line:%(lineno)d] \
            %(levelname)s %(message)s',
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
        logger.error("Error occured!", exc_info=True)
        sys.exit(1)

    app.run()
