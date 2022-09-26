from threading import Thread, Event, Lock
import time
from datetime import datetime
from pytz import timezone
import random

import cars_detector

"""
# cctv 가정
- 중앙선 기준 왼쪽 차만 파악
"""

"""
# 알고리즘
# 가정
- 차량과 보행자 고려
- 4차선 교차로, 한 방향에서만 신호를 받음
- 교차로 신호 주기 : 120초  / 기존교차로: 각 방향에 30초씩 배정
- 보행자 횡단보행시간 고려 (7초 + (1m당 1초) / 3m x 4라 가정, 19초) / 걸음속도 : 3.6km/h = 1m/s, 차로폭 : 3m
    >> 19초 -> 15초

- 차로 당 5초에 한 대씩 쌓임
- 2초에 한 대씩 빠질 수 있음

- 1사이클에 모든 방향이 보장되야 한다
** 차량이 없으면 생략 -> 보행자 문제가 생김 **

- Detection 방법
1. 영상처리
2. 주기적으로 처리 / ex) 2초마다, 5초마다 ...
3. 신호가 바뀌기 직전에 처리

https://www.pressian.com/pages/articles/185874
https://m.blog.naver.com/PostView.naver?isHttpsRedirect=true&blogId=hyjaeho&logNo=90195547390
"""


def get_nowtime():
    return datetime.now(timezone('Asia/Seoul')).strftime('20%y.%m.%d_%H:%M:%S')

# 한 방향
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

