# -*- coding: utf-8-*-
import subprocess
import time

import logging
import wave
import threading
import tempfile
try:
    import pygame
    pygame.mixer.init(frequency=16000)
except ImportError:
    pass

_logger = logging.getLogger(__name__)
_sound_instance = None
_music_instance = None

# the vlc.MediaPlayer can't free memory automatically,
# must use only one instance
_vlc_media_player = None


class AbstractSoundPlayer(threading.Thread):

    def __init__(self, **kwargs):
        super(AbstractSoundPlayer, self).__init__()

    def play(self):
        pass

    def play_block(self):
        pass

    def stop(self):
        pass

    def is_playing(self):
        return False


class AudioSoundPlayer(AbstractSoundPlayer):
    SLUG = 'pyaudio'

    def __init__(self, src, audio=None, **kwargs):
        import pyaudio
        super(AudioSoundPlayer, self).__init__(**kwargs)
        if not audio:
            self.audio = pyaudio.PyAudio()
        else:
            self.audio = audio
        self.src = src
        self.playing = False
        self.stop = False

    def run(self):
        # play a voice
        CHUNK = 1024

        _logger.debug("playing wave %s", self.src)
        f = wave.open(self.src, "rb")
        stream = self.audio.open(
            format=self.audio.get_format_from_width(f.getsampwidth()),
            channels=f.getnchannels(),
            rate=f.getframerate(),
            output=True)

        self.playing = True
        data = f.readframes(CHUNK)
        while data and not self.stop:
            stream.write(data)
            data = f.readframes(CHUNK)

        self.playing = False
        stream.stop_stream()
        stream.close()

    def play(self):
        self.start()

    def play_block(self):
        self.run()

    def stop(self):
        self.stop = True

    def is_playing(self):
        return self.playing


class ShellSoundPlayer(AbstractSoundPlayer):
    SLUG = 'aplay'

    def __init__(self, src, **kwargs):
        super(ShellSoundPlayer, self).__init__(**kwargs)
        self.src = src
        self.playing = False
        self.pipe = None

    def run(self):
        # play a voice
        cmd = ['aplay', '-q', str(self.src)]
        _logger.debug('Executing %s', ' '.join(cmd))

        self.pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
        self.playing = True
        # while self.pipe.poll():
        #     time.sleep(0.1)
        self.pipe.wait()
        self.playing = False
        output = self.pipe.stdout.read()
        if output:
            _logger.debug("play Output was: '%s'", output)
        error = self.pipe.stderr.read()
        if error:
            _logger.error("play error: '%s'", error)

    def play(self):
        self.start()

    def play_block(self):
        self.run()

    def stop(self):
        if self.pipe:
            self.pipe.kill()

    def is_playing(self):
        return self.playing


class AbstractMusicPlayer(threading.Thread):

    def __init__(self, **kwargs):
        super(AbstractMusicPlayer, self).__init__()

    def play(self):
        pass

    def play_block(self):
        pass

    def stop(self):
        pass

    def is_playing(self):
        return False

    def pause(self):
        pass


class ShellMusicPlayer(AbstractMusicPlayer):
    SLUG = 'play'

    def __init__(self, src, **kwargs):
        super(ShellMusicPlayer, self).__init__(**kwargs)
        self.src = src
        self.playing = False
        self.pipe = None

    def run(self):
        cmd = ['play', str(self.src)]
        _logger.debug('Executing %s', ' '.join(cmd))

        with tempfile.TemporaryFile() as f:
            self.pipe = subprocess.Popen(cmd, stdout=f, stderr=f)
            self.playing = True
            self.pipe.wait()
            self.playing = False
            f.seek(0)
            output = f.read()
            if output:
                _logger.debug("play Output was: '%s'", output)

    def play(self):
        self.start()

    def play_block(self):
        self.run()

    def stop(self):
        if self.pipe:
            self.pipe.kill()

    def is_playing(self):
        return self.playing


