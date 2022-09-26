import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtTest import *
from PyQt5 import uic
import sys
from PyQt5.QtWidgets import * 
from PyQt5 import uic, QtGui, QtCore, QtWidgets
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QSize, Qt
import os
import PyQt5
import cars_detector as c_d
import cv2
import threading
from time import sleep
import cars_detector
import time
# For Simulation
import random
from threading import Lock

class Way:
    def __init__(self, lanes, det=0):
        if lanes < 1:
            return
        self.__lanes = lanes

        self.cars = {f"{i+1}차선": int(det/lanes) for i in range(lanes)}
        self.lock = Lock()
    
    def __repr__(self):
        return f"{self.total_cars()} cars"
    
    def total_cars(self):
        return sum(self.cars.values())
    
    def remove_cars(self, num):
        self.lock.acquire()
        for key in self.cars:
            self.cars[key] = max(self.cars[key]-num , 0)
        self.lock.release()

    def incoming_cars(self, incoming_time, event):
        while True:
            if event.is_set():
                break
            self.lock.acquire()
            for key in self.cars:
                self.cars[key] += 1            # 5초에 한번씩 갱신
            self.lock.release()
            time.sleep(incoming_time)           # 5초마다 차가 추가된다고 가정
    
    def incoming_cars_timer(self):
        # 5초에 한번씩 갱신
        self.lock.acquire()
        # 랜덤으로 한 차로에 차를 추가함
        # for key in self.cars:
        #     self.cars[key] += 1 
        line = random.choice(list(self.cars.keys()))
        self.cars[line] += random.randint(0,2)
        self.lock.release()
    
    def remove_cars_timer(self):
        self.lock.acquire()
        for key in self.cars:
            self.cars[key] = max(self.cars[key]-1 , 0)
        self.lock.release()


global running 
global car
car = [0,0,0,0]
form_class = uic.loadUiType("test4.ui")[0]
form_class1 = uic.loadUiType("test_page_copy.ui")[0]