# 교차로
class Intersection:
    def __init__(self,det):
        self.__total_lanes = 4        # 4차로 -> 1방향당 2차로
        self.__signal_cycle = 120     # 신호 주기
        self.__crosswalk_time = 15    # 횡단보행시간, 원래는 19초 필요함
        self.__incoming_time = 5      # 차가 들어오는 시간  1대/5s
        self.__passing_time = 2       # 차가 나가는 시간    1대/2s
        self.__Way_lanes = self.__total_lanes // 2
        self.__det = det

        self.ways ={
            "East" : Way(self.__Way_lanes,self.__det[0]),
            "West" : Way(self.__Way_lanes,self.__det[1]),
            "South" : Way(self.__Way_lanes,self.__det[2]),
            "North" : Way(self.__Way_lanes,self.__det[3]),
        }
    
    def __repr__(self):
        return f"{self.__total_lanes}차선 교차로"
        
    def run(self):
        realtime_simulation = False # 중복실행 방지
        normal_simulation = False # 중복실행 방지
        text_correction = False

        print(f"({get_nowtime()})")
        while True: 
            tmp = "\n" if text_correction else ""
            if text_correction : text_correction = False
            user = input(ui + tmp)

            print(f"({get_nowtime()})",end=' ')
            # 실시간 교차로 시뮬레이션
            if user == '1':
                if normal_simulation:   # '기존 교차로 시뮬레이션'이 동작 중일 때 중복 실행제한
                    print("다른 시뮬레이션이 이미 실행중입니다.", end=' ')
                    print("종료 후 다시 눌러주세요.\n")
                    text_correction = True
                    continue
                if realtime_simulation:       # 2번째 눌렀을 때는 실행 종료
                    print("실시간 교차로 시뮬레이션을 종료합니다.\n")
                    simulate_event.set()
                    realtime_simulation = False
                    continue
                simulate_event = Event()
                simulate_thread = Thread(target=self.realtime_simulate,args=(simulate_event,),daemon=True)
                simulate_thread.start()
                realtime_simulation = True
                input("시뮬레이션이 정상 작동되었습니다.")

            # 기존 교차로 시뮬레이션
            elif user == '2':
                if realtime_simulation:     # '실시간 교차로 시뮬레이션'이 동작 중일 때 중복 실행제한
                    print("다른 시뮬레이션이 이미 실행중입니다.", end=' ')
                    print("종료 후 다시 눌러주세요.\n")
                    text_correction = True
                    continue
                if normal_simulation:       # 2번째 눌렀을 때는 실행 종료
                    print("기존 교차로 시뮬레이션을 종료합니다.\n")
                    simulate_event.set()
                    normal_simulation = False
                    continue
                simulate_event = Event()
                simulate_thread = Thread(target=self.normal_simulate,args=(simulate_event,),daemon=True)
                simulate_thread.start()
                normal_simulation = True
                input("시뮬레이션이 정상 작동되었습니다.")
            # 종료
            elif user == '3':
                if realtime_simulation or normal_simulation:
                    simulate_event.set()
                break
            else:
                print("1~3까지의 숫자만 입력해주세요.\n")
                continue
        
        print("프로그램 종료\n")

    def realtime_simulate(self,simulate_event):
        event = Event() # 스레드 종료조건
        threads = [Thread(target=self.ways[way].incoming_cars,args=(self.__incoming_time, event),daemon=True) for way in self.ways]
        for thread in threads:
            thread.start()

        print("\n\nRealtime simulation starts...")
        for name, way in self.ways.items():
            print(f"{name}\t: {way}")
        print()

        count = 1
        print(f"1 cycle : {self.__signal_cycle}s")
        while not simulate_event.is_set():
            print(f"========{count} cycle========")
            self.realtime_update(simulate_event)
            count += 1
        event.set()

    def realtime_update(self,simulate_event):
        tags = ('East','West','South','North')
        
        # 1 Cycle
        used_way = []
        this_cycle = self.__signal_cycle                    # 1사이클 필요 시간
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

            print(f"----------{5-i}th----------")
            print(f"target:{target_way}, Lights on:{target_time}s, extra_time:{extra_time}s")

            timer_start = time.time()
            # 해당 방향은 초록불인 상태
            while True:
                if simulate_event.is_set():
                    break
                timer_end = time.time()
                # 정해진 시간만큼 동작하도록, 타이머 이용
                if timer_end - timer_start >= target_time:
                    break
                
                self.ways[target_way].remove_cars(self.__Way_lanes)
                time.sleep(2)
            
            if simulate_event.is_set():
                break
            
            print(f"results ({get_nowtime()})")
            for name, way in self.ways.items():
                print(f"{name}\t: {way}")
            print(f"남은 시간 : {this_cycle}s")
            print("-----------------------")
            print()
            
            used_way.append(target_way)

        used_way.clear()

    def normal_simulate(self,simulate_event):
        event = Event() # 스레드 종료조건
        threads = [Thread(target=self.ways[way].incoming_cars,args=(self.__incoming_time, event),daemon=True) for way in self.ways]
        for thread in threads:
            thread.start()

        print("\n\nNormal simulation starts...")
        for name, way in self.ways.items():
            print(f"{name}\t: {way}")
        print()

        count = 1
        print(f"1 cycle : {self.__signal_cycle}s")
        while not simulate_event.is_set():
            print(f"========{count} cycle========")
            self.normal_update(simulate_event)

            count += 1
        event.set()

    def normal_update(self,simulate_event):
        tags = ('East','West','South','North')
        
        # 1 Cycle
        this_cycle = self.__signal_cycle # 1사이클 필요 시간
        for i in range(4):
            target_way = tags[i]
            target_time = self.__signal_cycle // 4
            this_cycle -= target_time

            print(f"----------{i+1}th----------")
            print(f"target:{target_way}, Lights on:{target_time}s")

            timer_start = time.time()
            # 해당 방향은 초록불인 상태
            while True:
                if simulate_event.is_set():
                    break
                timer_end = time.time()
                # 정해진 시간만큼 동작하도록, 타이머 이용
                if timer_end - timer_start >= target_time:
                    break
                
                self.ways[target_way].remove_cars(self.__Way_lanes)
                time.sleep(2)
            
            if simulate_event.is_set():
                break
            
            print(f"results ({get_nowtime()})")
            for name, way in self.ways.items():
                print(f"{name}\t: {way}")
            print(f"남은 시간 : {this_cycle}s")
            print("-----------------------")
            print()

    

def main():

    inter = Intersection()
    inter.run()

if __name__ == '__main__':
    print("Colab에서 실행할때 첫 실행은 정상이지만,")
    print("두 번째 실행시 스레드가 완전히 없어지지 않기 때문에")
    print("런타임 연결 해제후 다시 실행하면 정상작동 합니다.\n")
    
    ui = """### 시뮬레이션 프로그램 ###
1. 실시간 교차로
2. 기존 교차로
3. 종료
###########################
입력 >> """
    main()