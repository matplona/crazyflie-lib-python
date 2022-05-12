import socket
import threading
import time
import numpy as np
import cv2

from extension.decks.deck import Deck, DeckType

class ImgThread(threading.Thread):
    def __init__(self, socket, callback, timeout=-1, *args):
        threading.Thread.__init__(self)
        self.__socket = socket
        self.__callback = callback
        self.__callback_args = args
        self.__timeout = timeout
        self.__stopped = False

    def run(self):
        finish = time.time() + self.__timeout
        imgdata = None
        data_buffer = bytearray()
        while(1):
            # if timeout is set and expired or stream is stopped
            if((self.__timeout > 0 and time.time() > finish) or self.__stopped):
                break
            # Reveive image data from the AI-deck
            data_buffer.extend(self.__socket.recv(512))

            # Look for start-of-frame and end-of-frame
            start_idx = data_buffer.find(b"\xff\xd8")
            end_idx = data_buffer.find(b"\xff\xd9")

            # At startup we might get an end before we get the first start, if
            # that is the case then throw away the data before start
            if end_idx > -1 and end_idx < start_idx:
                data_buffer = data_buffer[start_idx:]

            # We have a start and an end of the image in the buffer now
            if start_idx > -1 and end_idx > -1 and end_idx > start_idx:
                # Pick out the image to render ...
                imgdata = data_buffer[start_idx:end_idx + 2]
                # .. and remove it from the buffer
                data_buffer = data_buffer[end_idx + 2 :]

                # callback the handler providing image and additional parameters
                self.__callback(imgdata, *self.__callback_args)

    def stop(self):
        self.__stopped = True

class AiDeck(Deck):
    def __init__(self, port=5000, ip="192.168.4.1") -> None:
        super().__init__(DeckType.bcAI) #initialize super
        self.__port = port
        self.__ip = ip
        self.__socket : socket.socket = None
        self.__connect() # connect to the drone

    def __connect(self) -> None:
        print("Connecting to socket on {}:{}...".format(self.__ip, self.__port))
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.settimeout(10)
        try:
            self.__socket.connect((self.__ip, self.__port))
            print("Socket connected")
        except:
            print("Socket not connected")
            self.__socket = None

    def show_recording(self, filename=False):
        if not filename:
            try:
                filename = self.__filename
            except:
                print("Error, provide a filename or record a video before showing it")
                return
        cap = cv2.VideoCapture(filename)
        if (cap.isOpened()== False):
            print("Error opening video file")
            return()
        fps = cap.get(cv2.CAP_PROP_FPS)
        period = int(1000//fps)
        while(cap.isOpened()):
            ret, frame = cap.read()
            if ret == True:                
                cv2.imshow("{}@{}fps".format(filename,fps),frame)
                cv2.waitKey(period)
            else:
                break
        cap.release()
        cv2.destroyAllWindows()

    def record(self, seconds=30, path="recordings/", name=None, format=".mp4"):
        if not self.__socket:
            print("Socket not connected, connect to the drone to record")
            return
        if seconds <= 0:
            seconds = 1 # minimum time of recording
        self.__img_array = []
        img_reader = ImgThread(self.__socket, self._add_frame, timeout=seconds)
        img_reader.start()
        img_reader.join() # at this point we have all the Images saved in the self.__img_array

        # consistency check:
        if len(self.__img_array) <= 0:
            print("Error, recording is empty, plase reboot the drone")
            return
        
        # get the fps of the video
        self.__fps = len(self.__img_array) / seconds

        # get the real size of the first frame
        h, w = cv2.imdecode(np.frombuffer(self.__img_array[0], np.uint8), 0).shape
        size = (w, h)
        if not name:
            # if name is unset give the default value using CET datetime
            name = time.strftime("%d-%m-%Y_%H-%M", time.gmtime(time.time() + 3600))

        fourcc = cv2.VideoWriter_fourcc(*'mp4v') # default mp4 format
        if format == ".avi":
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')

        self.__filename = "{}{}{}".format(path, name, format)
        print("Saving file @ {} fps:{} frames:{}".format(self.__filename,self.__fps,len(self.__img_array)))
        video = cv2.VideoWriter(self.__filename,fourcc, self.__fps, size, isColor=False)
        # add all frame to the video
        for img in self.__img_array:
            frame = cv2.imdecode(np.frombuffer(img, np.uint8), 0)
            video.write(frame)
        video.release()
        cv2.destroyAllWindows()

    def _add_frame(self, frame):
        self.__img_array.append(frame)

    def run_ai(self, algo, *args):
        if not self.__socket:
            print("Socket not connected, connect to the drone to start the video stream")
            return
        self.__start_stream(algo, *args)
    
    def __start_stream(self, callback, *args):
        self.__stream = ImgThread(self.__socket, callback, *args)
        self.__stream.start()
    
    def stop_ai(self):
        if not self.__stream:
            print("Error, run ai before stopping it")
            return
        self.__stream.stop()
        self.__stream.join()