class VlcMusicPlayer(AbstractMusicPlayer):
    SLUG = 'vlc'

    def __init__(self, src, **kwargs):
        import vlc
        global _vlc_media_player
        super(VlcMusicPlayer, self).__init__(**kwargs)
        if not _vlc_media_player:
            _vlc_media_player = vlc.MediaPlayer()
        self.media_player = _vlc_media_player
        self.src = src
        self.media_player.set_media(vlc.Media(src))
        self.played = False

    def run(self):
        pass

    def play(self):
        _logger.debug('vlc play %s', self.src)
        self.played = True
        self.media_player.play()

    def play_block(self):
        _logger.debug('vlc play_block %s', self.src)
        self.media_player.play()
        time.sleep(0.4)
        while self.media_player.is_playing():
            time.sleep(0.1)

    def stop(self):
        self.media_player.stop()

    def is_playing(self):
        return self.media_player.is_playing() == 1

    def pause(self):
        self.media_player.pause()

    def wait(self):
        if self.played:
            time.sleep(0.4)
            while self.media_player.is_playing():
                time.sleep(0.1)


class PyGameMusicPlayer(AbstractMusicPlayer):
    SLUG = 'pygame'

    def __init__(self, src, **kwargs):
        import pygame
        super(PyGameMusicPlayer, self).__init__(**kwargs)
        self.src = src
        self.played = False
        pygame.mixer.music.load(self.src)
        self.paused = False

    def run(self):
        pass

    def play(self):
        _logger.debug('pygame play %s', self.src)
        self.played = True
        pygame.mixer.music.play()

    def play_block(self):
        _logger.debug('pygame play %s', self.src)
        self.played = True
        pygame.mixer.music.play()
        pygame.time.delay(200)
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

    def stop(self):
        pygame.mixer.music.stop()

    def is_playing(self):
        return pygame.mixer.music.get_busy()

    def pause(self):
        if not self.played:
            return
        if not self.paused:
            pygame.mixer.music.pause()
            self.paused = True
        else:
            pygame.mixer.music.unpause()
            self.paused = False

    def wait(self):
        if self.played:
            pygame.time.delay(200)
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)


class Sound(object):

    def __init__(self, slug, audio=None):
        for sound_engine in get_subclasses(AbstractSoundPlayer):
            if hasattr(sound_engine, 'SLUG') and sound_engine.SLUG == slug:
                self.slug = slug
                self.sound_engine = sound_engine
                break
        else:
            raise ValueError("No sound engine found for slug '%s'" % slug)
        self.audio = audio
        self.thread = None

    def play(self, src):
        self.thread = self.sound_engine(src, audio=self.audio)
        self.thread.play()

    def play_block(self, src):
        t = self.sound_engine(src, audio=self.audio)
        t.play_block()

    def wait(self):
        if self.thread:
            self.thread.join()

    def stop(self):
        if self.thread and self.thread.is_playing():
            self.thread.stop()


class Music(object):

    def __init__(self, slug):
        for music_engine in get_subclasses(AbstractMusicPlayer):
            if hasattr(music_engine, 'SLUG') and music_engine.SLUG == slug:
                self.slug = slug
                self.music_engine = music_engine
                break
        else:
            raise ValueError("No music engine found for slug '%s'" % slug)
        self.thread = None

    def play(self, src):
        self.thread = self.music_engine(src)
        self.thread.play()

    def play_block(self, src):
        t = self.music_engine(src)
        t.play_block()

    def wait(self):
        if self.thread:
            if hasattr(self.thread, 'wait'):
                self.thread.wait()
            else:
                self.thread.join()

    def stop(self):
        if self.thread and self.thread.is_playing():
            self.thread.stop()

    def pause(self):
        if self.thread:
            self.thread.pause()


def get_subclasses(cls):
    subclasses = set()
    for subclass in cls.__subclasses__():
        subclasses.add(subclass)
        subclasses.update(get_subclasses(subclass))
    return subclasses


def get_sound_manager(audio=None):
    from . import config
    global _sound_instance
    if not _sound_instance:
        _sound_instance = Sound(config.get('sound_engine', 'pyaudio'),
                                audio=audio)
    return _sound_instance


def get_music_manager():
    from . import config
    global _music_instance
    if not _music_instance:
        _music_instance = Music(config.get('music_engine', 'play'))
    return _music_instance
