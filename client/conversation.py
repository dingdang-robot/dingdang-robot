# -*- coding: utf-8-*-
from __future__ import absolute_import
import logging
import time
from .notifier import Notifier
from .brain import Brain
from .drivers.pixels import pixels
from . import plugin_loader
from . import config


class Conversation(object):

    def __init__(self, persona, mic):
        self._logger = logging.getLogger(__name__)
        self.persona = persona
        self.mic = mic
        self.brain = Brain(mic)
        self.notifier = Notifier(config.get(), self.brain)
        self.wxbot = None

    @staticmethod
    def is_proper_time():
        """
        whether it's the proper time to gather
        notifications without disturb user
        """
        if not config.has('do_not_bother'):
            return True
        bother_profile = config.get('do_not_bother')
        if not bother_profile['enable']:
            return True
        if 'since' not in bother_profile or 'till' not in bother_profile:
            return True

        since = bother_profile['since']
        till = bother_profile['till']
        current = time.localtime(time.time()).tm_hour
        if till > since:
            return current not in range(since, till)
        else:
            return not (current in range(since, 25) or
                        current in range(-1, till))

    def handleForever(self):
        """
        Delegates user input to the handling function when activated.
        """
        self._logger.info("Starting to handle conversation with keyword '%s'.",
                          self.persona)
        while True:
            # Print notifications until empty
            if self.is_proper_time():
                notifications = self.notifier.getAllNotifications()
                for notif in notifications:
                    self._logger.info("Received notification: '%s'",
                                      str(notif))
                    self.mic.say(str(notif))

            if self.mic.stop_passive:
                self._logger.info("skip conversation for now.")
                time.sleep(1)
                continue

            if not self.mic.skip_passive:
                self._logger.debug("Started listening for keyword '%s'",
                                   self.persona)
                threshold, transcribed = self.mic.passiveListen(self.persona)
                self._logger.debug("Stopped listening for keyword '%s'",
                                   self.persona)

                if not transcribed or not threshold:
                    self._logger.info("Nothing has been said or transcribed.")
                    continue
                self._logger.info("Keyword '%s' has been said!", self.persona)
            else:
                self._logger.debug("Skip passive listening")
                if not self.mic.chatting_mode:
                    self.mic.skip_passive = False
                continue
            pixels.wakeup()            

            self._logger.debug("Started to listen actively with threshold: %r",
                               threshold)

            # run plugins before listen
            for plugin in plugin_loader.get_plugins_before_listen():
                continueHandle = False
                try:
                    continueHandle = plugin.beforeListen(
                        self.mic, config.get(), self.wxbot)
                except Exception:
                    self._logger.error("plugin '%s' run error",
                                       plugin.__name__, exc_info=True)
                finally:
                    if not continueHandle:
                        break

            input = self.mic.activeListenToAllOptions(threshold)
            self._logger.debug("Stopped to listen actively with threshold: %r",
                               threshold)
<<<<<<< HEAD
            pixels.think()
=======

            # run plugins after listen
            for plugin in plugin_loader.get_plugins_after_listen():
                continueHandle = False
                try:
                    continueHandle = plugin.afterListen(
                        self.mic, config.get(), self.wxbot)
                except Exception:
                    self._logger.error("plugin '%s' run error",
                                       plugin.__name__, exc_info=True)
                finally:
                    if not continueHandle:
                        break
>>>>>>> efc94c2... fix: modify for PEP8

            if input:
                self.brain.query(input, self.wxbot)
            elif config.get('shut_up_if_no_input', False):
                self._logger.info("Active Listen return empty")
            else:
                self.mic.say(u"什么?")
            pixels.off()
