import cv2
import pickle
import numpy as np
from queue import Queue

inf = 2147483647
models = pickle.load(open('models.pck', 'rb'))


def bfs(img, flag, i, j):
    ways = ((-1, 0), (1, 0), (0, -1), (0, 1))
    task = Queue()
    flag[i, j] = 1
    task.put((i, j))
    color: np.ndarray = img[i, j]
    min_i, max_i, min_j, max_j = inf, 0, inf, 0
    size = 0
    while task.qsize():
        ti, tj = task.get()
        size += 1
        min_i, max_i, min_j, max_j = min(min_i, ti), max(max_i, ti), min(min_j, tj), max(max_j, tj)
        for w in ways:
            ni, nj = ti+w[0], tj+w[1]
            if ni >= len(img) or ni < 0:
                continue
            if nj >= len(img[0]) or nj < 0:
                continue
            if not (all(img[ni, nj] == (255, 255, 255)) or flag[ni, nj]) and np.all(img[ni, nj] == color):
                flag[ni, nj] = 1
                task.put((ni, nj))
    if size < 20:
        return None
    return img[min_i:max_i+1, min_j:max_j+1]


def binary(img):
    count = {}
    for line in img:
        for px in line:
            c = [int(n) for n in px]
            key = c[0] << 16 | c[1] << 8 | c[2]
            if key == 16777215:
                continue
            if key not in count:
                count[key] = 0
            count[key] += 1
    color = ''
    count[''] = 0
    for n in count:
        if count[n] > count[color]:
            color = n
    color = np.array((color >> 16, color >> 8 & 0xff, color & 0xff))
    out = np.zeros((len(img), len(img[0]), 3), dtype=np.uint8)
    out[np.where(color != img)] = 255
    return out


def similarity(im1, im2):  # img, model
    im1 = im1[:, :, 0]
    im2 = cv2.resize(im2, (len(im1[0]), len(im1)), interpolation=cv2.INTER_LINEAR)[:, :, 0]
    sim = -int(np.sum(np.abs(im1-im2)))
    return sim


def detect(data):
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)  # 解码图片
    img = img[:, :-20]
    flag = np.zeros((len(img), len(img[0])), dtype=np.uint8)
    dec = []
    for j in range(len(img[0])):
        for i in range(len(img)):
            if not (all(img[i, j] == (255, 255, 255)) or flag[i, j]):
                sub = bfs(img, flag, i, j)
                if sub is not None:
                    dec.append(binary(sub))
    exp = ''
    for img in dec:
        sims = [(similarity(img, m), i) for i, m in enumerate(models)]
        exp += '1234567890-+'[sorted(sims)[-1][1]]
    try:
        return str(eval(exp))
    except Exception:
        return ''