class MyWindow(QMainWindow,QWidget, form_class):
    def __init__(self):
        # GUI __init__
        super(MyWindow,self).__init__()
        self.setupUi(self)
        self.page_2.clicked.connect(self.Home)
        

        # 타이머 1분마다 갱신
        self.nowtimer = QTimer(self)
        self.nowtimer.start(1000)
        self.nowtimer.timeout.connect(self.display_nowtime)

        self.pushButton_1.clicked.connect(self.btn_clicked_1)
        self.pushButton_2.clicked.connect(self.btn_clicked_2)
        self.pushButton_3.clicked.connect(self.btn_clicked_3)
        self.Intersection_init()

    def Intersection_init(self):
        self.__total_lanes = 4        # 4차로 -> 1방향당 2차로
        self.__signal_cycle = 120     # 신호 주기
        self.__crosswalk_time = 15    # 횡단보행시간, 원래는 19초 필요함
        self.__incoming_time = 5      # 차가 들어오는 시간  1대/5s
        self.__passing_time = 2       # 차가 나가는 시간    1대/2s
        self.__Way_lanes = self.__total_lanes // 2

        self.realtime_simulation = False # 중복실행 방지
        self.normal_simulation = False # 중복실행 방지

        self.target_way = ''

        self.lcdNumber_ways = {
            "East" : self.lcdNumber_East,
            "West" : self.lcdNumber_West,
            "South" : self.lcdNumber_South,
            "North" : self.lcdNumber_North,
            }
        self.trafficlight_ways = {
            "East" : self.label_East_trafficlight,
            "West" : self.label_West_trafficlight,
            "South" : self.label_South_trafficlight,
            "North" : self.label_North_trafficlight,
        }

    def Home(self):
        global cars
        self.close()
        self.first = WindowClass()
        self.first.show()
    # 왼쪽 하단 & 중앙에 시간 보여주기
    def display_nowtime(self):
        cur_time = QTime.currentTime()
        str_time = cur_time.toString("hh:mm:ss")
        # self.statusBar().showMessage(str_time)
        self.label_datetime.setText(str_time)
    
    # 차 늘려주기
    def add_cars(self):
        if self.realtime_simulation or self.normal_simulation:
            for way in self.ways.values():
                way.incoming_cars_timer()
    
    # 차 빼기
    def subtract_cars(self,way):
        if self.realtime_simulation or self.normal_simulation:
            self.ways[way].remove_cars(1)

    def display_4way(self):
        tags = ('East','West','South','North')
        
        for tag in tags:
            total_car = self.ways[tag].total_cars()
            if total_car > 15:
                self.lcdNumber_ways[tag].setStyleSheet("color: red;" "background: transparent;" "border-style: solid;"
                                                        "border-width: 3px;" "border-color: #FA8072;" "border-radius: 3px")
            else:
                self.lcdNumber_ways[tag].setStyleSheet("color: green;" "background: transparent;")
            
            self.lcdNumber_ways[tag].display(self.ways[tag].total_cars())
    
    def display_trafficlights(self, target_way):
        tags = ('East','West','South','North')
        for tag in tags:
            if tag == target_way:
                self.trafficlight_ways[tag].setStyleSheet("background:transparent;" "border-radius:5px;"
                    f"background:url(:/TrafficLight/TrafficLight/{tag}/{tag}_TrafficLight_Green.png);")
            else:
                self.trafficlight_ways[tag].setStyleSheet("background:transparent;" "border-radius:5px;"
                    f"background:url(:/TrafficLight/TrafficLight/{tag}/{tag}_TrafficLight_Red.png);")

    def display_reset(self):
        tags = ('East','West','South','North')
        for tag in tags:
            self.trafficlight_ways[tag].setStyleSheet("background:transparent;" "border-radius:5px;"
                f"background:url(:/TrafficLight/TrafficLight/{tag}/{tag}_TrafficLight_Yellow.png);")
            self.lcdNumber_ways[tag].setStyleSheet("background: transparent;")
            self.lcdNumber_ways[tag].display(0)

    # 이벤트 처리 코드
    # 실시간 교차로 시뮬레이션
    def btn_clicked_1(self):
        cars = WindowClass.return_cars()
        if self.normal_simulation:
            text = "다른 시뮬레이션이 이미 실행중입니다.\n종료 후 다시 눌러주세요.\n"
            self.textBrowser_Main.setText(text)
            return

        if not self.realtime_simulation:
            self.textBrowser_Main.setText("실시간 교차로 시뮬레이션을 시작합니다.\n")
            self.pushButton_1.setText("실시간 교차로\n종료")
            self.realtime_simulation = True

            self.ways ={
                "East" : Way(self.__Way_lanes,cars[0]),
                "West" : Way(self.__Way_lanes,cars[1]),
                "South" : Way(self.__Way_lanes,cars[2]),
                "North" : Way(self.__Way_lanes,cars[3]),
            }
            self.pluscar = QTimer(self)
            self.pluscar.start(5000)    # 1s = 1000ms
            self.pluscar.timeout.connect(self.add_cars)

            self.display4 = QTimer(self)
            self.display4.start(1000)
            self.display4.timeout.connect(self.display_4way)
        
            ## 내용
            self.textBrowser_Main.clear()
            self.textBrowser_Main.append("Realtime simulation starts...")
            self.textBrowser_Main.append(f"1 cycle : {self.__signal_cycle}s\n")
            for name, way in self.ways.items():
                self.textBrowser_Main.append(f"{name}\t: {way}")
            self.textBrowser_Main.append("\n")

            QTimer.singleShot(0,self.realtime_update)

        else:       # 2번째 눌렀을 때는 실행 종료
            self.textBrowser_Main.setText("종료")
            self.pushButton_1.setText("실시간 교차로\n시작")
            self.realtime_simulation = False
            self.pluscar.stop()
            self.display4.stop()
            self.subtract_car.stop()
            self.display_reset()
            return

    # 기존 교차로 시뮬레이션
    def btn_clicked_2(self):
        if self.realtime_simulation:     # '실시간 교차로 시뮬레이션'이 동작 중일 때 중복 실행제한
            text = "다른 시뮬레이션이 이미 실행중입니다.\n종료 후 다시 눌러주세요.\n"
            self.textBrowser_Main.setText(text)
            return
        if not self.normal_simulation:       # 2번째 눌렀을 때는 실행 종료
            self.textBrowser_Main.setText("기존 교차로 시뮬레이션을 시작합니다.\n")
            self.pushButton_2.setText("기존 교차로\n종료")
            self.normal_simulation = True

            self.ways ={
                "East" : Way(self.__Way_lanes,random.randint(1,10)),
                "West" : Way(self.__Way_lanes,random.randint(1,10)),
                "South" : Way(self.__Way_lanes,random.randint(1,10)),
                "North" : Way(self.__Way_lanes,random.randint(1,10)),
            }
            self.pluscar = QTimer(self)
            self.pluscar.start(5000)    # 1s = 1000ms
            self.pluscar.timeout.connect(self.add_cars)

            self.display4 = QTimer(self)
            self.display4.start(2000)
            self.display4.timeout.connect(self.display_4way)
        
            ## 내용
            self.textBrowser_Main.clear()
            self.textBrowser_Main.append("Normal simulation starts...")
            self.textBrowser_Main.append(f"1 cycle : {self.__signal_cycle}s\n")
            for name, way in self.ways.items():
                self.textBrowser_Main.append(f"{name}\t: {way}")
            self.textBrowser_Main.append("\n")

            # Qthread 구간일듯
            QTimer.singleShot(0,self.normal_update)
        else:       # 2번째 눌렀을 때는 실행 종료
            self.textBrowser_Main.setText("종료")
            self.pushButton_2.setText("기존 교차로\n시작")
            self.normal_simulation = False
            self.pluscar.stop()
            self.display4.stop()
            self.subtract_car.stop()
            self.display_reset()
            return

    def realtime_update(self):
        tags = ('East','West','South','North')
        count = 1

        while self.realtime_simulation:
            self.textBrowser_Main.append(f"========{count} cycle========")

            used_way = []
            this_cycle = self.__signal_cycle # 1사이클 필요 시간
            extra_time = this_cycle - self.__crosswalk_time * 4 # 1사이클에 가질 수 있는 여분의 시간
            for i in range(4, 0, -1):
                # 네 방향에서 차량이 많은 순으로 정렬
                # 정렬후 중복되지 않게 최대치를 찾음
                tmp = {tag:self.ways[tag].total_cars() for tag in tags}
                tmp = list(tmp.items())
                sequence = sorted(tmp,key=lambda x:x[1],reverse=True)
                for seq in sequence:    # sequence는 튜플을 원소로 갖는 리스트 [('East', 4), ...]
                    if seq[0] in used_way:
                        continue
                    target_way = seq[0]
                    break
                """
                # 알고리즘 핵심
                - 한 방향이 초록불인 시간 = 최소치 + alpha, 최소치 = 횡단보행시간(self.__crosswalk_time)
                - 각 방향에 차가 1대도 없어도 15초의 신호를 준다    => 횡단보행을 고려해야함
                - 차가 많아도 1사이클(120초)를 넘기지 않고, 다른 방향에도 최소치를 보장하는 선에서 신호를 배분한다.
                """
                # self.label_sign(target_way)
                target_time = self.__crosswalk_time # 15초 -> 7.5 * 2 대 처리가능
                target_cars = self.ways[target_way].total_cars() # 현재 이차선에 있는 차량의 수
                needs = target_cars - self.__crosswalk_time * self.__Way_lanes / self.__passing_time    # 최소치만큼 시간을 줬을 때 남는 차량
                if needs > 0: # 차가 빠지는데 self.__crosswalk_time보다 더 필요할 경우
                    alpha = (needs / self.__Way_lanes) * self.__passing_time  # (남은 차량 / 차선) * (한차선에서 차가 빠지는 데 필요한 시간) => 추가로 필요한 시간
                    if extra_time >= 0 : # 여유시간이 있을 때 alpha를 더함 없으면 무시
                        alpha = min(alpha, extra_time)
                        target_time += alpha
                        extra_time = max(extra_time - alpha, 0)
                this_cycle -= target_time

                self.textBrowser_Main.append(f"----------{5-i}th----------")
                self.textBrowser_Main.append(QTime.currentTime().toString("(hh:mm:ss)"))
                self.textBrowser_Main.append(f"target:{target_way}, Lights on:{target_time}s\nextra_time:{extra_time}s")

                self.subtract_car = QTimer(self)
                self.subtract_car.start(self.__passing_time * 1000)    # 1s = 1000ms
                self.subtract_car.timeout.connect(lambda: self.subtract_cars(target_way))
                
                self.display_trafficlights(target_way)
                QTest.qWait(int(target_time * 1000))
                self.subtract_car.stop()
                
                if not self.realtime_simulation: break
                
                for name, way in self.ways.items():
                    self.textBrowser_Main.append(f"{name}\t: {way}")
                self.textBrowser_Main.append(f"남은 시간 : {this_cycle}s")
                self.textBrowser_Main.append("-----------------------\n")
                used_way.append(target_way)

            if not self.realtime_simulation: break

            count += 1
            used_way.clear()

    def normal_update(self):
        tags = ('East','West','South','North')
        count = 1

        while self.normal_simulation:
            self.textBrowser_Main.append(f"========{count} cycle========")

            this_cycle = self.__signal_cycle # 1사이클 필요 시간
            for i in range(4):
                target_way = tags[i]
                target_time = self.__signal_cycle // 4
                this_cycle -= target_time

                self.textBrowser_Main.append(f"----------{i+1}th----------")
                self.textBrowser_Main.append(QTime.currentTime().toString("(hh:mm:ss)"))
                self.textBrowser_Main.append(f"target:{target_way}, Lights on:{target_time}s")

                self.subtract_car = QTimer(self)
                self.subtract_car.start(self.__passing_time * 1000)    # 1s = 1000ms
                self.subtract_car.timeout.connect(lambda: self.subtract_cars(target_way))

                self.display_trafficlights(target_way)
                QTest.qWait(int(target_time * 1000))
                self.subtract_car.stop()

                if not self.normal_simulation: break
                
                for name, way in self.ways.items():
                    self.textBrowser_Main.append(f"{name}\t: {way}")
                self.textBrowser_Main.append(f"남은 시간 : {this_cycle}s")
                self.textBrowser_Main.append("-----------------------\n")

            if not self.normal_simulation: break
            count += 1

    # 종료
    def btn_clicked_3(self):
        sys.exit()

    def get_nowtime(self):
        cur_time = QTime.currentTime()
        return cur_time.toString("(hh:mm:ss)")

