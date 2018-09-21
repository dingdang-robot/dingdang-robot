# -*- coding: utf-8-*-
"""
    The Mic class handles all interactions with the microphone and speaker.
"""
from __future__ import absolute_import
import ctypes
import logging
import tempfile
import wave
import audioop
import time
import pyaudio
import threading
from time import ctime,sleep
from . import dingdangpath
from . import mute_alsa
from .app_utils import wechatUser
from .drivers.pixels import pixels
from . import plugin_loader
from . import config

nowTime = lambda:int(round(time.time() * 1000))

class Mic:
    speechRec = None
    speechRec_persona = None

    THRESHOLD_MULTIPLIER = 2
    RATE = 16000  #每秒数据
    CHUNK = 1024  #每秒15段数据
    audioFrames = []

    isLongVoiceState = False;
    keepLive = True;
    passiveText = "";
    longVoiceText = "";
    passiveLock = threading.Semaphore(0)
    longVoiceLock = threading.Semaphore(0)
    sttLongTextLock = threading.Semaphore(0)
    audioFramesLock = threading.Lock()
    hasLockedPassive = False

    def __init__(self, speaker, passive_stt_engine, active_stt_engine):
        """
        Initiates the pocketsphinx instance.

        Arguments:
        speaker -- handles platform-independent audio output
        passive_stt_engine -- performs STT while Dingdang is in passive listen
                              mode
        acive_stt_engine -- performs STT while Dingdang is in active listen
                            mode
        """
        self.robot_name = config.get('robot_name_cn', u'叮当')
        self._logger = logging.getLogger(__name__)
        self.speaker = speaker
        self.wxbot = None
        self.passive_stt_engine = passive_stt_engine
        self.active_stt_engine = active_stt_engine
        self.dingdangpath = dingdangpath
        self._logger.info("Initializing PyAudio. ALSA/Jack error messages " +
                          "that pop up during this process are normal and " +
                          "can usually be safely ignored.")
        try:
            asound = ctypes.cdll.LoadLibrary('libasound.so.2')
            asound.snd_lib_error_set_handler(mute_alsa.c_error_handler)
        except OSError:
            pass
        self._audio = pyaudio.PyAudio()
        self._logger.info("Initialization of PyAudio completed.")
        self.stop_passive = False
        self.skip_passive = False
        self.chatting_mode = False
        threadConsumer = threading.Thread(target=self.audioConsumerThread,args=())
        threadProducer = threading.Thread(target=self.audioProducerThread,args=())
        threadConsumer.setDaemon(True);
        threadProducer.setDaemon(True);
        threadConsumer.start();
        threadProducer.start();


    def __del__(self):
        self._audio.terminate()

    def audioProducerThread(self):
        print "# prepare recording stream"
        stream = self._audio.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=self.RATE,
                                  input=True,
                                  frames_per_buffer=self.CHUNK)
        print "# stores the audio data"
        while self.keepLive:
            frame = stream.read(self.CHUNK, exception_on_overflow=False);
             
            self.audioFramesLock.acquire();
            self.audioFrames.append(frame)       
            if len(self.audioFrames) > 30:   #超过1秒钟的存储全删掉
                del self.audioFrames[:-30]   
            self.audioFramesLock.release();
        

    def audioConsumerThread(self):
        FRAME_TIME = 0.2  #400毫秒
        threshold = 1000000;
        longVoiceDuration = 0; #毫秒
        lastVoiceFrameTime = 0; #毫秒
        self.isLongVoiceState = False
        frames = []
        lastN = [i for i in range(350, 370)]
        moreFrame = False;
        while self.keepLive:
            frame = [];

            self.audioFramesLock.acquire();
            if len(self.audioFrames) > 4:
                frame = self.audioFrames[:4]
                del self.audioFrames[:4]
            self.audioFramesLock.release();
            
            if len(frame) == 0:
                time.sleep(0.05);
                continue;

            if self.stop_passive:
                continue

            frames += frame;
            score = self.getScore("".join(frame))
            #print(score, threshold,len(frame), self.stop_passive, self.isLongVoiceState, moreFrame)

            if score < threshold and not moreFrame: #如果静音并且不需要更多数据帧
                if self.isLongVoiceState and nowTime() - lastVoiceFrameTime < 1200: #短暂的停顿, 文本分句
                    self._logger.debug("short blank as hearing something", len(frames))
                    continue
                elif self.isLongVoiceState:   #长时间的停顿, 本次语音输入停止
                    self.isLongVoiceState = False       #标记长语音识别停止
                    self.longVoiceLock.release();
                    self.longVoiceText = self.sttProcess(frames);
                    self.sttLongTextLock.release();
                    del frames[:]

                else:
                    # save this data point as a score
                    lastN.pop(0)
                    lastN.append(score)                  #记录当前帧环境音的水平
                    average = sum(lastN) / len(lastN)    #记录当前环境音的平均水平
                    threshold = average * self.THRESHOLD_MULTIPLIER   #计算超过声音在环境音当中的阈值
                    slientDurationStart = nowTime();
                    del frames[:]

                    continue                #非长语音识别状态下的静音跳出
            else: #否则非静音状态
                moreFrame = False;
                if not self.isLongVoiceState:  #如果非长语音识别状态下
                    passiveText = self.passive_stt_engine.transcribe_keyword(''.join(frames));
                    if len(passiveText) != 0: #探测到唤醒词
                        self.passiveText = passiveText;
                        self.isLongVoiceState = True; #进入长语音识别状态
                        del frames[:];  #清空数据缓冲区
                        self.passiveLock.release();
                        moreFrame = True;
                    else:  #没有探测到唤醒词
                        if score > threshold:
                            moreFrame = True;

                    if len(frames) > 4 * len(frame):         #超过完整的语音唤醒词的时间大约1.2秒, 2个数据帧的长度
                        del frames[0-len(frame)*4:];          #从头删除一个数据帧
                    #print(2, len(frames))

                else: #否则长语音识别状态下
                    lastVoiceFrameTime = nowTime(); #毫秒
        
        
        #结束关闭数据流,其实无法走到这里
        try:
            # self.stop_passive = False
            stream.stop_stream()
            stream.close()
        except Exception as e:
            self._logger.debug(e)
            pass


    def sttProcess(self, frames):
        with tempfile.SpooledTemporaryFile(mode='w+b') as f:
            wav_fp = wave.open(f, 'wb')
            wav_fp.setnchannels(1)
            wav_fp.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
            wav_fp.setframerate(self.RATE)
            wav_fp.writeframes(''.join(frames))
            wav_fp.close()
            f.seek(0)
            return self.active_stt_engine.transcribe(f)

    def getScore(self, data):
        rms = audioop.rms(data, 2)
        score = rms / 3
        return score

    def stopPassiveListen(self):
        """
        Stop passive listening
        """
        self.stop_passive = True

    def passiveListen(self, PERSONA):
        """
        Listens for PERSONA in everyday sound. Times out after LISTEN_TIME, so
        needs to be restarted.
        """
        self.passiveLock.acquire();
        transcribed = self.passiveText;
        if transcribed is not None and \
           any(PERSONA in phrase for phrase in transcribed):
            return 200, PERSONA

        return False, transcribed

    def activeListen(self, THRESHOLD=None, LISTEN=True,
                                 MUSIC=False):
        self.longVoiceLock.acquire();


    def getTextFromListen(self):
        self.sttLongTextLock.acquire();
        longVoiceText = self.longVoiceText;
        self.longVoiceText = "";
        return longVoiceText;

    def say(self, phrase,
            OPTIONS=" -vdefault+m3 -p 40 -s 160 --stdout > say.wav",
            cache=False):
        pixels.speak()
        self._logger.info(u"机器人说：%s" % phrase)
        self.stop_passive = True
        if self.wxbot is not None:
            wechatUser(config.get(), self.wxbot, "%s: %s" %
                       (self.robot_name, phrase), "")
        # incase calling say() method which
        # have not implement cache feature yet.
        # the count of args should be 3.
        self._logger.info("start to say something ...")
        if self.speaker.say.__code__.co_argcount > 2:
            self.speaker.say(phrase, cache)
        else:
            self.speaker.say(phrase)
        self._logger.info("say something end ...")
        time.sleep(0.1)  # 避免叮当说话时误唤醒
        self.stop_passive = False

    def play(self, src):
        # play a voice
        self.speaker.play(src)
