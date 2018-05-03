import RPi.GPIO as GPIO
import time
import threading
try:
    import queue as Queue
except ImportError:
    import Queue as Queue


class Pixels:
    def __init__(self, gpio_mode, pin):
        self.led_pin = pin
        GPIO.setwarnings(False)
        if gpio_mode == 'bcm':
            GPIO.setmode(GPIO.BCM)
        else:
            GPIO.setmode(GPIO.BOARD)
        GPIO.setup(pin, GPIO.OUT)

        self.next = threading.Event()
        self.queue = Queue.Queue()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def wakeup(self, direction=0):
        def f():
            self._wakeup(direction)

        self.next.set()
        self.queue.put(f)

    def listen(self):
        self.next.set()
        self.queue.put(self._listen)

    def think(self):
        self.next.set()
        self.queue.put(self._think)

    def speak(self):
        self.next.set()
        self.queue.put(self._speak)

    def off(self):
        self.next.set()
        self.queue.put(self._off)

    def _run(self):
        while True:
            func = self.queue.get()
            func()

    def _wakeup(self, direction=0):
        GPIO.output(self.led_pin, GPIO.HIGH)

    def _listen(self):
        GPIO.output(self.led_pin, GPIO.HIGH)

    def _think(self):
        self.next.clear()
        while not self.next.is_set():
            GPIO.output(self.led_pin, GPIO.HIGH)
            time.sleep(0.3)
            GPIO.output(self.led_pin, GPIO.LOW)
            time.sleep(0.3)

    def _speak(self):
        self.next.clear()
        while not self.next.is_set():
            GPIO.output(self.led_pin, GPIO.HIGH)
            time.sleep(0.3)
            GPIO.output(self.led_pin, GPIO.LOW)
            time.sleep(0.3)

        self._off()

    def _off(self):
        GPIO.output(self.led_pin, GPIO.LOW)


if __name__ == '__main__':
    while True:
        try:
            pixels = Pixels("bcm", 24)
            pixels.wakeup()
            time.sleep(3)
            pixels.think()
            time.sleep(3)
            pixels.speak()
            time.sleep(3)
            pixels.off()
            time.sleep(3)
        except KeyboardInterrupt:
            break

    pixels.off()
    time.sleep(1)
