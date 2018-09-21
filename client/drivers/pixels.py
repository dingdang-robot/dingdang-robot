import math
import apa102
import time
import threading
from gpiozero import LED
try:
    import queue as Queue
except ImportError:
    import Queue as Queue


class Pixels:
    PIXELS_N = 12

    def __init__(self):
        self.basis = [0] * 3 * self.PIXELS_N

        self.colors = [0] * 3 * self.PIXELS_N
        self.dev = apa102.APA102(num_led=self.PIXELS_N)
        #self.dev.global_brightness = int(0b1111 * 0.7)
        self.next = threading.Event()
        self.queue = Queue.Queue()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        self.power = LED(5)
        self.power.on()
        self.write([0]*3*self.PIXELS_N)

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
        N = self.PIXELS_N;
        colors = [0, 120, 0]; 
        colors = colors * self.PIXELS_N;
        colors[15:18] = [120, 120, 120];
        for n in range(5, N + 5):
            i = n%12
            if i != N - 1:
                temp = colors[3*(i+1) : 3*(i+1)+3]
                colors[3*(i+1) : 3*(i+1)+3] = colors [3 * i : 3 * i + 3];
                colors[3*i : 3*i+3] = temp;
            else:
                temp = colors[3*(N-1):];
                colors[3*(N-1):] = colors[:3];
                colors[:3] = temp;

            self.write([v * math.sin(3.14 * i / N) for v in colors])
            time.sleep(0.04)

    def _listen(self):
        for i in range(1, 12):
            colors = [i * v for v in self.basis]
            self.write(colors)
            time.sleep(0.01)

        self.colors = colors

    def _think(self):
        seconds = 2;
        colors = [110, 0, 110] * self.PIXELS_N;
        for i in range(0, int(50 * seconds)):
            tempColors = [math.sin((i%50)*3.14/50) * v for v in colors];
            self.write(tempColors)
            time.sleep(0.04);
        
        # time.sleep(0.5)
        self.write([0]*3*self.PIXELS_N);
        #self.colors = colors

    def _speak(self):
        colors = self.colors

        self.next.clear()
        while not self.next.is_set():
            for i in range(5, 25):
                colors = [(v * i / 24) for v in colors]
                self.write(colors)
                time.sleep(0.01)

            time.sleep(0.3)

            for i in range(24, 4, -1):
                colors = [(v * i / 24) for v in colors]
                self.write(colors)
                time.sleep(0.01)

            time.sleep(0.3)

        self._off()

    def _off(self):
        self.write([0] * 3 * self.PIXELS_N)

    def write(self, colors):
        for i in range(self.PIXELS_N):
            self.dev.set_pixel(i, int(colors[3*i]), int(colors[3*i + 1]), int(colors[3*i + 2]))

        self.dev.show()


pixels = Pixels()


if __name__ == '__main__':
    i = 0;
    #pixels.wakeup()
    #print("wakeup")
    #time.sleep(3)
    pixels.think(5)
    print("think")
    time.sleep(3)
    #pixels.speak()
    print("speak")
    time.sleep(3)
    #pixels.off()
    print("off")
    time.sleep(3)

    pixels.off()
    time.sleep(1)
