import socket
import threading
import av
import io
import numpy as np
from djitellopy import Tello
import time
#import cv2
from PIL import Image

class Tello:
    def __init__(self, local_ip="0.0.0.0", local_port=8889, tello_ip="192.168.10.1", tello_port=8889, video_ip="192.168.10.1", video_port=11111, state_port=8890):
        self.local_ip = local_ip
        self.local_port = local_port
        self.tello_ip = tello_ip
        self.tello_port = tello_port
        self.video_ip = video_ip 
        self.video_port = video_port  # будет учитываться динамический
        self.state_port = state_port  

        self.response = None
        self.frame = None
        #self.is_freeze = False
        #self.last_frame = None
        self.dynamic_video_port = None  # ответ по поводу линамического порта

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
        self.socket_video = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  #пока
        self.socket_state = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
        self.socket_8899 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # также добавляем порт на 8899



        self.socket.bind((self.local_ip, self.local_port))  
        self.socket_video.bind((self.local_ip, self.video_port))  
        self.socket_state.bind((self.local_ip, self.state_port))  
        self.socket_8899.bind((self.local_ip, 8899))  #  слушаем порт 8899



        self.stop_event = threading.Event()
        self.receive_thread1 = threading.Thread(target=self.receive_thread)
        self.receive_thread1.daemon = True
        self.receive_thread1.start()

        self.receive_thread_video = threading.Thread(target=self.receive_video_thread)
        self.receive_thread_video.daemon = True
        self.receive_thread_video.start()

        self.receive_thread_state = threading.Thread(target=self.receive_state_thread)
        self.receive_thread_state.daemon = True
        self.receive_thread_state.start()

        self.receive_thread_8899 = threading.Thread(target=self.receive_8899_thread)
        self.receive_thread_8899.daemon = True
        self.receive_thread_8899.start()


    def __del__(self):
        self.socket.close()
        self.socket_video.close()
        self.socket_state.close()
        self.socket_8899.close()

    #def stop(self):
        #self.stop_event.set()
        #self.response_thread.join()
        #self.socket.close()

    def send_command(self, command):

        self.socket.sendto(command.encode('utf-8'), (self.tello_ip, self.tello_port))

    def receive_thread(self):

        while not self.stop_event.is_set():#True:
            try:
                self.response, _ = self.socket.recvfrom(1024)
                try:
                    decoded_response=self.response.decode("utf8",errors="ignore")

                    print("ответ", decoded_response)
                except socket.timeout:
                    pass
                except Exception as e:
                    print("не удалосб декодировать")

            except Exception as e:
                print("ошибка ответа от дрона", e)

    def receive_video_thread(self):

       
        #self.first_frame=False
        buffer = bytearray()#накапливаем данные, изменяемые
        self.socket_video.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2048) #буфер для сокета для видеопотока(размер) функция применяется к конкретному сокету
        #self.socket_video.timeout(0.5)

        

        try:
            while True: #not self.first_frame:

                packet, _ = self.socket_video.recvfrom(2048) 
                time.sleep(2)
                buffer.extend(packet) #добавляем пакеты в буфер

                if len(buffer)>2048*2:# достаточно ли данных для декодирования
                    try:

                #buffer.seek(0)  
                        buffer_new=io.BytesIO(buffer)#создаем поток с которым уже можно рабоать
                        container = av.open(buffer_new, format="h264")  

                        for frame in container.decode(video=0):
                            img = np.array(frame.to_image())  
                            if img is not None and img.size>0:

                    #if self.is_freeze:
                        #self.last_frame = img
                    #else:
                        #self.frame = img
                                self.frame=img
                                self.first_frame=True
                                print("сделали фото")
                                return
                    except Exception as e:
                        continue#print(f"Ошибка видео {e}")
                    break

                #buffer.seek(0)  
                #buffer.truncate()
        except Exception as e:
            print(f"Ошибка видео {e}")

    def receive_8899_thread(self): #обработка с порта 8899

        while True:
            try:
                data, _= self.socket_8899.recvfrom(2048)

                

                try:
                    decoded_data = data.decode('utf-8', errors='ignore')  # Игнор ошибок и бинар в текст
                    #print(f"кодек на порту 8899 {decoded_data}")
                except Exception as e:
                    print(f"ошибка кодека {e}")

            except Exception as e:
                print(f"не может принять порт 8899 {e}")


    def receive_state_thread(self):

        while self.dynamic_video_port is None:#True:
            try:
                state_data, _ = self.socket_state.recvfrom(2048) 
                #print("полученное состояние", state_data.decode())

 
                if "video_port" in state_data.decode():#получаем динамический порт из состояния (проверка есть ли упоминание видео порт в строке)
                    self.dynamic_video_port = int(state_data.decode().split(';')[1].split(':')[1])# превращаем нужный порт в число байтовых данных строке разделяем строку и получаем второй элемент-видео порт
                    print(f"динамический порт {self.dynamic_video_port}")
                        # в состоянии есть видео порт
            except Exception as e:
                print("ошибка ответа состояния", e)

    #def read_frames(self):

        return self.last_frame if self.is_freeze else self.frame

    #def freeze(self, is_freeze=True):

        self.is_freeze = is_freeze
        if is_freeze:
            self.last_frame = self.frame


tello = Tello()
tello.send_command("command")  
tello.send_command("streamoff")
time.sleep(1)
tello.send_command("streamon")  


while tello.dynamic_video_port is None:
    pass #ждем получения динамического порта


tello.socket_video = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tello.socket_video.bind((tello.local_ip, tello.dynamic_video_port)) #переместили видео на динамический порт



while tello.frame is None:
    print("жди")
    time.sleep(2)

if tello.frame is not None and tello.frame.size>0:

    image=Image.fromarray(tello.frame)
    image.save("photo.png")
    image.show()
    #cv2.imshow("photo", tello.frame)  
    #cv2.waitKey(0)  
    #cv2.destroyAllWindows()
else:
    print("нихуя")



