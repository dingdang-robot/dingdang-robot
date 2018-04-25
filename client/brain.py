# -*- coding: utf-8-*-
from __future__ import absolute_import
import logging
from . import plugin_loader
from . import config


class Brain(object):

    def __init__(self, mic):
        """
        Instantiates a new Brain object, which cross-references user
        input with a list of plugins. Note that the order of brain.plugins
        matters, as the Brain will cease execution on the first plugin
        that accepts a given input.

        Arguments:
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone
                   number)
        """

        self.mic = mic
        self.plugins = plugin_loader.get_plugins()
        self._logger = logging.getLogger(__name__)
        self.handling = False

    def query(self, texts, wxbot=None, thirdparty_call=False):
        """
        Passes user input to the appropriate plugin, testing it against
        each candidate plugin's isValid function.

        Arguments:
        texts -- user input, typically speech, to be parsed by a plugin
        wxbot -- also send the respondsed result to wechat
        thirdparty_call -- call from wechat or email
        """

        for plugin in self.plugins:
            for text in texts:
                if not plugin.isValid(text):
                    continue

                # check whether plugin is allow to be call by thirdparty
                if thirdparty_call \
                        and plugin_loader.check_thirdparty_exclude(plugin):
                    self.mic.say(u'抱歉，该功能暂时只能通过语音' +
                                 u'命令开启。请试试唤醒我后直接' +
                                 u'对我说"%s"' % text)
                    return

                self._logger.debug("'%s' is a valid phrase for plugin " +
                                   "'%s'", text, plugin.__name__)
                continueHandle = False
                try:
                    self.handling = True
                    continueHandle = plugin.handle(text, self.mic,
                                                   config.get(), wxbot)
                    self.handling = False
                except Exception:
                    self._logger.error('Failed to execute plugin',
                                       exc_info=True)
                    reply = u"抱歉，我的大脑出故障了，晚点再试试吧"
                    self.mic.say(reply)
                else:
                    self._logger.debug("Handling of phrase '%s' by " +
                                       "plugin '%s' completed", text,
                                       plugin.__name__)
                finally:
                    self.mic.stop_passive = False
                    if not continueHandle:
                        return
        self._logger.debug("No plugin was able to handle any of these " +
                           "phrases: %r", texts)
