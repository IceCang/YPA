import sys
import json
import time
import pyzstd
import websocket
import threading
from PIL import Image
import random
# import pygame

headers = {"Content-Type": "application/json",
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0"
                         ".0.0 Safari/537.36"}

board = []
goal = []
updates = []  # For surface
tokensAvailable = 0
paintSuccess = 0
correct = 0
total = 0
stop = 0

# pygame.init()
# SCREEN = pygame.display.set_mode((1000, 600))
# pygame.display.set_caption("Yur PaintBoard Viewer")
# SCREEN.fill((255, 255, 255))


def fill_board():
    global board
    global goal
    for i in range(1000):
        l = []
        for j in range(600):
            l.append(0)
        board.append(l)


def fill_goal():
    global goal
    for i in range(1000):
        l = []
        for j in range(600):
            l.append(0)
        goal.append(l)


def set_board(bd):
    global board
    idx = 0
    for i in range(1000):
        for j in range(600):
            board[i][j] = tuple(bd[idx:(idx + 3)])
            # SCREEN.set_at((i, j), tuple(bd[idx:(idx + 3)]))
            idx += 3
    # pygame.display.flip()
    # test_write_image()


def update_board(x, y, c):
    board[x][y] = c
    updates.append((x, y, c))


def put_board(ws: websocket.WebSocketApp, x, y, c):
    msg = b'\xfe'
    msg += bytes([x % 256, x // 256 % 256])
    msg += bytes([y % 256, y // 256 % 256])
    msg += bytes(c)
    try:
        ws.send(msg, websocket.ABNF.OPCODE_BINARY)
    except:
        return False
    return True


mainWorker = None


def log(typ, wid, message):
    if typ == 0:
        print("%s [Worker Thread #%d SUCCESS]: \033[32m%s\033[0m" % (
            time.asctime(time.localtime(time.time())), wid, message))
    elif typ == 1:
        print("%s [Worker Thread #%d INFO]: %s" % (time.asctime(time.localtime(time.time())), wid, message))
    elif typ == 2:
        print("%s [Worker Thread #%d ERROR]: \033[31m%s\033[0m" % (
            time.asctime(time.localtime(time.time())), wid, message))


class Worker:
    # ,{"x":500,"y":250,"path":"sun.jpg"}
    def __init__(self, token, main, id) -> None:

        global mainWorker
        self.token = token
        self.main = main
        self.id = id
        self.startSec = 0
        self.running = False
        self.firstLaunch = True
        self.ws = websocket.WebSocketApp('wss://paint.yurzhang.com/ws',
                                         on_open=self.on_open, on_message=self.on_message, on_error=self.on_error)
        if self.main:
            mainWorker = self
        self.ws.run_forever()

    def paint(self, ws: websocket.WebSocketApp):
        global cnt
        global paintQueue
        global lock
        global paintSuccess
        while True:
            try:
                if stop == 1:
                    sys.exit(0)
                if lock == 0:
                    time.sleep(0.3)
                    continue
                if cnt == 0:
                    if put_board(ws, 999, 599, (0, 0, 0)) is not True:
                        log(2, self.id, "Websocket Error. Reconnecting...")
                        self.running = False
                        time.sleep(1)
                        self.ws = websocket.WebSocketApp('wss://paint.yurzhang.com/ws',
                                                         on_open=self.on_open, on_message=self.on_message,
                                                         on_error=self.on_error)
                        self.ws.run_forever()
                        sys.exit(0)
                    else:
                        if isVerbose:
                            log(0, self.id, "Paint %d %d (%d, %d, %d) for lock" % (999, 599, 0, 0, 0))
                        time.sleep(0.1)
                        continue
                poi = paintQueue[0]
                paintQueue.remove(paintQueue[0])
                cnt -= 1
                stat = put_board(ws, poi[0], poi[1], poi[2])
                if stat is not True:
                    log(2, self.id, "Websocket Error. Reconnecting...")
                    self.running = False
                    time.sleep(1)
                    self.ws = websocket.WebSocketApp('wss://paint.yurzhang.com/ws',
                                                     on_open=self.on_open, on_message=self.on_message,
                                                     on_error=self.on_error)
                    self.ws.run_forever()
                    sys.exit(0)
                else:
                    paintSuccess += 1

                if isVerbose:
                    log(0, self.id, "Paint %d %d (%d, %d, %d) -> (%d, %d, %d) for %s" % (poi[0], poi[1],
                                                                                     board[poi[0]][poi[1]][0],
                                                                                     board[poi[0]][poi[1]][0],
                                                                                     board[poi[0]][poi[1]][0],
                                                                                     poi[2][0],
                                                                                     poi[2][1], poi[2][2], poi[3]))
                time.sleep(0.1)
            except IndexError:
                print("INDEXE")
                time.sleep(0.1)
                continue

    def on_open(self, ws: websocket.WebSocketApp):
        l = [255]
        for i in range(166):
            sl = self.token[i]
            l.append(ord(sl))
        ws.send(bytes(l), websocket.ABNF.OPCODE_BINARY)

    def on_message(self, ws: websocket.WebSocketApp, raw_msg):
        global tokensAvailable
        global lock
        msg_type, msg = raw_msg[0], raw_msg[1:]
        if msg_type == 251 and self.main is True:  # 0xfb
            lock = 0
            boarda = pyzstd.decompress(msg)
            log(0, self.id, len(boarda))
            set_board(boarda)
            lock = 1
            log(0, self.id, "Done " + '(' + str(time.time() - self.startSec) + 's)')
            if not self.running:
                t3 = threading.Thread(target=self.paint, args=(ws,), daemon=True)
                t3.start()
                self.running = True
            if self.firstLaunch:
                t4 = threading.Thread(target=run, daemon=True)
                t4.start()
                self.firstLaunch = False
        elif msg_type == 251:
            if not self.running:
                t3 = threading.Thread(target=self.paint, args=(ws,), daemon=True)
                t3.start()
                self.running = True
        elif msg_type == 250:
            if self.main:
                i = 0
                while i < len(msg):
                    x = msg[i + 1] * 256 + msg[i]
                    y = msg[i + 3] * 256 + msg[i + 2]
                    c = (msg[i + 4], msg[i + 5], msg[i + 6])
                    i += 7
                    update_board(x, y, c)
        elif msg_type == 253:
            log(2, self.id, 'Token error: ' + self.token)
            ws.close()
        elif msg_type == 252:
            tokensAvailable += 1
            if self.main:
                self.startSec = time.time()
                ws.send(bytes([249]), websocket.ABNF.OPCODE_BINARY)
            else:
                t3 = threading.Thread(target=self.paint, args=(ws,), daemon=True)
                t3.start()
                self.running = True
        elif msg_type == 248:
            ws.send(bytes([247]), websocket.ABNF.OPCODE_BINARY)

    def on_error(self, ws: websocket.WebSocketApp, err_msg):
        log(2, self.id, 'Error: ' + str(err_msg))
        ws.close()
        sys.exit(0)


sx, sy = 0, 0
# sx, sy = 600, 0
# sx, sy = 338, 0
cnt = 0
paintQueue = []
lock = 0
tokenNums = 0
tokens = []
imgConfig = {}
mods = 1.0
isShuffle = True
isVerbose = False
priTot = 0


def make_goal():
    global imgConfig
    global goal
    global total
    global stop
    global priTot
    try:
        fill_goal()
        priNow = -1
        for _p in imgConfig['images']:
            priNow += 1
            priTot += 1
            for _i in _p:
                img = Image.open(_i['path']).convert("RGB")
                for __i in range(img.size[0]):
                    for __j in range(img.size[1]):
                        if img.getpixel((__i, __j)) != (0, 255, 0):
                            goal[_i['x'] + __i][_i['y'] + __j] = (priNow, img.getpixel((__i, __j)))
        for _i in range(1000):
            for _j in range(600):
                if goal[_i][_j] != 0:
                    total += 1
    except:
        log(2, 1, "Failed to load images. Exiting...")
        stop = 1
        sys.exit(0)
    # print(goal)


def run():
    global cnt
    global lock
    global paintQueue
    global goal
    global paintSuccess
    global correct
    global total
    global stop
    global board
    global priTot
    global isShuffle
    try:
        make_goal()
        while True:
            if lock == 0:
                time.sleep(0.3)
                continue
            cachePri = []
            cachecnt = 0
            _correct = 0
            cache = []
            for _ in range(priTot):
                cachePri.append([])
            for _i in range(1000):
                for _j in range(600):
                    try:
                        if goal[_i][_j] == 0:
                            continue
                        if goal[_i][_j][1] != board[_i][_j]:
                            cachePri[goal[_i][_j][0]].append((_i, _j, goal[_i][_j][1], "paint"))
                            cachecnt += 1
                        else:
                            _correct += 1
                    except IndexError:
                        print(_i, _j)
                        sys.exit(0)
            if isShuffle:
                for _ in range(priTot):
                    random.shuffle(cachePri[_])
            for _ in cachePri:
                for __ in _:
                    cache.append(__)
            if (_correct - correct) / mods == 0:
                log(1, 1, "[Cycle] Queue Length: %d, Delta: %d, Success: %d, Wrong: %d, Correct: %d, Total: %d, ETC: %d"
                          "s" % (
                    len(cache), (correct - _correct + paintSuccess) / (mods / 0.1), paintSuccess, cachecnt, _correct, total, -1))
            else:
                log(1, 1, "[Cycle] Queue Length: %d, Delta: %d, Success: %d, Wrong: %d, Correct: %d, Total: %d, ETC: %d"
                          "s" % (len(cache), (correct - _correct + paintSuccess) / (mods / 0.1), paintSuccess,
                                 cachecnt, _correct, total, cachecnt /
                                 ((_correct - correct) / mods)))
            paintQueue = cache
            cnt = cachecnt
            correct = _correct
            paintSuccess = 0
            time.sleep(mods)
    except:
        log(2, 1, "Cycle ERROR!")
        stop = 1
        sys.exit(0)


def newWorker(token, main, id):
    Worker(token, main, id)


FPS = 120


def commandHandler():
    global mods
    global isShuffle
    global stop
    global isVerbose
    while True:
        cmd = input()
        if cmd.startswith(":!"):
            if cmd.split(' ')[0][2:] == "reload_board":
                mainWorker.ws.send(bytes([249]), websocket.ABNF.OPCODE_BINARY)
            elif cmd.split(' ')[0][2:] == "mode_sleep":
                mods = float(cmd[13:])
                log(0, 0, "Changed! %f" % float(cmd[13:]))
            elif cmd.split(' ')[0][2:] == "shuffle":
                if cmd[10:] == "on":
                    isShuffle = True
                    log(0, 0, "Shuffle On!")
                else:
                    isShuffle = False
                    log(0, 0, "Shuffle Off!")
            elif cmd.split(' ')[0][2:] == "stop":
                stop = 1
                log(1, 0, "STOPPING...")
                sys.exit(0)
            elif cmd.split(' ')[0][2:] == "verbose":
                if cmd.split(' ')[1] == "on":
                    isVerbose = True
                    log(0, 0, "Verbose On!")
                else:
                    isVerbose = False
                    log(0, 0, "Verbose Off!")
            else:
                log(2, 0, "Command Not Found!")


startType = 1

if __name__ == '__main__':
    while time.localtime().tm_hour < 15:
        time.sleep(1)
    startsec = time.time()
    log(1, 0, "Filling Board...")
    fill_board()
    # uid = int(input('uid:'))
    log(1, 0, "Loading Token And Image...")
    f = open('token.txt', 'r')
    tokenNums = int(f.readline())
    tokens = f.readlines()
    f1 = open('config.json', 'r')
    imgConfig = json.loads(f1.readline())
    log(1, 0, "Starting Worker Processes...")
    t = threading.Thread(target=newWorker, args=(tokens[0], True, 1,), daemon=True)
    t.start()
    time.sleep(0.500)
    for i in range(1, tokenNums):
        t1 = threading.Thread(target=newWorker, args=(tokens[i], False, i + 1,), daemon=True)
        t1.start()
        time.sleep(0.500/tokenNums)
    time.sleep(6.5)
    log(1, 0, "Done " + '(' + str(time.time() - startsec) + 's).')
    log(1, 0, "Loaded %d Token(s)." % tokensAvailable)
    tc = threading.Thread(target=commandHandler, daemon=True)
    tc.start()
    while True:
        # for event in pygame.event.get():
        #     if event.type == pygame.QUIT:
        #         pygame.quit()
        #         sys.exit(0)
        if stop == 1:
            exit(0)
        if time.localtime().tm_hour >= 20 and time.localtime().tm_min >= 1:
            stop = 1
            exit(0)
        # for item in updates:
        #     # SCREEN.set_at((item[0], item[1]), item[2])
        # pygame.display.update()