class WindowClass(QMainWindow, form_class1):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.show()

    def initUI(self):
        self.setupUi(self)
        self.start_bt.clicked.connect(self.start)
        self.button_next.clicked.connect(self.button_Second)

    def button_Second(self):
        global cars
        self.stop()
        self.close()#메인 윈도우 숨김
        self.second = MyWindow()
        self.second.show() #두번째 창 닫으면 다시

    def run1(self):
        global running
        global car
        cap = cv2.VideoCapture('file2.mp4')
        while running:
            ret, src = cap.read()
            _,src[:,450:] = cv2.threshold(src[:,450:],127,255,cv2.THRESH_BINARY)
            det = cars_detector.detect(src)
            if det is not None:
                dst = cars_detector.draw_boxes(src, det)
                det_length = len(det)
            else:
                dst = src.copy()
                det_length = 0
            if car[0] < det_length:
                car[0] = det_length
            
            if ret:
                img = cv2.cvtColor(dst, cv2.COLOR_BGR2RGB)
                img = cv2.putText(img, str(det_length), color=(255,0,0),thickness=10,org= (550,450),fontScale=4,fontFace=cv2.FONT_HERSHEY_SIMPLEX)
                h, w, c = img.shape 
                qImg = QtGui.QImage(img.data, w, h, w*c, QtGui.QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qImg).scaledToWidth(500)
                self.label_pic1.setPixmap(pixmap)
            else:
                break
       

    def run2(self):
        global running
        global car
        cap = cv2.VideoCapture('file.mp4')
        
        while running:
            ret, src = cap.read()
            _,src[:,500:] = cv2.threshold(src[:,500:],127,255,cv2.THRESH_BINARY)
            det = cars_detector.detect(src)
            if det is not None:
                dst = cars_detector.draw_boxes(src, det)
                det_length = len(det)
            else:
                dst = src.copy()
                det_length = 0
            if car[1] < det_length:
                car[1] = det_length
            
            if ret:
                img = cv2.cvtColor(dst, cv2.COLOR_BGR2RGB)
                img = cv2.putText(img, str(det_length), color=(255,0,0),thickness=10,org= (550,450),fontScale=4,fontFace=cv2.FONT_HERSHEY_SIMPLEX)
                h, w, c = img.shape 
                qImg = QtGui.QImage(img.data, w, h, w*c, QtGui.QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qImg).scaledToWidth(500)
                self.label_pic2.setPixmap(pixmap)
            else:
                break
       
      

    def run3(self):
        global running
        global car
        cap = cv2.VideoCapture('file3.mp4')
        while running:
            ret, src = cap.read()
            _,src[:,450:] = cv2.threshold(src[:,450:],127,255,cv2.THRESH_BINARY)
            det = cars_detector.detect(src)
            if det is not None:
                dst = cars_detector.draw_boxes(src, det)
                det_length = len(det)
            else:
                dst = src.copy()
                det_length = 0
            
            if car[2] < det_length:
                car[2] = det_length
            if ret:
                img = cv2.cvtColor(dst, cv2.COLOR_BGR2RGB)
                img = cv2.putText(img, str(det_length), color=(255,0,0),thickness=10,org= (550,450),fontScale=4,fontFace=cv2.FONT_HERSHEY_SIMPLEX)
                h, w, c = img.shape 
                qImg = QtGui.QImage(img.data, w, h, w*c, QtGui.QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qImg).scaledToWidth(500)
                self.label_pic3.setPixmap(pixmap)
            else:
                break

    def run4(self):
        global running
        global car
        cap = cv2.VideoCapture('file4.mp4')
        while running:
            ret, src = cap.read()
            # _,src[:,500:] = cv2.threshold(src[:,500:],127,255,cv2.THRESH_BINARY)
            det = cars_detector.detect(src)
            if det is not None:
                dst = cars_detector.draw_boxes(src, det)
                det_length = len(det)
            else:
                dst = src.copy()
                det_length = 0
            if car[3] < det_length:
                car[3] = det_length
            
            if ret:
                img = cv2.cvtColor(dst, cv2.COLOR_BGR2RGB)
                img = cv2.putText(img, str(det_length), color=(255,0,0),thickness=10,org= (550,450),fontScale=4,fontFace=cv2.FONT_HERSHEY_SIMPLEX)
                h, w, c = img.shape 
                qImg = QtGui.QImage(img.data, w, h, w*c, QtGui.QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qImg).scaledToWidth(500)
                self.label_pic4.setPixmap(pixmap)
            else:
                break

        

    def stop(self):
        global running
        global car
        running = False
        # cars = [0,0,0,0]
        print("stopped..")

    def start(self):
        global running
        running = True
        self.th1 = threading.Thread(target=self.run1)
        self.th1.start()
        self.th2 = threading.Thread(target=self.run2)
        self.th2.start()
        self.th3 = threading.Thread(target=self.run3)
        self.th3.start()
        self.th4 = threading.Thread(target=self.run4)
        self.th4.start()
        print("started..")

    def onExit(self):
        print("exit")
        self.stop()

    def return_cars():
        return car

if __name__ =='__main__':

    app = QApplication(sys.argv)
    mainWindow = WindowClass()
    mainWindow.show()
    app.exec_()

# app = QApplication(sys.argv)
# app.exec_()