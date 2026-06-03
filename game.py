import pygame
import math
import random
import sys
import json
import os
import array

pygame.init()
try:
    pygame.mixer.quit()
    pygame.mixer.init(frequency=22050, size=-16, channels=1)
    pygame.mixer.set_num_channels(24)
    SOUND_OK=True
except Exception:
    SOUND_OK=False

GAME_VERSION = 8  # версия игры для синхронизации профиля

WIDTH, HEIGHT = 1100, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
pygame.display.set_caption("Матвей Рязанцев: Оборона башен")
clock = pygame.time.Clock()
FPS = 60

SAVE_FILE = "savegame.json"
PROFILE_FILE = "profile.json"
AUTOSAVE_SECONDS = 180

font_s = pygame.font.SysFont("arial", 16)
font_m = pygame.font.SysFont("arial", 22, bold=True)
font_l = pygame.font.SysFont("arial", 44, bold=True)
font_xl = pygame.font.SysFont("arial", 66, bold=True)  # крупный логотип-заголовок

WHITE=(240,240,240); BLACK=(15,15,20); GREEN=(60,200,80); RED=(220,50,50)
BLUE=(60,130,230); YELLOW=(245,220,60); GRAY=(120,120,130); DARK=(26,26,36)
ORANGE=(245,140,40); PURPLE=(170,70,210); CYAN=(110,210,255)
POISONC=(120,210,90); LIGHT=(210,214,230)
PATHCOL=(74,68,86); GRASS=(38,52,44); PANEL=(40,40,56)

# ================== СПРАЙТЫ И ТЕКСТУРЫ (пиксель-арт) ==================
# Все ассеты ищутся в папке assets/. Если файла нет — генерируется
# процедурная пиксель-арт текстура, поэтому игра красивая даже без картинок.
ASSET_DIR = "assets"

# ----- Авто-докачка картинок при запуске -----
# Пропиши прямые ссылки на свои PNG (проще всего — GitHub raw,
# ссылка вида https://raw.githubusercontent.com/<юзер>/<репо>/main/grass.png).
# Пустая строка "" = пропустить файл (будет процедурный фолбэк).
import urllib.request
ASSET_URLS = {
    "assets/grass.png": "",
    "assets/dirt.png": "",
    "weapon_pistol.png": "",
    "weapon_smg.png": "",
    "weapon_shotgun.png": "",
    "weapon_sniper.png": "",
    "weapon_minigun.png": "",
    "weapon_bazooka.png": "",
    "skin1.png": "",
    "skin2.png": "",
    "skin3.png": "",
    "skin4.png": "",
    "skin5.png": "",
    "menu.png": "",
    "assets/seller_andrey.png": "",
    "assets/seller_dima.png": "",
    "assets/hero.png": "",
    "assets/enemy.png": "",
    "assets/boss.png": "",
    "assets/turret_base.png": "",
    "assets/turret_cannon.png": "",
}

def ensure_assets():
    """Скачивает недостающие картинки по ссылкам из ASSET_URLS (один раз при запуске)."""
    for path, url in ASSET_URLS.items():
        if not url or os.path.exists(path):
            continue
        try:
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            print(f"Докачиваю {path} ...")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp, open(path, "wb") as f:
                f.write(resp.read())
        except Exception as ex:
            print(f"Не удалось скачать {path}: {ex} — будет процедурный фолбэк")

ensure_assets()

def load_asset(name, size=None, alpha=True):
    """Грузит картинку из assets/. Возвращает None, если файла нет."""
    path = os.path.join(ASSET_DIR, name)
    try:
        if os.path.exists(path):
            img = pygame.image.load(path)
            img = img.convert_alpha() if alpha else img.convert()
            if size: img = pygame.transform.scale(img, size)
            return img
    except Exception:
        pass
    return None

def draw_sprite(surf, image, x, y, angle=0.0, scale=1.0):
    """Рисует спрайт по центру (x,y) с поворотом на angle (в радианах)."""
    img = image
    if scale != 1.0:
        w, h = img.get_size()
        img = pygame.transform.smoothscale(img, (max(1,int(w*scale)), max(1,int(h*scale))))
    if angle:
        img = pygame.transform.rotate(img, -math.degrees(angle))
    surf.blit(img, img.get_rect(center=(int(x), int(y))))

def _px_noise(surf, colors, density, seed=1):
    """Накладывает пиксельный «шум» на поверхность (пиксель-арт фактура)."""
    w, h = surf.get_size(); rnd = random.Random(seed)
    for _ in range(int(w*h*density)):
        surf.set_at((rnd.randrange(w), rnd.randrange(h)), rnd.choice(colors))

def make_grass_tile(size=64):
    t = pygame.Surface((size, size))
    t.fill((46, 86, 54))
    _px_noise(t, [(40,76,48),(52,96,60),(58,106,66),(43,82,52)], 0.10, seed=7)
    rnd = random.Random(11)
    for _ in range(size//3):
        x, y = rnd.randrange(size), rnd.randrange(size)
        pygame.draw.line(t, (66,120,74), (x, y), (x, y-rnd.randint(2,4)))
    return t

def make_dirt_tile(size=64):
    t = pygame.Surface((size, size))
    t.fill((122, 96, 64))
    _px_noise(t, [(110,86,56),(134,106,72),(100,78,50),(140,114,80)], 0.12, seed=23)
    return t

GRASS_TILE = load_asset("grass.png", (64,64)) or make_grass_tile(64)
DIRT_TILE  = load_asset("dirt.png", (64,64)) or make_dirt_tile(64)
ANDREY_IMG = load_asset("seller_andrey.png", (54,54))  # PNG продавца (необязательно)
DIMA_IMG   = load_asset("seller_dima.png", (54,54))    # иначе рисуется примитив
HERO_SPRITE       = load_asset("hero.png", (40,40))    # вид сверху игрока (опц.)
ENEMY_IMG         = load_asset("enemy.png")            # спрайт обычного врага (опц.)
BOSS_IMG          = load_asset("boss.png")             # спрайт босса (опц.)
TURRET_BASE_IMG   = load_asset("turret_base.png")      # неподвижная база башни (опц.)
TURRET_CANNON_IMG = load_asset("turret_cannon.png")    # вращающаяся пушка башни (опц.)

# ----- Звуки (генерируются программно, файлы не нужны) -----
def make_tone(freq=440, ms=80, vol=0.4, kind="sine"):
    if not SOUND_OK:
        return None
    sr=22050; n=max(1,int(sr*ms/1000)); buf=array.array("h"); amp=int(32767*vol)
    for i in range(n):
        t=i/sr; env=max(0.0, 1.0 - i/n)
        s=random.uniform(-1,1) if kind=="noise" else math.sin(2*math.pi*freq*t)
        buf.append(max(-32767,min(32767,int(amp*env*s))))
    try:
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception:
        return None

def make_sound(ms=120, vol=0.3, f0=440, f1=None, kind="sine", attack=0.012, noise_mix=0.0, decay=3.2):
    """Мягкий синтезатор: плавная атака + экспоненциальный спад (БЕЗ щелчков),
    плавный глайд частоты f0→f1 и мягкие волны (треугольник/синус) вместо резкого шума."""
    if not SOUND_OK:
        return None
    sr=22050; n=max(1,int(sr*ms/1000)); buf=array.array("h"); amp=int(32767*vol)
    if f1 is None: f1=f0
    atk=max(1,int(n*attack)); phase=0.0
    for i in range(n):
        t=i/n
        freq=f0+(f1-f0)*t
        phase+=2*math.pi*freq/sr
        if kind=="triangle":
            s=2.0/math.pi*math.asin(max(-1.0,min(1.0,math.sin(phase))))
        elif kind=="square":
            s=0.7 if math.sin(phase)>=0 else -0.7
        elif kind=="noise":
            s=random.uniform(-1,1)
        else:
            s=math.sin(phase)
        if noise_mix>0:
            s=(1-noise_mix)*s+noise_mix*random.uniform(-1,1)
        env=(i/atk) if i<atk else math.exp(-decay*(i-atk)/max(1,(n-atk)))
        buf.append(max(-32767,min(32767,int(amp*env*s))))
    try:
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception:
        return None

# Мягкие, приятные звуки (без режущего шума и щелчков)
SND_HIT  = make_sound(ms=60,  vol=0.16, f0=900, f1=600, kind="triangle", attack=0.03)            # мягкий «ток»
SND_SHOOT= make_sound(ms=85,  vol=0.15, f0=720, f1=300, kind="triangle", attack=0.012, noise_mix=0.10)  # мягкий «pew»
SND_BOOM = make_sound(ms=320, vol=0.45, f0=140, f1=45,  kind="noise",    attack=0.006, decay=2.6)  # глубокий рокот
SND_HURT = make_sound(ms=170, vol=0.28, f0=240, f1=150, kind="sine",     attack=0.02)             # глухой удар
SND_BUY  = make_sound(ms=140, vol=0.24, f0=620, f1=950, kind="triangle", attack=0.02)             # приятная трель

# ----- Менеджер звуков (Sound Manager) -----
# Все звуки ПРЕДЗАГРУЖАЮТСЯ один раз при старте в словарь SOUNDS, поэтому
# воспроизведение по имени мгновенно и не вызывает подвисаний при выстреле.
SOUNDS = {
    "shoot": SND_SHOOT,
    "hit":   SND_HIT,
    "boom":  SND_BOOM,
    "hurt":  SND_HURT,
    "buy":   SND_BUY,
}
_last_play_ms = {}

def play(snd):
    if SOUND_OK and snd is not None and PROFILE.get("sound", True):
        try:
            snd.set_volume(PROFILE.get("volume", 0.7)); snd.play()
        except Exception: pass

def play_sound(name, throttle_ms=0):
    """Воспроизвести звук по имени: play_sound('shoot'/'hit'/'buy'/'boom'/'hurt').
    throttle_ms ограничивает частоту повтора (чтобы пулемёт/миниган не трещали сплошняком)."""
    snd = SOUNDS.get(name)
    if snd is None:
        return
    if throttle_ms > 0:
        now = pygame.time.get_ticks()
        if now - _last_play_ms.get(name, -99999) < throttle_ms:
            return
        _last_play_ms[name] = now
    play(snd)

def play_hit():
    play_sound("hit", throttle_ms=28)

# ----- Фон-фото для меню -----
MENU_BG = None
try:
    if os.path.exists("menu.png"):
        MENU_BG = pygame.image.load("menu.png").convert()
        MENU_BG = pygame.transform.scale(MENU_BG, (WIDTH, HEIGHT))
except Exception:
    MENU_BG = None

# ================== ПРОФИЛЬ И СКИНЫ ==================
SKIN_NAMES = ["Классический", "Скин 1", "Скин 2", "Скин 3", "Скин 4", "Скин 5"]
SKIN_FILES = [None, "skin1.png", "skin2.png", "skin3.png", "skin4.png", "skin5.png"]
NUM_SKINS = len(SKIN_NAMES)
SKIN_COST = 10
SKIN_HERO = [None]*NUM_SKINS
SKIN_PREVIEW = [None]*NUM_SKINS

def autocrop_image(img):
    """Обрезает белый/прозрачный фон вокруг лица, чтобы оно заполнило кружок."""
    img = img.convert_alpha()
    w, h = img.get_size()
    scale = 256.0 / max(w, h)
    sw, sh = max(1, int(w*scale)), max(1, int(h*scale))
    small = pygame.transform.smoothscale(img, (sw, sh))
    minx, miny, maxx, maxy = sw, sh, 0, 0
    found = False
    for yy in range(sh):
        for xx in range(sw):
            r, g, b, a = small.get_at((xx, yy))
            if a > 25 and not (r > 234 and g > 234 and b > 234):
                found = True
                if xx < minx: minx = xx
                if xx > maxx: maxx = xx
                if yy < miny: miny = yy
                if yy > maxy: maxy = yy
    if not found:
        return img
    pad = 4
    minx = max(0, minx-pad); miny = max(0, miny-pad)
    maxx = min(sw-1, maxx+pad); maxy = min(sh-1, maxy+pad)
    rx0 = int(minx/scale); ry0 = int(miny/scale)
    cw = max(1, int((maxx+1)/scale) - rx0); ch = max(1, int((maxy+1)/scale) - ry0)
    side = max(cw, ch)
    ccx = rx0 + cw//2; ccy = ry0 + ch//2
    sx = max(0, ccx - side//2); sy = max(0, ccy - side//2)
    side = min(side, w - sx, h - sy)
    crop = pygame.Surface((side, side), pygame.SRCALPHA)
    crop.blit(img, (0, 0), pygame.Rect(sx, sy, side, side))
    return crop

def make_circle_image(img, d):
    img = pygame.transform.smoothscale(img.convert_alpha(), (d, d))
    mask = pygame.Surface((d, d), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255,255,255,255), (d//2, d//2), d//2)
    res = img.copy()
    res.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
    return res

for i, fn in enumerate(SKIN_FILES):
    if fn and os.path.exists(fn):
        try:
            raw = pygame.image.load(fn)
            cropped = autocrop_image(raw)
            SKIN_HERO[i] = make_circle_image(cropped, 34)
            SKIN_PREVIEW[i] = make_circle_image(cropped, 100)
        except Exception:
            pass

PROFILE = {"version": GAME_VERSION, "coins": 0, "unlocked_skins": [0], "skin_idx": 0, "sound": True, "volume": 0.7, "achievements": []}

def load_profile():
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            PROFILE["coins"] = int(d.get("coins", 0))
            unlocked = [int(x) for x in d.get("unlocked_skins", [0])]
            if 0 not in unlocked: unlocked.append(0)
            PROFILE["unlocked_skins"] = sorted(set(unlocked))
            PROFILE["skin_idx"] = int(d.get("skin_idx", 0))
            PROFILE["sound"] = bool(d.get("sound", True))
            PROFILE["volume"] = float(d.get("volume", 0.7))
            PROFILE["achievements"] = list(d.get("achievements", []))
            if d.get("version", 1) != GAME_VERSION:
                PROFILE["version"] = GAME_VERSION
                save_profile()
        except Exception:
            pass
    if PROFILE["skin_idx"] not in PROFILE["unlocked_skins"] or PROFILE["skin_idx"] >= NUM_SKINS:
        PROFILE["skin_idx"] = 0

def save_profile():
    try:
        data = {"version": GAME_VERSION, "coins": PROFILE["coins"],
                "unlocked_skins": PROFILE["unlocked_skins"], "skin_idx": PROFILE["skin_idx"],
                "sound": PROFILE.get("sound", True), "volume": PROFILE.get("volume", 0.7),
                "achievements": PROFILE.get("achievements", [])}
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

load_profile()

# ----- Карты и Менеджер уровней -----
class LevelManager:
    """Система уровней. Чтобы добавить новую карту — просто вызови или
    add_level(имя, массив_точек_пути, позиция_Андрея, позиция_Димы), или добавь словарь в LEVELS_DATA."""
    def __init__(self, levels):
        self.levels=levels; self.current=0
    def __len__(self): return len(self.levels)
    def names(self): return [lv.get("name",f"Карта {i+1}") for i,lv in enumerate(self.levels)]
    def get(self, idx): return self.levels[idx % len(self.levels)]
    def add_level(self, name, path, andrey, dima):
        self.levels.append({"name":name,"path":path,"andrey":andrey,"dima":dima})
        return len(self.levels)-1
    def select(self, idx):
        self.current=idx % len(self.levels); return self.get(self.current)

LEVELS_DATA = [
    {"name":"Зелёная застава", "path": [(120,90),(1010,90),(1010,300),(430,300),(430,470),(1010,470),(1010,780)],
     "andrey": (300,630), "dima": (770,630)},
    {"name":"Двойная петля", "path": [(120,120),(950,120),(950,330),(150,330),(150,540),(1010,540),(1010,780)],
     "andrey": (330,660), "dima": (760,660)},
    {"name":"Лабиринт Шира", "path": [(120,90),(1010,90),(1010,250),(120,250),(120,410),(1010,410),(1010,560),(120,560),(120,780)],
     "andrey": (450,650), "dima": (800,650)},
]
LEVELS = LevelManager(LEVELS_DATA)
MAPS = LEVELS.levels   # обратная совместимость со старым кодом
PATH = MAPS[0]["path"]; ANDREY_POS = MAPS[0]["andrey"]; DIMA_POS = MAPS[0]["dima"]
PATH2 = []          # вторая дорожка (сверху), строится в set_map
PATHS = [PATH]       # все активные дорожки текущей карты
INTERACT_R = 80

BG_CACHE = None  # запечённый фон текущей карты (трава + тропинка)

def _tile_fill(surf, tile):
    tw, th = tile.get_size()
    for yy in range(0, surf.get_height(), th):
        for xx in range(0, surf.get_width(), tw):
            surf.blit(tile, (xx, yy))

def build_background():
    """Запекает фон карты: тайлы травы + ВСЕ тропинки (PATHS) с тенью. Рендерится 1 раз на карту."""
    global BG_CACHE
    bg = pygame.Surface((WIDTH, HEIGHT))
    _tile_fill(bg, GRASS_TILE)
    # мягкая тень-кайма под тропинками
    for _pth in PATHS:
        for i in range(len(_pth)-1):
            pygame.draw.line(bg, (28,40,30), _pth[i], _pth[i+1], 54)
        for p in _pth:
            pygame.draw.circle(bg, (28,40,30), p, 27)
    # сами тропинки — текстура земли, обрезанная по маске путей
    dirt = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    _tile_fill(dirt, DIRT_TILE)
    mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for _pth in PATHS:
        for i in range(len(_pth)-1):
            pygame.draw.line(mask, (255,255,255,255), _pth[i], _pth[i+1], 44)
        for p in _pth:
            pygame.draw.circle(mask, (255,255,255,255), p, 22)
    dirt.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
    bg.blit(dirt, (0,0))
    # светлая серединка тропинок для объёма
    for _pth in PATHS:
        for i in range(len(_pth)-1):
            pygame.draw.line(bg, (150,122,86), _pth[i], _pth[i+1], 6)
    BG_CACHE = bg

def set_map(idx):
    global PATH, PATH2, PATHS, ANDREY_POS, DIMA_POS
    m = MAPS[idx]
    PATH = m["path"]; ANDREY_POS = m["andrey"]; DIMA_POS = m["dima"]
    PATH2 = []
    PATHS = [PATH]
    build_background()

def dist(ax,ay,bx,by):
    return math.hypot(ax-bx, ay-by)

def point_seg_dist(px,py,ax,ay,bx,by):
    dx,dy = bx-ax, by-ay
    if dx==0 and dy==0:
        return dist(px,py,ax,ay)
    t = ((px-ax)*dx + (py-ay)*dy) / (dx*dx + dy*dy)
    t = max(0, min(1, t))
    return dist(px,py, ax+t*dx, ay+t*dy)

def near_path(x,y,margin=40):
    for _pth in PATHS:
        for i in range(len(_pth)-1):
            ax,ay = _pth[i]; bx,by = _pth[i+1]
            if point_seg_dist(x,y,ax,ay,bx,by) < margin:
                return True
    return False

def enemy_progress(e):
    """Насколько враг продвинулся по своему пути (больше = ближе к базе)."""
    pth=getattr(e,"path",PATH)
    p=e.idx
    if e.idx < len(pth)-1:
        ax,ay=pth[e.idx]; bx,by=pth[e.idx+1]
        seg=dist(ax,ay,bx,by)
        if seg>0:
            p+=min(1.0, dist(ax,ay,e.x,e.y)/seg)
    return p

# ----- Оружие (Андрей Кол): баланс + модельки + очереди -----
WEAPONS = {
    "Пистолет":         {"dmg":16, "cooldown":0.30,"speed":13,"pellets":1,"spread":0.0, "cost":0,  "color":YELLOW,"aoe":0, "gun_len":18,"gun_w":5},
    "Пистолет-пулемёт": {"dmg":13, "cooldown":0.62,"speed":15,"pellets":1,"spread":0.05,"cost":240,"color":(120,220,150),"aoe":0,"burst":3,"burst_gap":0.06,"gun_len":22,"gun_w":6},
    "Дробовик":         {"dmg":11, "cooldown":0.7, "speed":12,"pellets":8,"spread":0.38,"cost":340,"color":RED,   "aoe":0, "gun_len":20,"gun_w":9},
    "Снайперка":        {"dmg":120,"cooldown":1.1, "speed":28,"pellets":1,"spread":0.0, "cost":480,"color":CYAN,  "aoe":0, "gun_len":34,"gun_w":4},
    "Миниган":          {"dmg":9,  "cooldown":0.05,"speed":17,"pellets":1,"spread":0.11,"cost":560,"color":ORANGE,"aoe":0, "gun_len":27,"gun_w":9},
    "Базука":           {"dmg":135,"cooldown":1.35,"speed":7.5,"pellets":1,"spread":0.0, "cost":700,"color":PURPLE,"aoe":95,"gun_len":30,"gun_w":11},
}
WEAPON_ORDER = ["Пистолет","Пистолет-пулемёт","Дробовик","Снайперка","Миниган","Базука"]

# ----- Текстуры оружия (картинки-модельки рядом с game.py) -----
WEAPON_FILES = {
    "Пистолет": "weapon_pistol.png",
    "Пистолет-пулемёт": "weapon_smg.png",
    "Дробовик": "weapon_shotgun.png",
    "Снайперка": "weapon_sniper.png",
    "Миниган": "weapon_minigun.png",
    "Базука": "weapon_bazooka.png",
}
WEAPON_IMG = {}
for _wn, _fn in WEAPON_FILES.items():
    if os.path.exists(_fn):
        try:
            _im = pygame.image.load(_fn).convert_alpha()
            _tw = int(WEAPONS[_wn].get("gun_len", 20) * 2.4)
            _sc = _tw / _im.get_width()
            _th = max(1, int(_im.get_height() * _sc))
            WEAPON_IMG[_wn] = pygame.transform.smoothscale(_im, (_tw, _th))
        except Exception:
            pass

# ----- Турели (Дима Трубаз): баланс + яд -----
TURRETS = {
    "Пушка":   {"dmg":34,"cooldown":1.1, "range":185,"cost":220,"color":GRAY,   "bspeed":12,"aoe":60,"slow":0,  "poison":0, "dtype":"phys"},
    "Пулемёт": {"dmg":5, "cooldown":0.16,"range":150,"cost":120,"color":BLUE,   "bspeed":15,"aoe":0, "slow":0,  "poison":0, "dtype":"phys"},
    "Огнемёт": {"dmg":4, "cooldown":0.06,"range":110,"cost":240,"color":ORANGE, "bspeed":9, "aoe":0, "slow":0,  "poison":0, "dtype":"fire"},
    "Мороз":   {"dmg":3, "cooldown":0.40,"range":150,"cost":170,"color":CYAN,   "bspeed":13,"aoe":0, "slow":1.4,"poison":0, "dtype":"ice"},
    "Яд":      {"dmg":3, "cooldown":0.8, "range":160,"cost":200,"color":POISONC,"bspeed":12,"aoe":0, "slow":0,  "poison":16,"dtype":"poison"},
    "Банк":    {"dmg":0, "cooldown":1.0, "range":0,  "cost":260,"color":(90,200,140),"bspeed":1,"aoe":0,"slow":0,"poison":0,"dtype":"econ","income":18,"interval":3.0},
    "Казарма": {"dmg":0, "cooldown":1.0, "range":0,  "cost":300,"color":(90,150,235),"bspeed":1,"aoe":0,"slow":0,"poison":0,"dtype":"summon","interval":7.0},
}
TURRET_ORDER = ["Пушка","Пулемёт","Огнемёт","Мороз","Яд","Банк","Казарма"]

# Ветвящаяся прокачка: на 3-м уровне башню можно специализировать (выбор из двух веток).
TURRET_SPECS = {
    "Пушка": [
        {"key":"sniper","name":"Снайперская","desc":"Огромный урон по одной цели, медленный выстрел","color":CYAN,
         "mods":{"dmg":3.2,"cooldown":1.9,"range":1.45}},
        {"key":"shrapnel","name":"Осколочная","desc":"Бьёт по площади, накрывает группу врагов","color":ORANGE,
         "mods":{"dmg":0.65,"cooldown":0.9,"aoe_set":95}},
    ],
    "Пулемёт": [
        {"key":"gatling","name":"Гатлинг","desc":"Бешеная скорострельность","color":YELLOW,
         "mods":{"dmg":0.9,"cooldown":0.45}},
        {"key":"piercer","name":"Тяжёлый калибр","desc":"Реже, но очень больно бьёт","color":(190,190,210),
         "mods":{"dmg":2.4,"cooldown":1.7,"range":1.15}},
    ],
    "Огнемёт": [
        {"key":"inferno","name":"Инферно","desc":"Сильнее жжёт вблизи","color":(255,120,40),
         "mods":{"dmg":1.8,"range":1.1}},
        {"key":"plasma","name":"Плазма","desc":"Дальнобойный поток","color":(255,180,90),
         "mods":{"dmg":1.2,"range":1.6,"cooldown":1.2}},
    ],
    "Мороз": [
        {"key":"glacier","name":"Ледник","desc":"Замедляет сильнее и дольше","color":(150,230,255),
         "mods":{"dmg":1.2,"slow_set":2.4}},
        {"key":"shatter","name":"Криоудар","desc":"Больше урона по цели","color":(120,200,255),
         "mods":{"dmg":3.0,"cooldown":1.4}},
    ],
    "Яд": [
        {"key":"plague","name":"Чума","desc":"Усиленный яд (DoT)","color":(120,210,90),
         "mods":{"dmg":1.4,"poison_mul":2.0}},
        {"key":"acid","name":"Кислота","desc":"Прямой урон выше","color":(160,220,80),
         "mods":{"dmg":2.4,"cooldown":1.3}},
    ],
}


# ===== Wave Timeline + UI ветвящейся прокачки (само-подключение, без правок game loop) =====
_WAVE_TRACK = {"wave": None, "total": 1}

def _alive_enemies():
    try: return [e for e in G.get("enemies", []) if getattr(e, "alive", True)]
    except Exception: return []

def _summarize_units(units):
    groups = {}; order = []
    for e in units:
        col = tuple(e.color) if not isinstance(e.color, tuple) else e.color
        key = (col, bool(getattr(e, "is_boss", False)), getattr(e, "kind", "normal"))
        if key not in groups: groups[key] = 0; order.append(key)
        groups[key] += 1
    out = []
    for key in order:
        col, is_boss, kind = key
        out.append((col, 11 if is_boss else 7, is_boss, groups[key]))
    return out

def draw_wave_timeline():
    if G.get("state") != "wave": return
    queue = G.get("spawn_queue", []); alive = _alive_enemies()
    remaining = len(queue) + len(alive)
    if _WAVE_TRACK["wave"] != G.get("wave"):
        _WAVE_TRACK["wave"] = G.get("wave"); _WAVE_TRACK["total"] = max(1, remaining)
    else:
        _WAVE_TRACK["total"] = max(_WAVE_TRACK["total"], remaining)
    total = max(1, _WAVE_TRACK["total"])
    done = max(0, total - remaining); frac = max(0.0, min(1.0, done/total))
    bw = 520; x = WIDTH//2 - bw//2; y = 60; h = 16
    pygame.draw.rect(screen, (18,20,30), (x-3, y-3, bw+6, h+6), border_radius=10)
    pygame.draw.rect(screen, (46,50,66), (x, y, bw, h), border_radius=8)
    fillw = int(bw*frac)
    if fillw > 4:
        draw_round_gradient(pygame.Rect(x, y, fillw, h), (130,215,150), (60,150,90), 8)
    pygame.draw.rect(screen, (150,160,185), (x, y, bw, h), 2, border_radius=8)
    lbl = font_s.render("Волна " + str(G.get("wave", 1)) + "  •  врагов осталось: " + str(remaining), True, WHITE)
    screen.blit(lbl, (x, y-20))
    types = _summarize_units(list(queue) + alive)
    ix = x + bw + 16; iy = y + h//2
    for col, rad, is_boss, cnt in types[:6]:
        pygame.draw.circle(screen, col, (ix, iy), rad)
        pygame.draw.circle(screen, BLACK, (ix, iy), rad, 2)
        c = font_s.render("x"+str(cnt), True, WHITE); screen.blit(c, (ix+rad+3, iy-8))
        ix += rad*2 + 30

def _selected_turret():
    try:
        t = G.get("sel_turret_obj")
        if t is not None and t in G.get("turrets", []): return t
    except Exception: pass
    return None

def _spec_options(t):
    if t and getattr(t, "level", 1) >= 3 and getattr(t, "spec", None) is None:
        return TURRET_SPECS.get(t.kind, [])
    return []

def _spec_panel_rects():
    t = _selected_turret(); opts = _spec_options(t)
    if not opts: return {}
    pw = 460; ph = 158; x = WIDTH//2 - pw//2; y = HEIGHT//2 - ph//2
    bw = (pw - 48)//2; rects = {}
    for i, sp in enumerate(opts[:2]):
        rects[sp["key"]] = pygame.Rect(x + 16 + i*(bw+16), y + 56, bw, ph - 72)
    return rects

def draw_spec_modal():
    t = _selected_turret(); opts = _spec_options(t)
    if not opts: return
    pw = 460; ph = 158; x = WIDTH//2 - pw//2; y = HEIGHT//2 - ph//2
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); dim.fill((0,0,0,120)); screen.blit(dim, (0,0))
    draw_round_gradient(pygame.Rect(x, y, pw, ph), (54,58,82), (34,36,54), 16)
    pygame.draw.rect(screen, (245,205,70), (x, y, pw, ph), 2, border_radius=16)
    title = font_m.render("Специализация: " + t.kind + " (ур. 3)", True, WHITE)
    screen.blit(title, (x + pw//2 - title.get_width()//2, y + 14))
    rects = _spec_panel_rects(); mp = pygame.mouse.get_pos()
    for sp in opts[:2]:
        r = rects[sp["key"]]; hover = r.collidepoint(mp); col = sp.get("color", (90,140,220))
        top = tuple(min(255, int(c*(1.35 if hover else 1.15))) for c in col)
        draw_round_gradient(r, top, tuple(int(c*0.6) for c in col), 12)
        pygame.draw.rect(screen, WHITE if hover else (20,20,28), r, 2, border_radius=12)
        n = font_m.render(sp["name"], True, (15,15,20)); screen.blit(n, (r.centerx - n.get_width()//2, r.y + 8))
        words = sp["desc"].split(); line = ""; yy = r.y + 40
        for w in words:
            test = (line + " " + w).strip()
            if font_s.size(test)[0] > r.width - 16:
                screen.blit(font_s.render(line, True, (20,20,28)), (r.x + 10, yy)); yy += 18; line = w
            else: line = test
        if line: screen.blit(font_s.render(line, True, (20,20,28)), (r.x + 10, yy))

def _apply_spec_choice(spec_key):
    t = _selected_turret()
    if t and getattr(t, "level", 1) >= 3 and getattr(t, "spec", None) is None:
        if t.specialize(spec_key):
            try: G["floats"].append(FloatText(t.x, t.y-30, t.spec_name, YELLOW))
            except Exception: pass
            play_sound("buy")

class Ally:
    """Союзник Казармы: идёт от базы по дороге навстречу врагам.
    Ур.1 — только ближний бой; ур.2+ — ещё и стреляет. Облик зависит от уровня."""
    def __init__(self, hp=60, dmg=14, speed=70, level=1):
        self.path = PATH
        self.idx = len(self.path)-1
        self.x, self.y = self.path[self.idx]
        self.level = max(1, level)
        self.hp = hp; self.max_hp = hp; self.dmg = dmg; self.speed = speed
        self.alive = True; self.atk_cd = 0.0; self.shoot_cd = 0.0; self.flash = 0.0
        self.ranged = self.level >= 2
        self.shoot_range = 150
    def update(self, dt):
        if self.flash>0: self.flash-=dt
        if self.ranged:
            self.shoot_cd-=dt
            tgt=None; best=self.shoot_range
            for e in G.get("enemies", []):
                if getattr(e,"alive",False):
                    d=dist(self.x,self.y,e.x,e.y)
                    if d<best: best=d; tgt=e
            if tgt is not None and self.shoot_cd<=0:
                self.shoot_cd=0.7
                ang=math.atan2(tgt.y-self.y, tgt.x-self.x); bs=11
                G["bullets"].append(Bullet(self.x,self.y,math.cos(ang)*bs,math.sin(ang)*bs,
                                    self.dmg,(120,200,255),4,target=tgt))
                play_sound("shoot", throttle_ms=90)
        target=None; best=1e9
        for e in G.get("enemies", []):
            if getattr(e,"alive",False):
                d=dist(self.x,self.y,e.x,e.y)
                if d<e.radius+13 and d<best: best=d; target=e
        if target is not None:
            self.atk_cd-=dt
            if self.atk_cd<=0:
                self.atk_cd=0.5
                target.hit(self.dmg)
                try: G["floats"].append(FloatText(target.x,target.y-target.radius,self.dmg,(120,200,255)))
                except Exception: pass
            self.hp-=22*dt
            self.flash=0.1
            if self.hp<=0: self.alive=False
            return
        if self.idx>0:
            tx,ty=self.path[self.idx-1]
            d=dist(self.x,self.y,tx,ty); spd=self.speed*dt
            if d<=spd:
                self.x,self.y=tx,ty; self.idx-=1
            else:
                self.x+=(tx-self.x)/d*spd; self.y+=(ty-self.y)/d*spd
        else:
            self.alive=False
    def draw(self, s):
        x,y=int(self.x),int(self.y); lvl=max(1,min(3,self.level))
        sh=pygame.Surface((24,10),pygame.SRCALPHA); pygame.draw.ellipse(sh,(0,0,0,90),sh.get_rect())
        s.blit(sh,(x-12,y+8))
        cols={1:(80,160,255),2:(120,210,150),3:(245,205,70)}; r=10+lvl
        pygame.draw.circle(s,cols[lvl],(x,y),r)
        pygame.draw.circle(s,(20,40,90),(x,y),r,2)
        if self.flash>0: pygame.draw.circle(s,(255,255,255),(x,y),r,2)
        if self.ranged:
            pygame.draw.line(s,(40,50,70),(x,y),(x+r+5,y),3)
        else:
            pygame.draw.line(s,(225,232,248),(x+5,y-5),(x+r+4,y-r-2),3)
        for i in range(lvl):
            pygame.draw.circle(s,(255,255,255),(x-6+i*6,y+r+4),2)
        w=24; f=max(0.0,self.hp/self.max_hp)
        pygame.draw.rect(s,(30,30,38),(x-w//2,y-r-9,w,4),border_radius=2)
        pygame.draw.rect(s,(90,220,120),(x-w//2,y-r-9,int(w*f),4),border_radius=2)

_LAST_TICK = [0]
def _frame_dt():
    now = pygame.time.get_ticks()
    if _LAST_TICK[0]==0: _LAST_TICK[0]=now; return 0.0
    dt=(now-_LAST_TICK[0])/1000.0; _LAST_TICK[0]=now
    return max(0.0, min(0.1, dt))

def _ensure_allies():
    if not isinstance(G.get("allies"), list): G["allies"]=[]
    return G["allies"]

def _update_allies():
    dt=_frame_dt()
    if not isinstance(G, dict): return
    if not G.get("endless") and G.get("max_waves",0) < 30:
        G["max_waves"]=30
    if G.get("state")!="wave":        # вне волны союзники не ходят и не остаются
        if G.get("allies"): G["allies"]=[]
        return
    allies=_ensure_allies()
    for a in allies[:]:
        a.update(dt)
        if not a.alive: allies.remove(a)

def _draw_allies():
    try:
        for a in _ensure_allies(): a.draw(screen)
    except Exception:
        pass

def _draw_tl_safe():
    try:
        if isinstance(G, dict) and G.get("state") in ("wave", "build", "mutator_warn"):
            _draw_allies()
            draw_wave_timeline(); draw_spec_modal()
    except Exception:
        pass
    try:
        _update_check_tick(); _draw_update_ui()
    except Exception:
        pass

_real_flip2 = pygame.display.flip
_real_update2 = pygame.display.update
def _flip_tl(*a, **k):
    _update_allies(); _draw_tl_safe(); return _real_flip2(*a, **k)
def _update_tl(*a, **k):
    _update_allies(); _draw_tl_safe(); return _real_update2(*a, **k)
pygame.display.flip = _flip_tl
pygame.display.update = _update_tl

_real_event_get = pygame.event.get
def _event_get_tl(*a, **k):
    evs = _real_event_get(*a, **k)
    if a or k: return evs
    try:
        rects = _spec_panel_rects()
        if not rects: return evs
        out = []
        for e in evs:
            if e.type == pygame.MOUSEBUTTONDOWN and getattr(e, "button", 1) == 1:
                hit = None
                for key, r in rects.items():
                    if r.collidepoint(e.pos): hit = key; break
                if hit is not None:
                    _apply_spec_choice(hit); continue
            out.append(e)
        return out
    except Exception:
        return evs
pygame.event.get = _event_get_tl
# ===== /Wave Timeline + spec UI =====
TRAPS = {
    "Шипы": {"cost":90,  "dmg":36, "uses":6, "radius":20, "color":(190,190,200)},
    "Мина": {"cost":140, "dmg":170,"radius":76,"color":(230,90,70)},
}
TRAP_ORDER = ["Шипы","Мина"]
DRONE_COST = 300
PRIORITIES = ["Первый","Последний","Сильнейший","Слабейший"]

def draw_range_ring(s, x, y, r, color, selected=False):
    """Стильная зона поражения: мягкий градиент + медленно пульсирующее кольцо."""
    pulse = 0.5 + 0.5*math.sin(pygame.time.get_ticks()*0.0035)
    d = r*2+10; cx = d//2
    surf = pygame.Surface((d, d), pygame.SRCALPHA)
    steps = 14
    for i in range(steps, 0, -1):
        rr = int(r*i/steps)
        a = int((22 if not selected else 34) * (1 - i/steps))
        pygame.draw.circle(surf, (color[0],color[1],color[2],a), (cx,cx), rr)
    edge_a = int(70 + 80*pulse)
    pygame.draw.circle(surf, (color[0],color[1],color[2],edge_a), (cx,cx), r, 3)
    inner = int(r*(0.82+0.12*pulse))
    pygame.draw.circle(surf, (color[0],color[1],color[2],45), (cx,cx), inner, 2)
    s.blit(surf, (x-cx, y-cx))


def draw_additive_glow(surf, x, y, r, color, intensity=120):
    """Лёгкий bloom: аддитивное свечение (аналог shadowBlur на канвасе)."""
    r=max(2,int(r)); d=r*2
    g=pygame.Surface((d,d),pygame.SRCALPHA)
    steps=4
    for i in range(steps,0,-1):
        rr=int(r*i/steps); a=int(intensity*(1-i/steps)/steps*2)
        pygame.draw.circle(g,(color[0],color[1],color[2],a),(r,r),rr)
    surf.blit(g,(int(x-r),int(y-r)),special_flags=pygame.BLEND_RGB_ADD)


class Effect:
    def __init__(self, x, y, max_r, color):
        self.x, self.y, self.max_r = x, y, max_r
        self.color = color; self.life = 0.35; self.t = 0.35; self.r = 4
    def update(self, dt):
        self.t -= dt
        self.r = self.max_r * (1 - max(0, self.t)/self.life)
        return self.t > 0
    def draw(self, s):
        a = int(180 * max(0, self.t)/self.life)
        surf = pygame.Surface((self.max_r*2, self.max_r*2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (self.color[0],self.color[1],self.color[2],a), (self.max_r,self.max_r), int(self.r))
        pygame.draw.circle(surf, (255,255,255,a), (self.max_r,self.max_r), int(self.r), 2)
        s.blit(surf, (self.x-self.max_r, self.y-self.max_r))
        draw_additive_glow(s, self.x, self.y, self.r*1.2, self.color, intensity=150)  # bloom взрыва


class Particle:
    """Лёгкая частица для вспышек выстрелов и искр от попаданий."""
    def __init__(self, x, y, vx, vy, life, color, radius, grav=0.0, fade=True):
        self.x=x; self.y=y; self.vx=vx; self.vy=vy
        self.life=life; self.max_life=life; self.color=color
        self.radius=radius; self.grav=grav; self.fade=fade
    def update(self, dt):
        self.x+=self.vx; self.y+=self.vy
        self.vy+=self.grav; self.vx*=0.92; self.vy*=0.92
        self.life-=dt
        return self.life>0
    def draw(self, s):
        k=max(0.0, self.life/self.max_life)
        r=max(1, int(self.radius*(k if self.fade else 1)))
        a=int(230*k); d=r*2
        surf=pygame.Surface((d+2,d+2),pygame.SRCALPHA)
        pygame.draw.circle(surf,(self.color[0],self.color[1],self.color[2],a),(r+1,r+1),r)
        s.blit(surf,(self.x-r,self.y-r))

def spawn_muzzle(parts, x, y, angle, color=(255,210,120)):
    """Вспышка от выстрела (muzzle flash) — конус искр по направлению ствола."""
    for _ in range(7):
        a=angle+random.uniform(-0.35,0.35); sp=random.uniform(2.5,6.0)
        parts.append(Particle(x, y, math.cos(a)*sp, math.sin(a)*sp,
                              random.uniform(0.12,0.26), color, random.randint(3,6)))
    parts.append(Particle(x, y, math.cos(angle)*1.5, math.sin(angle)*1.5, 0.08, (255,255,220), 8))

def spawn_hit(parts, x, y, color=(255,230,150)):
    """Искры при попадании пули."""
    for _ in range(8):
        a=random.uniform(0, math.tau); sp=random.uniform(1.5,4.5)
        parts.append(Particle(x, y, math.cos(a)*sp, math.sin(a)*sp,
                              random.uniform(0.18,0.4), color, random.randint(2,4), grav=0.05))


def spawn_shell(x, y, angle):
    """Выброс гильзы из ствола (огнестрел игрока и башен)."""
    if len(G["shells"])>120: G["shells"].pop(0)
    G["shells"].append(Shell(x, y, angle))


def spawn_splat(x, y, color=(120,22,22)):
    """Пятно крови/масла на земле при попадании."""
    if len(G["splats"])>140: G["splats"].pop(0)
    G["splats"].append(Splat(x, y, color))


class FloatText:
    """Вылетающая цифра урона (floating damage number) — отлетает вверх и гаснет."""
    def __init__(self, x, y, value, color=WHITE, crit=False):
        self.x=x+random.uniform(-6,6); self.y=y
        self.vy=-1.2; self.life=0.8; self.max_life=0.8
        self.text=(value if isinstance(value,str) else str(int(value))); self.color=color
        self.crit=crit
    def update(self, dt):
        self.y+=self.vy; self.vy+=0.025; self.life-=dt
        return self.life>0
    def draw(self, s):
        k=max(0.0, self.life/self.max_life); a=int(255*k)
        f=font_m if self.crit else font_s
        surf=f.render(self.text, True, self.color); surf.set_alpha(a)
        sh=f.render(self.text, True, (0,0,0)); sh.set_alpha(a)
        s.blit(sh,(self.x-surf.get_width()/2+1, self.y+1))
        s.blit(surf,(self.x-surf.get_width()/2, self.y))


class Shell:
    """Гильза: вылетает из ствола вбок, падает, чуть отскакивает и лежит (~10с)."""
    def __init__(self, x, y, angle):
        side=angle+math.pi/2*random.choice((-1,1))
        sp=random.uniform(1.4,2.8)
        self.x=x; self.y=y
        self.vx=math.cos(side)*sp; self.vy=math.sin(side)*sp
        self.z=5.0; self.vz=random.uniform(2.2,3.6)
        self.rot=random.uniform(0,math.tau); self.vrot=random.uniform(-0.5,0.5)
        self.life=10.0; self.settled=False
    def update(self, dt):
        self.life-=dt
        if not self.settled:
            self.x+=self.vx; self.y+=self.vy
            self.vx*=0.85; self.vy*=0.85
            self.z+=self.vz; self.vz-=0.45
            self.rot+=self.vrot
            if self.z<=0:
                self.z=0
                if self.vz<-1.2: self.vz=-self.vz*0.42; self.vrot*=0.5
                else: self.settled=True; self.vz=0; self.vrot=0
        return self.life>0
    def draw(self, s):
        a=255 if self.life>2 else max(0,int(255*self.life/2))
        sh=pygame.Surface((8,5),pygame.SRCALPHA); pygame.draw.ellipse(sh,(0,0,0,70),sh.get_rect())
        s.blit(sh,(self.x-4,self.y-2))
        shell=pygame.Surface((7,4),pygame.SRCALPHA)
        pygame.draw.rect(shell,(225,195,70,a),(0,0,7,4),border_radius=1)
        pygame.draw.rect(shell,(255,235,150,a),(0,0,2,4))
        shell=pygame.transform.rotate(shell,math.degrees(self.rot))
        s.blit(shell, shell.get_rect(center=(int(self.x),int(self.y-self.z))))


class Splat:
    """Пятно крови/масла на земле от попадания — лежит и медленно тает."""
    def __init__(self, x, y, color=(120,22,22)):
        self.x=x; self.y=y; self.color=color
        self.life=14.0; self.max_life=14.0
        self.blobs=[(random.uniform(-8,8),random.uniform(-5,5),random.randint(2,5)) for _ in range(random.randint(3,5))]
    def update(self, dt):
        self.life-=dt
        return self.life>0
    def draw(self, s):
        k=max(0.0,self.life/self.max_life); a=int(140*k)
        surf=pygame.Surface((34,26),pygame.SRCALPHA)
        for ox,oy,r in self.blobs:
            pygame.draw.circle(surf,(self.color[0],self.color[1],self.color[2],a),(17+int(ox),13+int(oy)),r)
        s.blit(surf,(self.x-17,self.y-13))


class Barrel:
    """Взрывоопасная бочка: при попадании пули взрывается и бьёт всех врагов рядом."""
    def __init__(self, x, y):
        self.x=x; self.y=y; self.radius=15; self.alive=True
        self.blast=120; self.dmg=240; self.wob=random.uniform(0,math.tau)
    def explode(self, chain=False):
        if not self.alive: return
        # огнемёт БОЛЬШЕ не детонирует бочки: если рядом только fire-пули — игнор
        if not chain:
            near=[b for b in G.get("bullets",[]) if dist(self.x,self.y,b.x,b.y)<self.radius+12]
            if near and all(getattr(b,"dtype",None)=="fire" for b in near):
                return
        self.alive=False
        G["effects"].append(Effect(self.x,self.y,self.blast,(255,140,40)))
        add_shake(13); play_sound("boom")
        for _ in range(26):
            a=random.uniform(0,math.tau); sp=random.uniform(2,7)
            G["particles"].append(Particle(self.x,self.y,math.cos(a)*sp,math.sin(a)*sp,
                                  random.uniform(0.3,0.7),(255,150,50),random.randint(4,8),grav=0.04))
        for e in G["enemies"]:
            if e.alive and dist(self.x,self.y,e.x,e.y)<self.blast:
                e.hit(self.dmg)
                G["floats"].append(FloatText(e.x,e.y-e.radius,self.dmg,ORANGE,crit=True))
        for bar in G["barrels"]:        # цепная реакция
            if bar.alive and bar is not self and dist(self.x,self.y,bar.x,bar.y)<self.blast:
                bar.explode(chain=True)
    def draw(self, s):
        if not self.alive: return
        wob=math.sin(pygame.time.get_ticks()*0.004+self.wob)*1.5
        sh=pygame.Surface((self.radius*2+6,self.radius),pygame.SRCALPHA)
        pygame.draw.ellipse(sh,(0,0,0,90),sh.get_rect())
        s.blit(sh,(self.x-self.radius-3,self.y+self.radius-6))
        r=pygame.Rect(0,0,self.radius*2-4,self.radius*2+4); r.center=(int(self.x),int(self.y+wob))
        pygame.draw.rect(s,(170,40,35),r,border_radius=5)
        pygame.draw.rect(s,(220,70,55),r.inflate(-8,-self.radius),border_radius=4)
        pygame.draw.rect(s,(60,16,16),r,2,border_radius=5)
        warn=font_s.render("!",True,YELLOW)
        s.blit(warn,(r.centerx-warn.get_width()//2,r.centery-warn.get_height()//2))


class Trap:
    """Одноразовая ловушка на дороге: Шипы (несколько срабатываний) или Мина (взрыв)."""
    def __init__(self, x, y, kind):
        self.x=x; self.y=y; self.kind=kind; self.cfg=TRAPS[kind]
        self.alive=True; self.uses=self.cfg.get("uses",1); self.cd=0.0
        self.radius=self.cfg.get("radius",20)
    def update(self, dt):
        self.cd-=dt
        if self.kind=="Мина":
            for e in G["enemies"]:
                if e.alive and dist(self.x,self.y,e.x,e.y)<e.radius+12:
                    self.explode(); return
        else:
            if self.cd<=0:
                for e in G["enemies"]:
                    if e.alive and dist(self.x,self.y,e.x,e.y)<self.radius+e.radius:
                        e.hit(self.cfg["dmg"]); play_hit()
                        G["floats"].append(FloatText(e.x,e.y-e.radius,self.cfg["dmg"],self.cfg["color"]))
                        self.uses-=1; self.cd=0.35
                        if self.uses<=0: self.alive=False
                        break
    def explode(self):
        self.alive=False; r=self.cfg["radius"]
        G["effects"].append(Effect(self.x,self.y,r,(255,140,40))); add_shake(9); play_sound("boom")
        for _ in range(14):
            a=random.uniform(0,math.tau); sp=random.uniform(2,6)
            G["particles"].append(Particle(self.x,self.y,math.cos(a)*sp,math.sin(a)*sp,
                                  random.uniform(0.3,0.6),(255,150,50),random.randint(3,6),grav=0.04))
        for e in G["enemies"]:
            if e.alive and dist(self.x,self.y,e.x,e.y)<r:
                e.hit(self.cfg["dmg"])
                G["floats"].append(FloatText(e.x,e.y-e.radius,self.cfg["dmg"],ORANGE,crit=True))
    def draw(self, s):
        if not self.alive: return
        if self.kind=="Мина":
            pygame.draw.circle(s,(90,90,100),(int(self.x),int(self.y)),11)
            pygame.draw.circle(s,(230,90,70),(int(self.x),int(self.y)),5)
            pygame.draw.circle(s,(20,20,26),(int(self.x),int(self.y)),11,2)
        else:
            for ox in (-12,-4,4,12):
                pygame.draw.polygon(s,(200,200,210),
                    [(self.x+ox-3,self.y+4),(self.x+ox,self.y-8),(self.x+ox+3,self.y+4)])
                pygame.draw.polygon(s,(60,60,70),
                    [(self.x+ox-3,self.y+4),(self.x+ox,self.y-8),(self.x+ox+3,self.y+4)],1)
            u=font_s.render(str(self.uses),True,WHITE)
            s.blit(u,(self.x-u.get_width()//2,self.y+6))


class Drone:
    """Дрон-помощник: летает по орбите вокруг Матвея и бьёт ближайших врагов лазером."""
    def __init__(self):
        self.angle=random.uniform(0,math.tau); self.orbit=48
        self.x=0.0; self.y=0.0; self.timer=0.0
        self.cooldown=0.45; self.range=250; self.dmg=6
    def update(self, dt, hero, enemies):
        self.angle+=dt*2.4
        self.x=hero.x+math.cos(self.angle)*self.orbit
        self.y=hero.y+math.sin(self.angle)*self.orbit-4
        self.timer-=dt
        if self.timer<=0:
            target=None; best=self.range
            for e in enemies:
                if e.alive:
                    d=dist(self.x,self.y,e.x,e.y)
                    if d<best: best=d; target=e
            if target:
                self.timer=self.cooldown
                target.hit(self.dmg)
                G["floats"].append(FloatText(target.x,target.y-target.radius,self.dmg,CYAN))
                G["lasers"].append([self.x,self.y,target.x,target.y,0.12])
                spawn_hit(G["particles"], target.x, target.y, CYAN)
                play_sound("shoot", throttle_ms=70)
    def draw(self, s):
        sh=pygame.Surface((20,8),pygame.SRCALPHA); pygame.draw.ellipse(sh,(0,0,0,80),sh.get_rect())
        s.blit(sh,(self.x-10,self.y+8))
        draw_additive_glow(s, self.x, self.y, 14, CYAN, intensity=120)
        pygame.draw.circle(s,(60,70,90),(int(self.x),int(self.y)),8)
        pygame.draw.circle(s,(120,210,255),(int(self.x),int(self.y)),5)
        pygame.draw.circle(s,WHITE,(int(self.x-2),int(self.y-2)),2)
        pygame.draw.circle(s,(20,24,32),(int(self.x),int(self.y)),8,2)


class Pickup:
    """Подбираемый предмет на карте: монета (деньги) или аптечка (HP).
    Игрок подбирает, подбегая близко; на малом расстоянии срабатывает магнетизм."""
    def __init__(self, x, y, kind="coin", value=0):
        self.x=x; self.y=y; self.kind=kind; self.value=value
        ang=random.uniform(0,math.tau); sp=random.uniform(1.5,3.6)
        self.vx=math.cos(ang)*sp; self.vy=math.sin(ang)*sp   # разлёт при выпадении
        self.life=14.0; self.bob=random.uniform(0,math.tau)
        self.alive=True; self.magnet=False
    def update(self, dt, hero):
        self.bob+=dt*6
        self.vx*=0.86; self.vy*=0.86
        self.x+=self.vx; self.y+=self.vy
        d=dist(self.x,self.y,hero.x,hero.y)
        if d<130:                                            # магнетизм лута к Матвею
            self.magnet=True
            pull=9.0
            self.x+=(hero.x-self.x)/max(1,d)*pull
            self.y+=(hero.y-self.y)/max(1,d)*pull
        if d<hero.radius+12:
            self.collect(hero); self.alive=False; return
        self.life-=dt
        if self.life<=0: self.alive=False
    def collect(self, hero):
        if self.kind=="coin":
            G["money"]+=self.value
            G["floats"].append(FloatText(self.x, self.y-10, self.value, YELLOW))
        else:
            hero.hp=min(hero.max_hp, hero.hp+self.value)
            G["floats"].append(FloatText(self.x, self.y-10, "+"+str(int(self.value)), (90,220,110)))
        play_sound("buy", throttle_ms=30)
    def draw(self, s):
        yy=self.y+math.sin(self.bob)*2.5
        if self.magnet:
            gl=pygame.Surface((26,26),pygame.SRCALPHA)
            pygame.draw.circle(gl,(255,235,150,70),(13,13),13)
            s.blit(gl,(self.x-13,yy-13))
        if self.kind=="coin":
            pygame.draw.circle(s,(180,150,30),(int(self.x),int(yy)),8)
            pygame.draw.circle(s,(245,205,70),(int(self.x),int(yy)),7)
            pygame.draw.circle(s,(255,235,150),(int(self.x-2),int(yy-2)),2)
        else:
            r=pygame.Rect(0,0,16,16); r.center=(int(self.x),int(yy))
            pygame.draw.rect(s,(60,200,90),r,border_radius=4)
            pygame.draw.rect(s,(255,255,255),r,2,border_radius=4)
            pygame.draw.line(s,WHITE,(r.centerx-4,r.centery),(r.centerx+4,r.centery),2)
            pygame.draw.line(s,WHITE,(r.centerx,r.centery-4),(r.centerx,r.centery+4),2)


def spawn_loot(e):
    """Выпадение лута из убитого врага: монеты (деньги) и иногда аптечка."""
    gold=G.get("mut_gold",1)   # мутатор «Золотая лихорадка» удваивает деньги
    if getattr(e,"is_boss",False):
        coins=max(1, (e.reward*gold)//8)
        for _ in range(8):
            G["pickups"].append(Pickup(e.x+random.uniform(-30,30), e.y+random.uniform(-30,30), "coin", coins))
        G["pickups"].append(Pickup(e.x, e.y, "health", 40))
    else:
        G["pickups"].append(Pickup(e.x, e.y, "coin", e.reward*gold))
        if random.random()<0.10:
            G["pickups"].append(Pickup(e.x+random.uniform(-12,12), e.y+random.uniform(-12,12), "health", 12))


class Character:
    """Универсальный персонаж со спрайтом и тенью под ногами.
    Подставь PNG в image — и примитив-квадрат заменится картинкой."""
    def __init__(self, x, y, image=None, color=GRAY, name="", size=44):
        self.x=x; self.y=y; self.image=image
        self.color=color; self.name=name; self.size=size
    def set_pos(self, x, y):
        self.x, self.y = x, y
    def draw(self, s, can_interact=False):
        half=self.size//2
        sh=pygame.Surface((self.size+10, half), pygame.SRCALPHA)
        pygame.draw.ellipse(sh,(0,0,0,110),sh.get_rect())
        s.blit(sh,(self.x-(self.size+10)//2, self.y+half-8))
        if self.image is not None:
            img=self.image if self.image.get_width()==self.size else pygame.transform.scale(self.image,(self.size,self.size))
            s.blit(img, img.get_rect(center=(int(self.x),int(self.y))))
        else:
            box=pygame.Rect(self.x-half, self.y-half, self.size, self.size)
            light=tuple(min(255,int(c*1.25)) for c in self.color)
            prev=s.get_clip(); s.set_clip(box)
            draw_vgradient(box, light, self.color)
            s.set_clip(prev)
            pygame.draw.rect(s,(20,20,28),box,2,border_radius=8)
            pygame.draw.rect(s,(255,255,255),(self.x-half+5,self.y-half+5,9,9),border_radius=3)
        if self.name:
            t=font_s.render(self.name,True,WHITE)
            s.blit(t,(self.x-t.get_width()/2, self.y-half-22))
        if can_interact:
            p=font_m.render("Нажми E",True,YELLOW)
            s.blit(p,(self.x-p.get_width()/2, self.y+half+6))


class Bullet:
    def __init__(self,x,y,vx,vy,dmg,color=YELLOW,radius=5,aoe=0,slow=0,poison=0,life=2.2,target=None,dtype="phys"):
        self.x,self.y,self.vx,self.vy = x,y,vx,vy
        self.dmg=dmg; self.color=color; self.radius=radius
        self.aoe=aoe; self.slow=slow; self.poison=poison; self.life=life; self.alive=True
        self.dtype=dtype   # "phys"/"fire"/"ice"/"poison" — для синергии статусов
        self.target=target; self.speed=math.hypot(vx,vy)
        self.smoke=aoe>0  # ракеты (базука/пушка) оставляют дымный шлейф
        self.trail_timer=0.0
    def update(self,dt):
        # самонаведение: пуля турели всегда летит в цель
        if self.target is not None and getattr(self.target,"alive",False) and self.speed>0:
            dx=self.target.x-self.x; dy=self.target.y-self.y; d=math.hypot(dx,dy)
            if d>0:
                self.vx=dx/d*self.speed; self.vy=dy/d*self.speed
        self.x+=self.vx; self.y+=self.vy; self.life-=dt
        # дымный шлейф ракеты (particle trail)
        if self.smoke:
            self.trail_timer-=dt
            if self.trail_timer<=0:
                self.trail_timer=0.02
                G["particles"].append(Particle(self.x,self.y,random.uniform(-0.4,0.4),random.uniform(-0.5,0.0),
                                      random.uniform(0.3,0.6),(120,118,128),random.randint(4,7),grav=-0.015))
        if self.life<=0 or self.x<-60 or self.x>WIDTH+60 or self.y<-60 or self.y>HEIGHT+60:
            self.alive=False
    def draw(self,s):
        r=self.radius; c=self.color
        # светящийся ГРАДИЕНТНЫЙ трассер с затухающим хвостом
        gd=r*6
        tail=pygame.Surface((gd*2,gd*2),pygame.SRCALPHA); cc=gd
        steps=7
        for i in range(steps,0,-1):
            k=i/steps; tx=cc-self.vx*0.8*i; ty=cc-self.vy*0.8*i
            a=int(110*(1-k)+25)
            pygame.draw.circle(tail,(c[0],c[1],c[2],a),(int(tx),int(ty)),max(1,int(r*(1-0.6*k))))
        pygame.draw.circle(tail,(c[0],c[1],c[2],60),(cc,cc),int(r*2))  # мягкий ореол
        s.blit(tail,(self.x-gd,self.y-gd))
        pygame.draw.circle(s,c,(int(self.x),int(self.y)),r)
        pygame.draw.circle(s,WHITE,(int(self.x-r*0.3),int(self.y-r*0.3)),max(1,r//2))


class Enemy:
    def __init__(self,hp,speed,color,radius,reward,name=None,is_boss=False,kind="normal",path=None):
        self.path = path if path is not None else PATH
        self.x,self.y = self.path[0]; self.idx=0
        self.kind=kind                 # "normal" / "flying" / "shooter"
        self.shoot_cd=random.uniform(0.8,1.8); self._counted=False
        self.max_hp=hp; self.hp=hp; self.speed=speed
        self.color=color; self.radius=radius; self.reward=reward
        self.name=name; self.is_boss=is_boss; self.alive=True; self.reached=False
        self.slow_timer=0.0; self.poison_dps=0.0; self.poison_timer=0.0; self.flash=0.0
        self.walk=random.uniform(0,6.28)  # фаза анимации ходьбы (wiggle/squash)
        # ---- абилки боссов ----
        self.boss_kind=None                 # "shark" / "stun" / "summon"
        self.water_r=98                      # радиус водяного круга (мегалодон)
        self.meg_ang=random.uniform(0,6.28); self.meg_x=self.x; self.meg_y=self.y
        self.ability_timer=5.0; self.speed_boost=0.0; self.bat_swing=0.0
    def add_poison(self,dps):
        if dps>0:
            self.poison_dps=max(self.poison_dps,dps); self.poison_timer=3.0
    def active_statuses(self):
        """Массив активных эффектов/дебаффов на враге."""
        st=[]
        if self.slow_timer>0: st.append("frozen")
        if self.poison_timer>0: st.append("poison")
        if self.speed_boost>0: st.append("haste")
        return st
    def update(self,dt):
        if self.flash>0: self.flash-=dt
        if self.is_boss and self.boss_kind=="shark":   # мегалодон плавает по кругу
            self.meg_ang+=dt*1.8
            self.meg_x=self.x+math.cos(self.meg_ang)*self.water_r
            self.meg_y=self.y+math.sin(self.meg_ang)*self.water_r
        if self.poison_timer>0:
            self.hp-=self.poison_dps*dt; self.poison_timer-=dt
            if self.hp<=0:
                self.alive=False
                if not self._counted: self._counted=True; G["kills"]=G.get("kills",0)+1
                return
        spd=self.speed
        if self.speed_boost>0:
            spd*=1.8; self.speed_boost-=dt
        if self.slow_timer>0:
            spd*=0.45; self.slow_timer-=dt
        self.walk+=spd*dt*4.0  # двигается — качается
        if self.kind=="flying":
            # Призрак: летит по прямой к базе сквозь препятствия
            tx,ty = self.path[-1]
            d = dist(self.x,self.y,tx,ty)
            if d<=spd or d<6:
                self.reached=True; self.alive=False
            else:
                self.x += (tx-self.x)/d*spd; self.y += (ty-self.y)/d*spd
            return
        if self.kind=="shooter":
            # Стрелок: тормозит рядом с Матвеем и стреляет в него
            h=G.get("hero"); near = bool(h) and dist(self.x,self.y,h.x,h.y) < 340
            self.shoot_cd-=dt
            if near and self.shoot_cd<=0:
                self.shoot_cd=1.6
                a=math.atan2(h.y-self.y, h.x-self.x); bs=4.2
                G.setdefault("enemy_bullets",[]).append(
                    EnemyBullet(self.x, self.y, math.cos(a)*bs, math.sin(a)*bs, dmg=12))
            if near: spd*=0.25   # притормаживает, чтобы стрелять
        if self.idx < len(self.path)-1:
            tx,ty = self.path[self.idx+1]
            d = dist(self.x,self.y,tx,ty)
            if d<=spd:
                self.x,self.y = tx,ty; self.idx+=1
            else:
                self.x += (tx-self.x)/d*spd; self.y += (ty-self.y)/d*spd
        else:
            self.reached=True; self.alive=False
    def hit(self,dmg,slow=0,poison=0):
        self.hp-=dmg; self.flash=0.12
        if slow>0: self.slow_timer=slow
        if poison>0: self.add_poison(poison)
        if self.hp<=0:
            self.alive=False
            if not self._counted: self._counted=True; G["kills"]=G.get("kills",0)+1
    def draw(self,s):
        # водяной круг Рената (рисуется ПОД боссом)
        if self.is_boss and self.boss_kind=="shark":
            wr=self.water_r
            water=pygame.Surface((wr*2+8,wr*2+8),pygame.SRCALPHA)
            pygame.draw.circle(water,(40,120,210,70),(wr+4,wr+4),wr)
            pygame.draw.circle(water,(90,170,240,90),(wr+4,wr+4),int(wr*0.7))
            pygame.draw.circle(water,(150,210,255,150),(wr+4,wr+4),wr,3)
            s.blit(water,(self.x-wr-4,self.y-wr-4))
        # анимация ходьбы: лёгкое покачивание + squash & stretch
        wob=math.sin(self.walk)
        bob=abs(math.sin(self.walk*2))*2.0
        sx=1.0+0.12*wob; sy=1.0-0.12*wob
        cy=self.y-bob
        esh=pygame.Surface((self.radius*2+4,self.radius),pygame.SRCALPHA)
        pygame.draw.ellipse(esh,(0,0,0,80),esh.get_rect())
        s.blit(esh,(self.x-self.radius-2,self.y+self.radius-5))
        img = BOSS_IMG if self.is_boss else ENEMY_IMG
        if img is not None:
            dw=max(1,int(self.radius*2*sx)); dh=max(1,int(self.radius*2*sy))
            sp=pygame.transform.smoothscale(img,(dw,dh))
            s.blit(sp, sp.get_rect(center=(int(self.x),int(cy))))
        else:
            outline = (90,90,90) if self.color==WHITE else BLACK
            rw=max(1,int(self.radius*sx)); rh=max(1,int(self.radius*sy))
            erect=pygame.Rect(0,0,rw*2,rh*2); erect.center=(int(self.x),int(cy))
            pygame.draw.ellipse(s,self.color,erect)
            pygame.draw.ellipse(s,outline,erect,2)
        if self.poison_timer>0:
            pygame.draw.circle(s,POISONC,(int(self.x),int(cy)),self.radius+3,2)
        if self.slow_timer>0:   # заморозка (дебафф «Мороз»)
            fr=pygame.Surface((self.radius*2+12,self.radius*2+12),pygame.SRCALPHA)
            pygame.draw.circle(fr,(140,220,255,55),(self.radius+6,self.radius+6),self.radius+5)
            s.blit(fr,(self.x-self.radius-6,cy-self.radius-6))
            pygame.draw.circle(s,CYAN,(int(self.x),int(cy)),self.radius+5,2)
        if self.flash>0:
            fl=pygame.Surface((self.radius*2+8,self.radius*2+8),pygame.SRCALPHA)
            pygame.draw.circle(fl,(255,255,255,150),(self.radius+4,self.radius+4),self.radius)
            s.blit(fl,(self.x-self.radius-4,cy-self.radius-4))
        # HP-бар появляется после урона; цвет ПЛАВНО перетекает зелёный → красный
        if self.hp < self.max_hp:
            w=max(self.radius*2, 24); bx=self.x-w/2; by=self.y-self.radius-11
            frac=max(0.0,min(1.0,self.hp/self.max_hp))
            pygame.draw.rect(s,(18,16,22),(bx-1,by-1,w+2,6),border_radius=3)
            col=(int(235-frac*155), int(60+frac*165), 70)
            pygame.draw.rect(s,col,(bx,by,int(w*frac),4),border_radius=2)
        # маркеры особых врагов
        if self.kind=="flying":
            halo=pygame.Surface((self.radius*4,self.radius*4),pygame.SRCALPHA)
            pygame.draw.circle(halo,(180,210,255,60),(self.radius*2,self.radius*2),self.radius*2)
            s.blit(halo,(int(self.x-self.radius*2),int(cy-self.radius*2)))
            pygame.draw.circle(s,(210,230,255),(int(self.x),int(cy)),self.radius+4,2)
        elif self.kind=="shooter":
            _h=G.get("hero")
            ha=math.atan2(_h.y-self.y,_h.x-self.x) if _h else 0
            ex=self.x+math.cos(ha)*(self.radius+10); ey=cy+math.sin(ha)*(self.radius+10)
            pygame.draw.line(s,(40,40,48),(int(self.x),int(cy)),(int(ex),int(ey)),5)
            pygame.draw.circle(s,(70,70,80),(int(ex),int(ey)),3)
        if self.name:
            t=font_s.render(self.name,True,WHITE)
            s.blit(t,(self.x-t.get_width()/2, self.y-self.radius-30))
        # мегалодон, плавающий по кругу и отбивающий пули
        if self.is_boss and self.boss_kind=="shark":
            mx,my=self.meg_x,self.meg_y
            ang=self.meg_ang+math.pi/2
            cs,sn=math.cos(ang),math.sin(ang)
            def _mp(lx,ly): return (int(mx+lx*cs-ly*sn),int(my+lx*sn+ly*cs))
            body=[_mp(0,-18),_mp(9,0),_mp(0,18),_mp(-9,0)]
            pygame.draw.polygon(s,(95,115,135),body); pygame.draw.polygon(s,(35,45,60),body,2)
            tail=[_mp(0,18),_mp(-7,28),_mp(7,28)]
            pygame.draw.polygon(s,(80,100,120),tail)
            fin=[_mp(0,-3),_mp(-12,-16),_mp(2,-7)]
            pygame.draw.polygon(s,(70,90,110),fin)
            pygame.draw.circle(s,(230,240,255),_mp(3,-9),2)
        # бита Валеры в момент оглушающего удара
        if self.is_boss and self.boss_kind=="stun" and self.bat_swing>0:
            bx=self.x+self.radius; by=self.y
            pygame.draw.line(s,(120,80,40),(self.x,self.y),(bx+18,by-26),7)
            pygame.draw.circle(s,(150,100,55),(int(bx+18),int(by-26)),9)


class Turret:
    def __init__(self,x,y,kind,level=1,priority="Первый"):
        self.x,self.y=x,y; self.kind=kind; self.level=level
        self.base=TURRETS[kind]
        self.color=self.base["color"]; self.bspeed=self.base["bspeed"]
        self.aoe=self.base["aoe"]; self.slow=self.base["slow"]
        self.timer=0.0; self.angle=0.0; self.target_angle=0.0
        self.priority=priority
        self.spec=None; self.spec_name=None
        self.income_timer=self.base.get("interval",3.0)
        self.invested=self.base["cost"]
        for lv in range(1, self.level):
            self.invested += int(self.base["cost"]*0.8*lv)
        self.apply_level()
    def apply_level(self):
        mult = 1 + 0.4*(self.level-1)
        self.dmg = self.base["dmg"]*mult
        self.range = self.base["range"] + 18*(self.level-1)
        self.cooldown = self.base["cooldown"]*(1 - 0.07*(self.level-1))
        self.poison_dps = self.base["poison"]*mult
    def upgrade_cost(self):
        return int(self.base["cost"]*0.8*self.level)
    def sell_value(self):
        return int(self.invested*0.5)
    def can_specialize(self):
        return self.level>=3 and getattr(self,"spec",None) is None and self.kind in TURRET_SPECS
    def specialize(self, spec_key):
        for sp in TURRET_SPECS.get(self.kind, []):
            if sp["key"]==spec_key:
                m=sp["mods"]
                self.dmg*=m.get("dmg",1.0)
                self.cooldown*=m.get("cooldown",1.0)
                self.range*=m.get("range",1.0)
                if "aoe_set" in m: self.aoe=m["aoe_set"]
                if "slow_set" in m: self.slow=m["slow_set"]
                if "poison_mul" in m and hasattr(self,"poison_dps"): self.poison_dps*=m["poison_mul"]
                if sp.get("color"): self.color=sp["color"]
                self.spec=sp["key"]; self.spec_name=sp["name"]
                return True
        return False
    def pick_target(self,enemies):
        rng=self.range*G.get("mut_range",1.0)   # мутатор «Туман» снижает радиус
        in_range=[e for e in enemies if e.alive and dist(self.x,self.y,e.x,e.y)<=rng]
        if not in_range:
            return None
        if self.priority=="Сильнейший": return max(in_range,key=lambda e:e.hp)
        if self.priority=="Слабейший": return min(in_range,key=lambda e:e.hp)
        if self.priority=="Последний": return min(in_range,key=enemy_progress)
        return max(in_range,key=enemy_progress)  # Первый
    def update(self,dt,enemies,bullets):
        self.timer-=dt
        if self.base.get("dtype")=="econ":   # Банк: не стреляет, даёт пассивный доход
            self.income_timer=getattr(self,"income_timer",self.base.get("interval",3.0))-dt
            if self.income_timer<=0:
                self.income_timer=self.base.get("interval",3.0)
                amt=self.base.get("income",15)+(self.level-1)*8
                G["money"]=G.get("money",0)+amt
                G["floats"].append(FloatText(self.x,self.y-24,"+"+str(amt),(245,225,150)))
                play_sound("buy", throttle_ms=80)
            return
        if self.base.get("dtype")=="summon":   # Казарма: призывает союзников на дорогу
            if G.get("state")!="wave":          # во время перерыва между волнами не призывает
                return
            self.income_timer=getattr(self,"income_timer",self.base.get("interval",7.0))-dt
            if self.income_timer<=0:
                self.income_timer=self.base.get("interval",7.0)
                _ensure_allies().append(Ally(hp=45+self.level*22, dmg=9+self.level*5, speed=70, level=self.level))
                play_sound("buy", throttle_ms=120)
            return
        if G.get("turret_stun",0)>0:   # башни оглушены битой Валеры
            return
        target=self.pick_target(enemies)
        if target:
            self.target_angle=math.atan2(target.y-self.y, target.x-self.x)
            # ПЛАВНЫЙ доворот пушки к цели (lerp по кратчайшей дуге)
            diff=(self.target_angle-self.angle+math.pi)%(2*math.pi)-math.pi
            self.angle+=diff*min(1.0, 12.0*dt)
            # стреляем, только когда пушка уже почти навелась
            if self.timer<=0 and abs(diff)<0.30:
                self.timer=self.cooldown
                # стреляем самонаводящейся пулей (всегда попадает)
                vx=math.cos(self.angle)*self.bspeed; vy=math.sin(self.angle)*self.bspeed
                blen=20+self.level*4
                mx=self.x+math.cos(self.angle)*blen; my=self.y+math.sin(self.angle)*blen
                spawn_muzzle(G["particles"], mx, my, self.angle, self.color)  # muzzle flash
                play_sound("shoot", throttle_ms=45)
                if self.kind in ("Пушка","Пулемёт"):
                    spawn_shell(self.x, self.y, self.angle)   # гильза из башни
                bullets.append(Bullet(self.x,self.y,vx,vy,self.dmg,self.color,5,self.aoe,self.slow,self.poison_dps,target=target,dtype=self.base.get("dtype","phys")))
    def draw(self,s,show_range=False,selected=False):
        if show_range:
            ring_col=YELLOW if selected else self.color
            draw_range_ring(s, self.x, self.y, int(self.range*G.get("mut_range",1.0)), ring_col, selected)
        base_r=14+self.level*3
        sh=pygame.Surface((base_r*2+10,base_r+8),pygame.SRCALPHA)
        pygame.draw.ellipse(sh,(0,0,0,90),sh.get_rect())
        s.blit(sh,(self.x-base_r-5,self.y+base_r-6))
        if self.base.get("dtype")=="econ":
            self._draw_bank(s, base_r, selected); return
        if self.base.get("dtype")=="summon":
            self._draw_barracks(s, base_r, selected); return
        if TURRET_BASE_IMG is not None and TURRET_CANNON_IMG is not None:
            # башня из двух картинок: неподвижная база + вращающаяся пушка
            draw_sprite(s, TURRET_BASE_IMG, self.x, self.y, 0.0, scale=(base_r*2)/TURRET_BASE_IMG.get_width())
            draw_sprite(s, TURRET_CANNON_IMG, self.x, self.y, self.angle, scale=(base_r*2)/TURRET_CANNON_IMG.get_width())
            if self.level>=2: pygame.draw.circle(s,LIGHT,(int(self.x),int(self.y)),base_r+4,2)
            if self.level>=3: pygame.draw.circle(s,YELLOW,(int(self.x),int(self.y)),base_r+8,2)
            if selected: pygame.draw.circle(s,YELLOW,(int(self.x),int(self.y)),base_r+8,3)
            return
        # внешний вид башни меняется с уровнем прокачки
        if self.level>=2:
            pygame.draw.circle(s,LIGHT,(int(self.x),int(self.y)),base_r+4,2)
        if self.level>=3:
            pygame.draw.circle(s,YELLOW,(int(self.x),int(self.y)),base_r+8,2)
        self._draw_body(s, base_r, selected)

    def _draw_body(self, s, base_r, selected):
        """Уникальная мини-текстура под каждый тип башни; облик меняется с уровнем."""
        x,y=int(self.x),int(self.y); k=self.kind; spec=getattr(self,"spec",None)
        a=self.angle; cs,sn=math.cos(a),math.sin(a); lvl=self.level
        col=self.color; dark=tuple(int(c*0.55) for c in col)
        def barrel(length,width,bcol=(30,30,38)):
            ex=x+cs*length; ey=y+sn*length
            pygame.draw.line(s,bcol,(x,y),(int(ex),int(ey)),width)
        if k=="Пушка":
            r=pygame.Rect(0,0,base_r*2,base_r*2); r.center=(x,y)
            pygame.draw.rect(s,col,r,border_radius=5)
            pygame.draw.rect(s,dark,r,2,border_radius=5)
            barrel(24+lvl*4,9+lvl); pygame.draw.circle(s,(60,60,72),(x,y),max(5,lvl+4))
        elif k=="Пулемёт":
            pts=[(int(x+math.cos(a+i*math.pi/3)*base_r), int(y+math.sin(a+i*math.pi/3)*base_r)) for i in range(6)]
            pygame.draw.polygon(s,col,pts); pygame.draw.polygon(s,dark,pts,2)
            for oy in (-3,3):
                ex=x+cs*(22+lvl*3)-sn*oy; ey=y+sn*(22+lvl*3)+cs*oy
                pygame.draw.line(s,(30,30,38),(int(x-sn*oy),int(y+cs*oy)),(int(ex),int(ey)),3+lvl//2)
        elif k=="Огнемёт":
            pygame.draw.circle(s,col,(x,y),base_r); pygame.draw.circle(s,dark,(x,y),base_r,2)
            barrel(18+lvl*2,9+lvl,(120,50,30))
            pygame.draw.circle(s,(255,140,40),(int(x+cs*(18+lvl*2)),int(y+sn*(18+lvl*2))),5+lvl)
        elif k=="Мороз":
            pts=[(int(x+math.cos(a+i*math.pi/2)*base_r), int(y+math.sin(a+i*math.pi/2)*base_r)) for i in range(4)]
            pygame.draw.polygon(s,col,pts); pygame.draw.polygon(s,(180,240,255),pts,2)
            barrel(20+lvl*2,5,(120,200,230))
        elif k=="Яд":
            pygame.draw.circle(s,col,(x,y),base_r); pygame.draw.circle(s,(70,150,60),(x,y),base_r,2)
            barrel(18+lvl*2,6,(70,150,60))
            pygame.draw.circle(s,POISONC,(int(x+cs*(18+lvl*2)),int(y+sn*(18+lvl*2))),5)
        else:
            pygame.draw.circle(s,col,(x,y),base_r); pygame.draw.circle(s,dark,(x,y),base_r,2)
            barrel(20+lvl*4,4+lvl)
        if spec=="sniper":
            barrel(36+lvl*3,4,(20,40,60)); pygame.draw.circle(s,CYAN,(x,y),5)
        elif spec=="shrapnel":
            for da in (-0.34,0.34):
                pygame.draw.line(s,(30,30,38),(x,y),(int(x+math.cos(a+da)*(24+lvl*3)),int(y+math.sin(a+da)*(24+lvl*3))),5)
        for i in range(lvl):
            pygame.draw.circle(s,YELLOW,(x-(lvl-1)*4+i*8,y+base_r+7),2)
        pygame.draw.circle(s,YELLOW if selected else BLACK,(x,y),base_r,3 if selected else 2)
        if spec is not None:
            pygame.draw.circle(s,self.color,(x,y),base_r+11,2)

    def _draw_bank(self, s, base_r, selected):
        """Постройка пассивного дохода (не стреляет)."""
        x,y=int(self.x),int(self.y)
        body=pygame.Rect(0,0,base_r*2,base_r*2); body.center=(x,y)
        draw_round_gradient(body,(120,220,160),(50,140,95),8)
        pygame.draw.rect(s,(20,60,40),body,2,border_radius=8)
        pygame.draw.polygon(s,(70,170,120),[(x-base_r-2,y-base_r+2),(x+base_r+2,y-base_r+2),(x,y-base_r-10)])
        t=font_m.render("$",True,(20,60,40)); s.blit(t,(x-t.get_width()//2,y-t.get_height()//2))
        if selected: pygame.draw.circle(s,YELLOW,(x,y),base_r+8,3)

    def _draw_barracks(self, s, base_r, selected):
        """Казарма: призывает союзников, идущих по дороге от базы."""
        x,y=int(self.x),int(self.y)
        body=pygame.Rect(0,0,base_r*2,int(base_r*1.7)); body.center=(x,y+2)
        draw_round_gradient(body,(120,160,240),(45,80,170),6)
        pygame.draw.rect(s,(18,30,70),body,2,border_radius=6)
        pygame.draw.line(s,(40,50,90),(x,y-base_r-10),(x,y-base_r+2),2)
        pygame.draw.polygon(s,(230,90,80),[(x,y-base_r-10),(x+14,y-base_r-6),(x,y-base_r-2)])
        pygame.draw.line(s,(230,235,255),(x-7,y+6),(x+7,y-6),3)
        pygame.draw.line(s,(230,235,255),(x-7,y-6),(x+7,y+6),3)
        if selected: pygame.draw.circle(s,YELLOW,(x,y),base_r+8,3)


def _tp(x,y,cs,sn,lx,ly):
    return (int(x+lx*cs-ly*sn), int(y+lx*sn+ly*cs))

def draw_gun(s, x, y, angle, weapon):
    img = WEAPON_IMG.get(weapon)
    if img is not None:
        cs0, sn0 = math.cos(angle), math.sin(angle)
        src = pygame.transform.flip(img, False, True) if abs(angle) > math.pi/2 else img
        rot = pygame.transform.rotate(src, -math.degrees(angle))
        off = img.get_width()*0.32
        gx, gy = x+cs0*off, y+sn0*off
        s.blit(rot, (int(gx-rot.get_width()/2), int(gy-rot.get_height()/2)))
        return
    # Детальные нарисованные модельки оружия (фолбэк без файлов)
    cs, sn = math.cos(angle), math.sin(angle)
    flip = -1 if abs(angle) > math.pi/2 else 1
    def P(pts,col,outline=BLACK):
        sp=[_tp(x,y,cs,sn,lx,ly*flip) for lx,ly in pts]
        pygame.draw.polygon(s,col,sp); pygame.draw.polygon(s,outline,sp,1)
    def C(lx,ly,r,col,outline=None):
        c=_tp(x,y,cs,sn,lx,ly*flip)
        pygame.draw.circle(s,col,c,r)
        if outline: pygame.draw.circle(s,outline,c,r,1)
    steel=(70,78,92); dark=(45,48,58); brown=(120,72,38); olive=(95,105,60); gray=(120,120,130)
    if weapon=="Пистолет":
        P([(-5,-5),(17,-5),(17,1),(-5,1)],steel)
        P([(-3,1),(4,1),(1,11),(-6,10)],brown)
        C(17,-2,2,dark)
    elif weapon=="Пистолет-пулемёт":
        P([(-7,-5),(21,-5),(21,2),(-7,2)],dark)
        P([(21,-3),(31,-3),(31,1),(21,1)],steel)
        P([(2,2),(8,3),(9,15),(3,15)],(60,65,75))
        P([(-5,2),(1,2),(-2,12),(-8,11)],olive)
    elif weapon=="Дробовик":
        P([(-3,-4),(35,-4),(35,1),(-3,1)],steel)
        P([(9,1),(22,1),(22,6),(9,6)],brown)
        P([(-15,-3),(-3,-4),(-3,3),(-13,7)],brown)
    elif weapon=="Снайперка":
        P([(-8,-3),(42,-3),(42,1),(-8,1)],dark)
        P([(-18,-4),(-8,-4),(-8,5),(-16,7)],olive)
        P([(7,-8),(24,-8),(24,-4),(7,-4)],(30,30,36))
        C(9,-6,2,CYAN); C(22,-6,2,CYAN)
    elif weapon=="Миниган":
        for oy in (-5,-1.7,1.7,5):
            P([(2,oy-1),(40,oy-1),(40,oy+1),(2,oy+1)],dark,dark)
        P([(-2,-8),(16,-8),(16,8),(-2,8)],olive)
        P([(8,-8),(12,-16),(16,-16),(14,-8)],brown)
    elif weapon=="Базука":
        P([(-12,-7),(34,-7),(34,7),(-12,7)],olive)
        P([(34,-5),(46,0),(34,5)],RED)
        P([(2,7),(7,7),(5,17),(0,16)],brown)
        P([(6,-7),(9,-7),(9,7),(6,7)],gray,gray)
        P([(20,-7),(23,-7),(23,7),(20,7)],gray,gray)
    else:
        P([(-4,-4),(16,-4),(16,2),(-4,2)],steel)


def draw_hero_skin(s, cx, cy, radius, label=None, idx=None):
    if idx is None: idx = PROFILE["skin_idx"]
    src = SKIN_PREVIEW[idx] if radius > 30 else SKIN_HERO[idx]
    if idx == 0 or src is None:
        col = GREEN if idx == 0 else GRAY
        pygame.draw.circle(s, col, (int(cx),int(cy)), radius)
        pygame.draw.circle(s, BLACK, (int(cx),int(cy)), radius, 2)
    else:
        d = radius*2
        im = src if src.get_width()==d else pygame.transform.smoothscale(src,(d,d))
        s.blit(im, (cx-radius, cy-radius))
        pygame.draw.circle(s, BLACK, (int(cx),int(cy)), radius, 2)
    if label:
        t=font_s.render(label,True,WHITE)
        s.blit(t,(cx-t.get_width()/2, cy-radius-20))


class Hero:
    def __init__(self):
        self.x,self.y = 540, 670
        self.speed=4.4; self.radius=16
        self.weapon="Пистолет"; self.timer=0.0; self.angle=0.0
        self.max_hp=120; self.hp=120; self.hurt_cd=0.0
        self.burst_left=0; self.burst_timer=0.0; self.burst_gap=0.06
        # ---- оглушение (боссом Валерой) ----
        self.stun=0.0
    def update(self,dt,keys):
        world_extras_update(dt)   # день/ночь, снаряды врагов, достижения
        if self.stun>0:
            self.stun-=dt; self.timer-=dt; self.hurt_cd-=dt
            return
        if keys[pygame.K_w] or keys[pygame.K_UP]:    self.y-=self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  self.y+=self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  self.x-=self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.x+=self.speed
        self.x=max(16, min(WIDTH-16, self.x))
        self.y=max(52, min(HEIGHT-16, self.y))
        self.timer-=dt; self.hurt_cd-=dt
        mx,my=pygame.mouse.get_pos()
        self.angle=math.atan2(my-self.y, mx-self.x)
        if self.burst_left>0:
            self.burst_timer-=dt
            if self.burst_timer<=0:
                self._fire_volley(); self.burst_left-=1; self.burst_timer=self.burst_gap
    def _fire_volley(self):
        w=WEAPONS[self.weapon]
        rad = 7 if w["aoe"]>0 else 5
        for _ in range(w["pellets"]):
            a=self.angle+random.uniform(-w["spread"],w["spread"])
            vx=math.cos(a)*w["speed"]; vy=math.sin(a)*w["speed"]
            G["bullets"].append(Bullet(self.x,self.y,vx,vy,w["dmg"],w["color"],rad,w["aoe"]))
        mx=self.x+math.cos(self.angle)*self.radius; my=self.y+math.sin(self.angle)*self.radius
        spawn_muzzle(G["particles"], mx, my, self.angle, w["color"])  # muzzle flash
        play_sound("shoot", throttle_ms=40)
        if self.weapon in ("Пистолет","Дробовик","Миниган"):
            spawn_shell(self.x, self.y, self.angle)   # вылет гильзы
        if self.weapon in ("Снайперка", "Базука"):
            add_shake(8 if self.weapon=="Базука" else 5)
    def shoot(self):
        if self.timer>0 or self.burst_left>0 or self.stun>0: return
        w=WEAPONS[self.weapon]; self.timer=w["cooldown"]
        if w.get("burst",1)>1:
            self.burst_left=w["burst"]; self.burst_timer=0.0; self.burst_gap=w.get("burst_gap",0.06)
        else:
            self._fire_volley()
    def draw(self,s):
        sh=pygame.Surface((self.radius*2+6,self.radius),pygame.SRCALPHA)
        pygame.draw.ellipse(sh,(0,0,0,90),sh.get_rect())
        s.blit(sh,(self.x-self.radius-3,self.y+self.radius-6))
        if HERO_SPRITE is not None:
            draw_sprite(s, HERO_SPRITE, self.x, self.y, self.angle)
            lbl=font_s.render("Матвей",True,WHITE)
            s.blit(lbl,(self.x-lbl.get_width()/2, self.y-self.radius-20))
        else:
            draw_hero_skin(s, self.x, self.y, self.radius, "Матвей")
        draw_gun(s, self.x, self.y, self.angle, self.weapon)
        if self.stun>0:
            st=font_m.render("★",True,YELLOW)
            s.blit(st,(self.x-st.get_width()/2,self.y-self.radius-34))


# ----- Мутаторы волн (случайные события) -----
MUTATORS = [
    {"key":"fog","name":"ТУМАН","desc":"Радиус стрельбы всех башен снижен на волну","color":(150,170,200)},
    {"key":"berserk","name":"БЕРСЕРКИ","desc":"Враги быстрее, но у них меньше HP","color":(230,90,80)},
    {"key":"gold","name":"ЗОЛОТАЯ ЛИХОРАДКА","desc":"Из врагов падает вдвое больше денег","color":(245,205,70)},
]

def make_wave(n):
    enemies=[]
    endless=G.get("endless")
    es=(1.18**(n-15)) if (endless and n>15) else 1.0   # экспоненциальный рост (Endless)
    berserk = G.get("mutator")=="berserk"
    if n % 10 == 0:
        if n==10:
            b=Enemy(2600, 1.4, PURPLE, 34, 320, "Ренат Мингаз", is_boss=True); b.boss_kind="shark"
            enemies.append(b)
        elif n==20:
            b=Enemy(5200, 1.6, ORANGE, 40, 520, "Валера Огнерубов", is_boss=True); b.boss_kind="stun"
            enemies.append(b)
        else:
            b=Enemy(9000 + (n-30)*2300, 1.7, RED, 52, 1600, "Диван Шир", is_boss=True); b.boss_kind="summon"; b.ability_timer=15.0
            enemies.append(b)
        for i in range(6 + n):
            enemies.append(Enemy(60 + n*8, 2.2, GRAY, 12, 9))
    else:
        for i in range(6 + n*2):
            col = RED if i%3 else BLUE
            enemies.append(Enemy(38 + n*16, 2.0 + n*0.05, col, 12, 7))
        # Стрелки (bullet hell) — с 4-й волны
        if n>=4:
            for _ in range(1 + n//4):
                enemies.append(Enemy(70 + n*14, 1.6, (240,150,60), 13, 12, kind="shooter"))
    if endless and es>1.0:            # Endless: экспоненциальный рост HP / скорости / числа
        for _ in range(int((es-1)*4)):
            enemies.append(Enemy(int((40+n*16)*es), 2.1, random.choice((RED,BLUE)), 12, 9))
        for e in enemies:
            if not e.is_boss:
                e.max_hp=int(e.max_hp*es); e.hp=e.max_hp
                e.speed=min(e.speed*(es**0.25), 4.0)
    if berserk:                       # мутатор «Берсерки»: быстрее, но меньше HP
        for e in enemies:
            e.max_hp=max(1,int(e.max_hp*0.6)); e.hp=e.max_hp; e.speed*=1.4
    return enemies


# ====================== КАМЕРА ======================
class Camera:
    """Плавная камера: следует за целью, если карта больше экрана.
    На картах, помещающихся в экран, остаётся в (0,0) и рендер не смещается."""
    def __init__(self):
        self.x=0.0; self.y=0.0; self.world_w=WIDTH; self.world_h=HEIGHT
    def set_world(self,w,h):
        self.world_w=max(WIDTH,w); self.world_h=max(HEIGHT,h)
    def follow(self,tx,ty,smooth=0.08):
        if self.world_w<=WIDTH and self.world_h<=HEIGHT:
            self.x=0.0; self.y=0.0; return
        gx=max(0,min(self.world_w-WIDTH, tx-WIDTH/2))
        gy=max(0,min(self.world_h-HEIGHT, ty-HEIGHT/2))
        self.x+=(gx-self.x)*smooth; self.y+=(gy-self.y)*smooth
    def apply(self,x,y):
        return (int(x-self.x), int(y-self.y))

CAMERA = Camera()

# ====================== НОВЫЕ СИСТЕМЫ (v7) ======================
# Снаряды врагов, цикл день/ночь + освещение, достижения. Легко расширять.

class EnemyBullet:
    """Медленный снаряд вражеского «стрелка» — летит в Матвея (bullet hell)."""
    def __init__(self, x, y, vx, vy, dmg=12):
        self.x=x; self.y=y; self.vx=vx; self.vy=vy
        self.dmg=dmg; self.radius=7; self.life=7.0; self.alive=True
    def update(self, dt):
        self.x+=self.vx; self.y+=self.vy; self.life-=dt
        if self.life<=0 or not (-40<self.x<WIDTH+40 and -40<self.y<HEIGHT+40):
            self.alive=False
    def draw(self, s):
        draw_additive_glow(s, self.x, self.y, 12, (255,80,90), intensity=150)
        pygame.draw.circle(s,(230,60,70),(int(self.x),int(self.y)),self.radius)
        pygame.draw.circle(s,(255,225,190),(int(self.x-2),int(self.y-2)),3)

# ----- День / Ночь + динамическое освещение (фонарики) -----
def night_strength():
    """0.0 — день, 1.0 — глубокая ночь (плавный цикл)."""
    return (1 - math.cos(G.get("daytime",0.0)*2*math.pi))/2

_LIGHT_CACHE={}
def get_light(radius):
    """Кэшированная радиальная маска света (ярче в центре, гаснет к краю)."""
    r=max(8,int(radius))
    if r in _LIGHT_CACHE: return _LIGHT_CACHE[r]
    surf=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
    steps=22
    for i in range(steps,0,-1):
        rr=int(r*i/steps); a=int(255*(1-i/steps))
        pygame.draw.circle(surf,(255,255,255,a),(r,r),rr)
    _LIGHT_CACHE[r]=surf
    return surf

def draw_night_overlay():
    """Тёмный слой ночи с «вырезанными» кругами света у Матвея и башен."""
    ns=night_strength()
    if ns<=0.03: return
    overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    overlay.fill((6,10,32,int(210*ns)))
    overlay.fill((0,0,0,0), pygame.Rect(0,0,WIDTH,52))   # не затемнять верхний HUD
    def cut(x,y,radius):
        lm=get_light(radius)
        overlay.blit(lm,(int(x-radius),int(y-radius)),special_flags=pygame.BLEND_RGBA_SUB)
    h=G.get("hero")
    if h: cut(h.x,h.y,160)                      # фонарик Матвея
    for t in G.get("turrets",[]):
        cut(t.x,t.y,95+t.level*10)              # подсветка вокруг башен
    screen.blit(overlay,(0,0))

# ----- Достижения (ачивки) -----
ACHIEVEMENTS = [
    {"id":"kill100","name":"Истребитель","desc":"Убить 100 врагов","reward":50,
     "check":lambda g: g.get("kills",0)>=100},
    {"id":"wave10","name":"Несокрушимый","desc":"Пережить 10 волн","reward":80,
     "check":lambda g: g.get("wave",1)>=10},
    {"id":"build5","name":"Архитектор","desc":"Построить 5 башен","reward":40,
     "check":lambda g: g.get("max_turrets",0)>=5},
]

class AchToast:
    """Плашка достижения: выезжает снизу с кубком, держится и уезжает."""
    def __init__(self, name, reward):
        self.name=name; self.reward=reward; self.t=0.0; self.life=3.8
    def update(self, dt):
        self.t+=dt; return self.t<self.life
    def draw(self, s, slot=0):
        appear=min(1.0,self.t/0.4); leave=min(1.0,max(0.0,(self.life-self.t)/0.4))
        k=min(appear,leave)
        w,hh=330,62; x=WIDTH//2-w//2
        base_y=HEIGHT-24-slot*(hh+10)
        y=int(base_y - k*(hh+8))            # выезд снизу вверх
        rect=pygame.Rect(x,y,w,hh)
        draw_round_gradient(rect,(60,52,90),(34,30,54),14)
        pygame.draw.rect(s,(245,205,70),rect,2,border_radius=14)
        cx,cy=x+34,y+hh//2                   # кубок
        pygame.draw.polygon(s,(245,205,70),[(cx-12,cy-12),(cx+12,cy-12),(cx+8,cy+4),(cx-8,cy+4)])
        pygame.draw.rect(s,(245,205,70),(cx-3,cy+4,6,8))
        pygame.draw.rect(s,(220,180,60),(cx-9,cy+12,18,4),border_radius=2)
        pygame.draw.arc(s,(245,205,70),(cx-20,cy-12,16,18),1.2,2.8,3)
        pygame.draw.arc(s,(245,205,70),(cx+4,cy-12,16,18),0.34,1.94,3)
        t1=font_m.render("Достижение!",True,(245,205,70))
        t2=font_s.render(self.name,True,WHITE)
        t3=font_s.render("+"+str(self.reward)+" монет",True,(245,225,150))
        s.blit(t1,(x+62,y+8)); s.blit(t2,(x+62,y+32))
        s.blit(t3,(x+w-t3.get_width()-14,y+34))

def check_achievements():
    """Проверяет достижения по состоянию и выдаёт монеты + плашку."""
    G["max_turrets"]=max(G.get("max_turrets",0), len(G.get("turrets",[])))
    done=PROFILE.setdefault("achievements",[])
    for a in ACHIEVEMENTS:
        if a["id"] not in done and a["check"](G):
            done.append(a["id"])
            PROFILE["coins"]=PROFILE.get("coins",0)+a["reward"]
            G.setdefault("ach_toasts",[]).append(AchToast(a["name"],a["reward"]))
            play_sound("buy"); save_profile()

# ----- Покадровое обновление и отрисовка новых систем (вызывать из game loop) -----
def world_extras_update(dt):
    """Тик день/ночь + снаряды врагов (попадание по Матвею) + достижения. Раз за кадр."""
    G["daytime"]=(G.get("daytime",0.0)+dt*0.012)%1.0   # полный цикл ~80с
    h=G.get("hero")
    bl=G.get("enemy_bullets",[])
    for b in bl:
        b.update(dt)
        if h and b.alive and dist(b.x,b.y,h.x,h.y)<h.radius+b.radius:
            b.alive=False
            if h.hurt_cd<=0:
                h.hp-=b.dmg; h.hurt_cd=0.45
                add_hurt_flash(0.7); add_shake(5); play_sound("hurt")
    G["enemy_bullets"]=[b for b in bl if b.alive]
    check_achievements()
    G["ach_toasts"]=[t for t in G.get("ach_toasts",[]) if t.update(dt)]

def draw_night_and_extras():
    """Затемнение ночи + свет, снаряды врагов и плашки достижений. В конце draw_game (перед HUD)."""
    draw_night_overlay()
    for b in G.get("enemy_bullets",[]):
        b.draw(screen)
    for i,t in enumerate(G.get("ach_toasts",[])):
        t.draw(screen,i)

# Авто-подключение ночи/достижений к КОНЦУ каждого кадра — без правок game loop.
# Оборачиваем pygame.display.flip/update: рисуем оверлей поверх мира перед показом.
_real_flip = pygame.display.flip
_real_update = pygame.display.update
def _draw_extras_safe():
    try:
        if isinstance(G, dict) and G.get("state") in ("wave","build","mutator_warn"):
            draw_night_and_extras()
    except Exception:
        pass
def _flip_with_extras(*a, **k):
    _draw_extras_safe(); return _real_flip(*a, **k)
def _update_with_extras(*a, **k):
    _draw_extras_safe(); return _real_update(*a, **k)
pygame.display.flip = _flip_with_extras
pygame.display.update = _update_with_extras

# ====================== СОСТОЯНИЕ ИГРЫ ======================
def new_game(map_idx=None, hardcore=False, endless=False, max_waves=15):
    if map_idx is None:
        map_idx = random.randrange(len(MAPS))
    set_map(map_idx)
    return {
        "state": "build", "wave": 1, "money": 250, "lives": 20,
        "endless": endless, "max_waves": max_waves, "level_name": MAPS[map_idx].get("name",""),
        "hero": Hero(), "turrets": [], "enemies": [], "bullets": [], "effects": [], "particles": [], "floats": [], "pickups": [], "shells": [], "splats": [],
        "barrels": [], "traps": [], "selected_trap": None, "drone": None, "lasers": [],
        "enemy_bullets": [], "kills": 0, "max_turrets": 0, "daytime": 0.0, "ach_toasts": [],
        "spawn_queue": [], "spawn_timer": 0.0, "turret_stun": 0.0,
        "mutator": None, "mut_range": 1.0, "mut_gold": 1, "mut_warn_timer": 0.0,
        "owned_weapons": {"Пистолет"},
        "selected_turret": None, "sel_turret_obj": None, "last_placed": None,
        "message": "", "map": map_idx,
        "started": False, "resume_state": "build",
        "hardcore": hardcore, "krakulya_done": False,
        "shop_return": "build",
        "skin_view": PROFILE["skin_idx"],
    }

G = new_game(0); G["state"] = "menu"
autosave_timer = 0.0
SHAKE = 0.0  # сила тряски экрана (game feel)
HURT_FLASH = 0.0  # сила красной виньетки при уроне игроку

def add_shake(amount):
    """Добавить тряску экрана (берётся максимум, чтобы выстрелы не складывались бесконечно)."""
    global SHAKE
    SHAKE = min(18.0, max(SHAKE, amount))

def add_hurt_flash(amount=1.0):
    """Красная виньетка по краям экрана при получении урона."""
    global HURT_FLASH
    HURT_FLASH = min(1.0, max(HURT_FLASH, amount))

def draw_hurt_vignette():
    if HURT_FLASH<=0.01: return
    a=int(170*HURT_FLASH)
    vg=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    pygame.draw.rect(vg,(190,20,20,a),vg.get_rect(),width=130,border_radius=70)
    inner=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    pygame.draw.rect(inner,(160,15,15,a//2),inner.get_rect(),width=60,border_radius=40)
    vg.blit(inner,(0,0))
    screen.blit(vg,(0,0))

def turret_limit():
    return 8 + (G["wave"]//5)*2

def type_limit(kind):
    """Отдельный лимит на КАЖДЫЙ тип башни (а не общий на все)."""
    if kind in ("Казарма","Банк"):
        return 2 + (G["wave"]//8)
    return 4 + (G["wave"]//5)

def count_kind(kind):
    return sum(1 for t in G["turrets"] if getattr(t,"kind",None)==kind)

def has_save():
    return os.path.exists(SAVE_FILE)

def save_game(silent=False):
    h=G["hero"]
    data={"version":GAME_VERSION,"wave":G["wave"],"money":G["money"],"lives":G["lives"],"map":G["map"],
          "hardcore":G["hardcore"],"krakulya_done":G["krakulya_done"],"has_drone":G.get("drone") is not None,
          "hero":{"x":h.x,"y":h.y,"hp":h.hp,"weapon":h.weapon},
          "owned_weapons":list(G["owned_weapons"]),
          "turrets":[{"x":t.x,"y":t.y,"kind":t.kind,"level":t.level,"priority":t.priority} for t in G["turrets"]]}
    try:
        with open(SAVE_FILE,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False)
        G["message"]="Автосохранение..." if silent else "Игра сохранена (F5)"
    except Exception:
        G["message"]="Ошибка сохранения"

def load_game():
    if not has_save(): return None
    try:
        with open(SAVE_FILE,"r",encoding="utf-8") as f:
            data=json.load(f)
    except Exception:
        return None
    g=new_game(data.get("map",0), data.get("hardcore",False))
    g["wave"]=data.get("wave",1); g["money"]=data.get("money",250); g["lives"]=data.get("lives",20)
    g["krakulya_done"]=data.get("krakulya_done",False)
    hd=data.get("hero",{}); h=g["hero"]
    h.x=hd.get("x",540); h.y=hd.get("y",670); h.hp=hd.get("hp",120); h.weapon=hd.get("weapon","Пистолет")
    g["owned_weapons"]=set(data.get("owned_weapons",["Пистолет"]))
    if data.get("has_drone"): g["drone"]=Drone()
    g["turrets"]=[Turret(t["x"],t["y"],t["kind"],t.get("level",1),t.get("priority","Первый")) for t in data.get("turrets",[])]
    g["state"]="build"; g["started"]=True; g["message"]="Игра загружена"
    return g

def spawn_barrels():
    """Случайно расставляет взрывоопасные бочки вдоль дороги в начале волны."""
    G["barrels"]=[]
    for _ in range(random.randint(2,4)):
        for _try in range(30):
            i=random.randrange(len(PATH)-1)
            ax,ay=PATH[i]; bx,by=PATH[i+1]
            t=random.random()
            px=ax+(bx-ax)*t; py=ay+(by-ay)*t
            dx,dy=bx-ax,by-ay; L=math.hypot(dx,dy) or 1
            off=random.choice((-1,1))*random.uniform(36,62)
            x=px-dy/L*off; y=py+dx/L*off
            if 30<x<WIDTH-30 and 60<y<HEIGHT-30 and not near_path(x,y,28):
                G["barrels"].append(Barrel(x,y)); break


def start_wave():
    # выбор мутатора волны (шанс 20%)
    G["mutator"]=random.choice(MUTATORS)["key"] if random.random()<0.20 else None
    G["mut_range"]=0.6 if G["mutator"]=="fog" else 1.0
    G["mut_gold"]=2 if G["mutator"]=="gold" else 1
    G["spawn_queue"]=make_wave(G["wave"])
    G["enemies"]=[]; G["effects"]=[]
    G["spawn_timer"]=0.0
    G["turret_stun"]=0.0
    G["selected_turret"]=None; G["sel_turret_obj"]=None; G["last_placed"]=None
    spawn_barrels()   # взрывоопасные бочки на поле
    if G["mutator"]:
        G["mut_warn_timer"]=2.6; G["state"]="mutator_warn"
    else:
        G["state"]="wave"


def draw_button(rect, text, color, selected=False, font=font_s):
    mp=pygame.mouse.get_pos(); hover=rect.collidepoint(mp)
    c=tuple(min(255,int(v*1.18)) for v in color) if hover else color
    sh=rect.move(0,3); pygame.draw.rect(screen,(18,18,26),sh,border_radius=9)
    pygame.draw.rect(screen,c,rect,border_radius=9)
    pygame.draw.rect(screen,WHITE if (selected or hover) else BLACK,rect,3 if (selected or hover) else 2,border_radius=9)
    t=font.render(text,True,BLACK)
    screen.blit(t,(rect.centerx-t.get_width()/2, rect.centery-t.get_height()/2))

def draw_chip(x,y,text,color):
    surf=font_s.render(text,True,BLACK)
    w=surf.get_width()+18
    rect=pygame.Rect(x,y,w,26)
    pygame.draw.rect(screen,color,rect,border_radius=13)
    screen.blit(surf,(x+9,y+4))
    return w

def draw_vgradient(rect, top, bottom):
    h=max(1,rect.height)
    for i in range(h):
        tt=i/max(1,h-1)
        c=(int(top[0]+(bottom[0]-top[0])*tt),
           int(top[1]+(bottom[1]-top[1])*tt),
           int(top[2]+(bottom[2]-top[2])*tt))
        pygame.draw.line(screen,c,(rect.x,rect.y+i),(rect.right,rect.y+i))

def draw_panel(rect, title=None, accent=BLUE):
    shadow=pygame.Surface((rect.width,rect.height),pygame.SRCALPHA)
    shadow.fill((0,0,0,90)); screen.blit(shadow,(rect.x,rect.y+6))
    pygame.draw.rect(screen,PANEL,rect,border_radius=14)
    pygame.draw.rect(screen,accent,pygame.Rect(rect.x,rect.y,rect.width,32),
                     border_top_left_radius=14,border_top_right_radius=14)
    pygame.draw.rect(screen,(120,128,150),rect,2,border_radius=14)
    if title:
        t=font_m.render(title,True,WHITE)
        screen.blit(t,(rect.x+16,rect.y+5))

def draw_round_gradient(rect, top, bottom, radius=12):
    """Вертикальный градиент со скруглёнными углами (temp surface + маска)."""
    surf=pygame.Surface((rect.width,rect.height),pygame.SRCALPHA)
    for i in range(rect.height):
        tt=i/max(1,rect.height-1)
        c=(int(top[0]+(bottom[0]-top[0])*tt),
           int(top[1]+(bottom[1]-top[1])*tt),
           int(top[2]+(bottom[2]-top[2])*tt))
        pygame.draw.line(surf,c,(0,i),(rect.width,i))
    mask=pygame.Surface((rect.width,rect.height),pygame.SRCALPHA)
    pygame.draw.rect(mask,(255,255,255,255),mask.get_rect(),border_radius=radius)
    surf.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
    screen.blit(surf,(rect.x,rect.y))

def draw_stat_icon(surf, kind, x, y):
    """Простые иконки: урон (красный ромб) и цена (золотая монета)."""
    if kind=="dmg":
        pts=[(x,y-7),(x+6,y),(x,y+7),(x-6,y)]
        pygame.draw.polygon(surf,(235,80,80),pts); pygame.draw.polygon(surf,WHITE,pts,1)
    else:
        pygame.draw.circle(surf,(245,205,70),(x,y),7)
        pygame.draw.circle(surf,(190,150,30),(x,y),7,1)
        pygame.draw.circle(surf,(255,235,150),(x-2,y-2),2)

def draw_weapon_icon(surf, weapon, cx, cy, size=34):
    """Иконка оружия: PNG-спрайт, если есть, иначе нарисованная моделька."""
    img=WEAPON_IMG.get(weapon)
    if img is not None:
        w,h=img.get_size(); sc=size/max(w,h)
        ic=pygame.transform.smoothscale(img,(max(1,int(w*sc)),max(1,int(h*sc))))
        surf.blit(ic, ic.get_rect(center=(int(cx),int(cy))))
    else:
        draw_gun(surf, cx-8, cy, 0.0, weapon)

def draw_fancy_button(rect, text, color, selected=False, font=font_s, icon_weapon=None):
    """Современная кнопка: градиент, скругление, тень, hover и эффект нажатия."""
    mp=pygame.mouse.get_pos(); hover=rect.collidepoint(mp)
    pressed=hover and pygame.mouse.get_pressed()[0]
    r=rect.move(0,2) if pressed else rect
    sh=pygame.Surface((r.width,r.height),pygame.SRCALPHA)
    pygame.draw.rect(sh,(0,0,0,120),sh.get_rect(),border_radius=12)
    screen.blit(sh,(r.x,r.y+(2 if pressed else 4)))
    top=tuple(min(255,int(c*(1.5 if hover else 1.35))) for c in color)
    bot=tuple(int(c*0.75) for c in color)
    draw_round_gradient(r, top, bot, 12)
    pygame.draw.rect(screen,(255,255,255) if (selected or hover) else (18,18,26),r,2,border_radius=12)
    tx=r.x+14
    if icon_weapon is not None:
        draw_weapon_icon(screen, icon_weapon, r.x+30, r.centery, 40)
        tx=r.x+62
    t=font.render(text,True,(15,15,20))
    screen.blit(t,(tx, r.centery-t.get_height()//2))
    return r

def draw_menu_button(rect, text, color, font=font_m):
    """Кнопка меню в стиле магазина: градиент + свечение и увеличение при наведении."""
    mp=pygame.mouse.get_pos(); hover=rect.collidepoint(mp)
    r=rect.inflate(12,6) if hover else rect
    if hover:
        glow=pygame.Surface((r.width+26,r.height+26),pygame.SRCALPHA)
        pygame.draw.rect(glow,(color[0],color[1],color[2],70),glow.get_rect(),border_radius=18)
        screen.blit(glow,(r.x-13,r.y-13))
    sh=pygame.Surface((r.width,r.height),pygame.SRCALPHA)
    pygame.draw.rect(sh,(0,0,0,130),sh.get_rect(),border_radius=12)
    screen.blit(sh,(r.x,r.y+5))
    top=tuple(min(255,int(c*(1.5 if hover else 1.32))) for c in color)
    bot=tuple(int(c*0.72) for c in color)
    draw_round_gradient(r, top, bot, 12)
    pygame.draw.rect(screen,(255,255,255) if hover else (18,18,26),r,2,border_radius=12)
    t=font.render(text,True,(15,15,20))
    screen.blit(t,(r.centerx-t.get_width()/2, r.centery-t.get_height()/2))

def draw_close_button(rect):
    """Крестик закрытия окна (с hover-подсветкой)."""
    mp=pygame.mouse.get_pos(); hover=rect.collidepoint(mp)
    col=(225,80,80) if hover else (175,55,55)
    pygame.draw.rect(screen,col,rect,border_radius=8)
    pygame.draw.rect(screen,WHITE,rect,2,border_radius=8)
    cx,cy=rect.center; rr=6
    pygame.draw.line(screen,WHITE,(cx-rr,cy-rr),(cx+rr,cy+rr),3)
    pygame.draw.line(screen,WHITE,(cx-rr,cy+rr),(cx+rr,cy-rr),3)


# ----- Меню -----
MENU_BLUR = None
def _menu_background():
    """Фон меню: своя картинка menu.png, иначе размытый кадр игрового поля."""
    global MENU_BLUR
    if MENU_BG is not None:
        return MENU_BG
    if MENU_BLUR is None and BG_CACHE is not None:
        small=pygame.transform.smoothscale(BG_CACHE,(max(1,WIDTH//10),max(1,HEIGHT//10)))
        MENU_BLUR=pygame.transform.smoothscale(small,(WIDTH,HEIGHT))
    return MENU_BLUR

def draw_menu_bg(dim=150):
    bg=_menu_background()
    if bg is not None:
        screen.blit(bg,(0,0))
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,dim)); screen.blit(ov,(0,0))
    else:
        for yy in range(0,HEIGHT,4):
            c=22+int(22*yy/HEIGHT)
            pygame.draw.rect(screen,(c,c,c+12),(0,yy,WIDTH,4))
    # лёгкая виньетка-рамка по краям для глубины
    vg=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    pygame.draw.rect(vg,(0,0,0,80),vg.get_rect(),width=110,border_radius=40)
    screen.blit(vg,(0,0))

def draw_title(text, y, color, font=font_l):
    """Заголовок-логотип: обводка (stroke) в 8 сторон + мягкая тень снизу."""
    out=font.render(text,True,(15,15,22))
    base=font.render(text,True,color)
    x0=WIDTH/2-base.get_width()/2
    for dx,dy in [(-3,0),(3,0),(0,-3),(0,3),(-3,-3),(3,3),(-3,3),(3,-3)]:
        screen.blit(out,(x0+dx,y+dy))
    sh=font.render(text,True,(0,0,0)); sh.set_alpha(110)
    screen.blit(sh,(x0+5,y+7))
    screen.blit(base,(x0,y))

def main_menu_buttons():
    cx=WIDTH/2
    keys=(["continue"] if G.get("started") else [])+["play","maps","hardcore","skins","settings","patch","part2","exit"]
    n=len(keys); y0=224; step=min(58, max(40, int((HEIGHT-66-y0)/n))); bh=min(46, step-10)
    btns=[]
    for i,key in enumerate(keys):
        btns.append((pygame.Rect(cx-170, y0+i*step, 340, bh), key))
    return btns

def play_menu_buttons():
    cx=WIDTH/2; y=300
    return [(pygame.Rect(cx-140,y,280,54),"new"),
            (pygame.Rect(cx-140,y+68,280,54),"load"),
            (pygame.Rect(cx-140,y+136,280,54),"back")]

# ----- Экран выбора карты и режима -----
def map_select_buttons():
    """Кнопки экрана выбора: ((тип, значение), rect)."""
    cx=WIDTH/2; rects=[]; n=len(MAPS)
    for i in range(n):
        rects.append((("map", i), pygame.Rect(cx-260, 200+i*64, 520, 54)))
    by=200+n*64+12
    rects.append((("mode","normal"),  pygame.Rect(cx-260, by, 250, 50)))
    rects.append((("mode","endless"), pygame.Rect(cx+10,  by, 250, 50)))
    rects.append((("start",None), pygame.Rect(cx-130, by+66, 260, 54)))
    rects.append((("back",None),  pygame.Rect(cx-130, by+128, 260, 44)))
    return rects

def draw_map_select():
    draw_menu_bg(160)
    draw_title("ВЫБОР КАРТЫ", 56, YELLOW)
    sel=G.get("sel_map",0); endless=G.get("sel_endless",False)
    for (kind,val),rect in map_select_buttons():
        if kind=="map":
            lv=MAPS[val]
            draw_menu_button(rect, f"{val+1}. {lv.get('name','Карта')}",
                             (140,210,150) if sel==val else (150,190,230), font=font_m)
        elif kind=="mode":
            on=(endless if val=="endless" else not endless)
            label="БЕСКОНЕЧНЫЙ" if val=="endless" else "ОБЫЧНЫЙ (30 волн)"
            draw_menu_button(rect, label, (245,200,90) if on else (105,105,125), font=font_m)
        elif kind=="start":
            draw_menu_button(rect, "СТАРТ", (130,210,140), font=font_m)
        else:
            draw_menu_button(rect, "НАЗАД", (150,190,230), font=font_m)
    hint=font_s.render("Выбери карту и режим, затем Нажми СТАРТ",True,LIGHT)
    screen.blit(hint,(WIDTH/2-hint.get_width()/2, HEIGHT-40))

def handle_map_select_click(pos):
    """Обработка клика на экране выбора. Возвращает 'start'/'back'/None."""
    for (kind,val),rect in map_select_buttons():
        if rect.collidepoint(pos):
            if kind=="map": G["sel_map"]=val; play_sound("buy")
            elif kind=="mode": G["sel_endless"]=(val=="endless"); play_sound("buy")
            elif kind=="start": return "start"
            elif kind=="back": return "back"
    return None

def start_selected_game():
    """Запуск забега с выбранной картой и режимом."""
    global G
    endless=G.get("sel_endless",False); sm=G.get("sel_map",0)
    G=new_game(sm, hardcore=False, endless=endless, max_waves=30)
    G["started"]=True

# ----- Всплывающее меню над башней (Продать / Улучшить) -----
def tower_popup_rects(t):
    by=max(38, int(t.y - (14+t.level*3) - 46))
    bx=int(t.x-72)
    return {"sell":pygame.Rect(bx,by,68,34), "upgrade":pygame.Rect(bx+76,by,68,34)}

def draw_tower_popup(t):
    r=tower_popup_rects(t)
    pygame.draw.line(screen,(15,15,22),(int(t.x),int(t.y)),(r["sell"].right,r["sell"].bottom),2)
    draw_button(r["sell"], f"-{t.sell_value()}", (225,120,120), font=font_s)
    if t.level<3:
        draw_button(r["upgrade"], f"^{t.upgrade_cost()}", (130,205,150), font=font_s)
    else:
        draw_button(r["upgrade"], "МАКС", (120,120,135), font=font_s)

def handle_tower_popup_click(pos):
    """Клик по кнопкам всплывающего меню выбранной башни. True — клик обработан."""
    t=G.get("sel_turret_obj")
    if not t or t not in G["turrets"]: return False
    r=tower_popup_rects(t)
    if r["sell"].collidepoint(pos):
        G["money"]+=t.sell_value(); G["turrets"].remove(t)
        G["sel_turret_obj"]=None; G["selected_turret"]=None
        play_sound("buy"); G["message"]="Башня продана (+50%)"
        return True
    if r["upgrade"].collidepoint(pos):
        if t.level>=3:
            G["message"]="Максимальный уровень башни"; return True
        c=t.upgrade_cost()
        if G["money"]>=c:
            G["money"]-=c; t.level+=1; t.invested+=c; t.apply_level()
            play_sound("buy"); G["message"]=f"Башня улучшена до ур. {t.level}"
        else:
            G["message"]="Недостаточно денег на улучшение!"
        return True
    return False

def draw_menu():
    draw_menu_bg()
    draw_title("МАТВЕЙ РЯЗАНЦЕВ",62,LIGHT)
    draw_title("ОБОРОНА БАШЕН",112,YELLOW,font=font_xl)
    coins=font_m.render(f"Монеты: {PROFILE['coins']}",True,YELLOW)
    screen.blit(coins,(WIDTH/2-coins.get_width()/2,196))
    if G["state"]=="menu":
        labels={"continue":"ПРОДОЛЖИТЬ","play":"ИГРАТЬ","maps":"ВЫБОР КАРТЫ И РЕЖИМА","hardcore":"ХАРДКОР (только пистолет)",
                "skins":"РЕДАКТОР СКИНОВ","settings":"НАСТРОЙКИ","patch":"ОБНОВЛЕНИЯ","part2":"ЧАСТЬ 2: ВОЗВРАЩЕНИЕ ДИВЫ","exit":"ВЫХОД"}
        colors={"hardcore":(230,120,120),"part2":(200,160,230),"maps":(150,210,170)}
        for rect,key in main_menu_buttons():
            draw_menu_button(rect, labels[key], colors.get(key,(150,190,230)), font=font_m)
    else:
        labels={"new":"НОВАЯ ИГРА","load":"ЗАГРУЗИТЬ","back":"НАЗАД"}
        for rect,key in play_menu_buttons():
            color=(150,190,230)
            if key=="load" and not has_save(): color=(90,90,100)
            draw_menu_button(rect, labels[key], color, font=font_m)
        if not has_save():
            t=font_s.render("Сохранений пока нет",True,WHITE)
            screen.blit(t,(WIDTH/2-t.get_width()/2, 520))

def draw_part2():
    draw_menu_bg(180)
    draw_title("Часть 2: Возвращение Дивы", HEIGHT/2-90, PURPLE)
    draw_title("ПРОДОЛЖЕНИЕ СЛЕДУЕТ...", HEIGHT/2, YELLOW)
    t3=font_s.render("ESC или клик — назад в меню",True,WHITE)
    screen.blit(t3,(WIDTH/2-t3.get_width()/2, HEIGHT/2+80))


# ----- Патч-ноты (история обновлений) -----
PATCH_NOTES = [
    ("Обновление 15 — 30 волн, союзники и авто-апдейт", [
        "30 волн, боссы на 10/20/30, финал — Кракуля",
        "Казарма призывает союзников: ур.1 — ближний бой, ур.2+ — стреляют",
        "Союзники упираются во врагов (не проходят сквозь) и гибнут в бою",
        "У каждого типа башни свой лимит; уникальный вид и смена облика по уровню",
        "Убрана вторая дорожка врагов; ночь сохраняется в меню продавцов",
        "Обновление прямо в игре: всплывает окно «Скачать» без выхода",
    ]),
    ("Обновление 14 — Новые враги, ночь и достижения", [
        "Призрак: летит напрямую к базе, игнорируя дорогу",
        "Стрелок: останавливается и обстреливает Матвея (bullet hell)",
        "Смена дня и ночи с динамическим освещением (фонарик у Матвея и башен)",
        "Система достижений: награды монетами и всплывающие плашки",
    ]),
    ("Обновление 13 — Карты, режимы и башни", [
        "Система уровней (LevelManager): легко добавлять новые карты",
        "Экран Выбора карты и режима в главном меню",
        "Бесконечный режим: экспоненциальный рост врагов",
        "Всплывающее меню над башней: Продать (50%) и Улучшить",
        "Класс Camera и тряска экрана при взрывах и ударах по базе",
    ]),
    ("Обновление 12 — Тактика, ловушки и дрон", [
        "Синергия башен: замороженный враг получает +50% физ. урона",
        "Огнемёт по отравленному врагу вызывает взрыв яда по площади",
        "Взрывоопасные красные бочки на карте — стреляй для цепных взрывов",
        "Ловушки Шипы и Мины (магазин Димы) ставятся прямо на дорогу",
        "Дрон-помощник (магазин Андрея) летает вокруг и бьёт лазером",
        "Bloom-свечение выстрелов и взрывов + красная виньетка при уроне",
    ]),
    ("Обновление 11 — Гильзы, кровь и мутаторы", [
        "Гильзы вылетают из оружия и башен, отскакивают и лежат на земле",
        "Следы крови/масла на поле боя в местах попаданий",
        "Мутаторы волн (шанс 20%): Туман, Берсерки, Золотая лихорадка",
        "Красивое предупреждение с названием мутатора перед волной",
        "Ползунок громкости в настройках, скины переносятся между версиями",
    ]),
    ("Обновление 10 — Эпичные боссы и движ", [
        "Огромная полоса HP босса с именем вверху экрана",
        "Лут падает на карту: монеты и аптечки, с магнетизмом к Матвею",
        "Абилки боссов: призыв помощников, ускорение, оглушающий удар",
        "У Рената — водяной круг с мегалодоном, отбивающим пули",
        "Валера с 10 волны оглушает битой игрока и башни",
    ]),
    ("Обновление 9 — Отмена установки", [
        "Отмена ещё ДО постановки: ✕ сверху или ESC, пока башня-призрак ходит за курсором",
        "Кнопка ✕ над только что поставленной башней — отменяет установку",
        "Полный возврат денег при отмене (обычная продажа по-прежнему 60%)",
    ]),
    ("Обновление 8 — Звук и оживление", [
        "Башни из двух частей: неподвижная база + плавно (lerp) вращающаяся пушка",
        "Враги шагают с покачиванием (squash & stretch), HP-бар зелёный→красный",
        "Градиентные трассеры пуль, дымный шлейф и взрыв базуки, вспышки у дула",
        "Мягкие приятные звуки выстрела и попадания вместо резкого шума",
        "Этот экран ОБНОВЛЕНИЯ с историей патчей",
    ]),
    ("Обновление 7 — Сочный интерфейс", [
        "Магазины-модалки с затемнением фона и крестиком ✕",
        "Прокачанное меню: размытый фон, заголовок-логотип, кнопки со свечением",
        "Иконки оружия на кнопках магазина, цифры урона и цены",
        "Вылетающие цифры урона и тряска экрана при мощных выстрелах",
    ]),
    ("Обновление 6 — Графика и спрайты", [
        "Тайловый фон-трава и текстурная тропинка, тени под объектами",
        "Частицы: вспышки выстрелов и искры попаданий",
        "Стильная зона поражения башен с пульсирующим кольцом",
        "Поддержка PNG-спрайтов игрока, врагов, продавцов и башен",
    ]),
    ("Обновление 5 — Умные башни", [
        "Самонаводящиеся пули у башен (всегда попадают), без лазеров",
        "Приоритет целей: Первый / Последний / Сильнейший / Слабейший",
        "Магазин и прокачка доступны прямо во время волны",
        "Экран Настроек: звук вкл/выкл и громкость",
    ]),
    ("Обновление 4 — Баланс оружия", [
        "Новый порядок и роли оружия, миниган и базука",
        "Очереди по 3 пули у пистолета-пулемёта, взрыв у базуки",
        "Прокачка башен до 3 уровня, продажа, лимит установки",
        "Ядовитая башня с уроном со временем",
    ]),
    ("Обновление 3 — Скины и монеты", [
        "Фото-скины Матвея с авто-обрезкой фона лица",
        "Редактор скинов, покупка за монеты (+5 за победу)",
        "Профиль с синхронизацией между версиями игры",
        "Кракуля — секретный босс после Дивана Шира",
    ]),
    ("Обновление 2 — Меню и сохранения", [
        "Главное меню, сохранение и автосохранение каждые 3 минуты",
        "Новая игра / загрузка, случайные карты",
        "Хардкор-режим (только пистолет)",
        "Полноэкранный режим и управление WASD",
    ]),
    ("Обновление 1 — Базовая игра", [
        "Tower Defense: Матвей против боссов Рената, Валеры и Дивана Шира",
        "Продавцы Андрей Кол (оружие) и Дима Трубаз (турели)",
        "Покупка оружия и установка башен между волнами",
    ]),
]

def patch_back_rect():
    return pygame.Rect(WIDTH//2-110, HEIGHT-52, 220, 40)

def draw_patchnotes():
    draw_menu_bg(175)
    draw_title("ОБНОВЛЕНИЯ", 26, YELLOW)
    top=116; bottom=HEIGHT-66; x=int(WIDTH/2-360)
    area=pygame.Rect(x-18, top-8, 756, bottom-top+16)
    box=pygame.Surface((area.width,area.height),pygame.SRCALPHA)
    box.fill((18,18,30,175)); screen.blit(box,(area.x,area.y))
    clip=pygame.Rect(x-10, top, 740, bottom-top)
    prev=screen.get_clip(); screen.set_clip(clip)
    y=top - G.get("patch_scroll",0)
    for title,items in PATCH_NOTES:
        screen.blit(font_m.render(title,True,YELLOW),(x,y)); y+=36
        for it in items:
            screen.blit(font_s.render("•  "+it,True,WHITE),(x+18,y)); y+=24
        y+=22
    content_h=(y+G.get("patch_scroll",0))-top
    screen.set_clip(prev)
    G["_patch_max"]=max(0, content_h-(bottom-top))
    pygame.draw.rect(screen,(120,128,150),area,2,border_radius=12)
    hint=font_s.render("Колесо мыши / ↑↓ — листать",True,LIGHT)
    screen.blit(hint,(WIDTH/2-hint.get_width()/2, top-2))
    draw_button(patch_back_rect(),"НАЗАД",(150,190,230),font=font_m)


# ----- Настройки -----
def settings_buttons():
    cx=WIDTH/2
    return {"sound":pygame.Rect(cx-150,225,300,52),
            "slider":pygame.Rect(cx-150,332,300,20),
            "voldown":pygame.Rect(cx-150,362,140,46),
            "volup":pygame.Rect(cx+10,362,140,46),
            "test":pygame.Rect(cx-150,422,300,46),
            "back":pygame.Rect(cx-150,480,300,46)}

def draw_settings():
    draw_menu_bg()
    draw_title("НАСТРОЙКИ",90,YELLOW)
    b=settings_buttons()
    s_on=PROFILE.get("sound",True)
    draw_button(b["sound"], f"Звук: {'ВКЛ' if s_on else 'ВЫКЛ'}",(130,200,130) if s_on else (200,120,120),font=font_m)
    vol=PROFILE.get("volume",0.7)
    vt=font_m.render(f"Громкость: {int(round(vol*100))}%",True,WHITE)
    screen.blit(vt,(WIDTH/2-vt.get_width()/2,298))
    sl=b["slider"]
    pygame.draw.rect(screen,(40,40,56),sl,border_radius=10)
    fill=pygame.Rect(sl.x,sl.y,int(sl.width*vol),sl.height)
    pygame.draw.rect(screen,(110,200,255),fill,border_radius=10)
    pygame.draw.rect(screen,(120,128,150),sl,2,border_radius=10)
    knob=int(sl.x+sl.width*vol)
    pygame.draw.circle(screen,WHITE,(knob,sl.centery),10)
    pygame.draw.circle(screen,(60,130,230),(knob,sl.centery),10,2)
    draw_button(b["voldown"],"–",(150,190,230),font=font_l)
    draw_button(b["volup"],"+",(150,190,230),font=font_l)
    draw_button(b["test"],"проверить звук",(180,200,150),font=font_m)
    draw_button(b["back"],"НАЗАД",(150,190,230),font=font_m)

def handle_settings_click(pos):
    b=settings_buttons()
    if b["sound"].collidepoint(pos):
        PROFILE["sound"]=not PROFILE.get("sound",True); save_profile()
    elif b["slider"].collidepoint(pos):
        frac=(pos[0]-b["slider"].x)/max(1,b["slider"].width)
        PROFILE["volume"]=max(0.0,min(1.0,round(frac,2))); save_profile(); play(SND_HIT)
    elif b["voldown"].collidepoint(pos):
        PROFILE["volume"]=max(0.0,round(PROFILE.get("volume",0.7)-0.1,2)); save_profile(); play(SND_HIT)
    elif b["volup"].collidepoint(pos):
        PROFILE["volume"]=min(1.0,round(PROFILE.get("volume",0.7)+0.1,2)); save_profile(); play(SND_HIT)
    elif b["test"].collidepoint(pos):
        play(SND_HIT)
    elif b["back"].collidepoint(pos):
        save_profile(); G["state"]="menu"


# ----- Редактор скинов -----
def skin_buttons():
    cx=WIDTH/2
    return {"prev": pygame.Rect(cx-280,250,70,70), "next": pygame.Rect(cx+210,250,70,70),
            "action": pygame.Rect(cx-150,470,300,50), "back": pygame.Rect(cx-150,535,300,46)}

def draw_skins():
    draw_menu_bg()
    draw_title("РЕДАКТОР СКИНОВ",80,YELLOW)
    coins=font_m.render(f"Монеты: {PROFILE['coins']}",True,YELLOW)
    screen.blit(coins,(WIDTH/2-coins.get_width()/2,150))
    view=G["skin_view"]
    draw_hero_skin(screen, WIDTH/2, 290, 50, idx=view)
    name=font_m.render(SKIN_NAMES[view],True,WHITE)
    screen.blit(name,(WIDTH/2-name.get_width()/2, 358))
    unlocked = view in PROFILE["unlocked_skins"]
    selected = (view == PROFILE["skin_idx"])
    if view!=0 and SKIN_HERO[view] is None:
        warn=font_s.render(f"Файл {SKIN_FILES[view]} не найден (положи рядом с игрой)",True,(230,180,180))
        screen.blit(warn,(WIDTH/2-warn.get_width()/2, 392))
    b=skin_buttons()
    draw_button(b["prev"], "<", (150,190,230), font=font_l)
    draw_button(b["next"], ">", (150,190,230), font=font_l)
    if selected:
        draw_button(b["action"], "ВЫБРАНО", (130,200,130), font=font_m)
    elif unlocked:
        draw_button(b["action"], "ВЫБРАТЬ", (150,190,230), font=font_m)
    else:
        draw_button(b["action"], f"КУПИТЬ ЗА {SKIN_COST} МОНЕТ", (210,180,120), font=font_m)
    draw_button(b["back"], "НАЗАД", (150,190,230), font=font_m)

def handle_skin_click(pos):
    b=skin_buttons(); view=G["skin_view"]
    if b["prev"].collidepoint(pos):
        G["skin_view"]=(view-1)%NUM_SKINS
    elif b["next"].collidepoint(pos):
        G["skin_view"]=(view+1)%NUM_SKINS
    elif b["action"].collidepoint(pos):
        if view in PROFILE["unlocked_skins"]:
            PROFILE["skin_idx"]=view; save_profile(); G["message"]="Скин выбран"
        else:
            if PROFILE["coins"]>=SKIN_COST:
                PROFILE["coins"]-=SKIN_COST
                PROFILE["unlocked_skins"]=sorted(set(PROFILE["unlocked_skins"]+[view]))
                PROFILE["skin_idx"]=view; save_profile()
            else:
                G["message"]="Не хватает монет! Побеждай, чтобы заработать."
    elif b["back"].collidepoint(pos):
        save_profile(); G["state"]="menu"


def handle_menu_click(pos):
    global G
    if G["state"]=="menu":
        for rect,key in main_menu_buttons():
            if rect.collidepoint(pos):
                if key=="continue": G["state"]=G.get("resume_state","build")
                elif key=="play": G["state"]="play_menu"
                elif key=="hardcore":
                    G=new_game(hardcore=True); G["state"]="build"; G["started"]=True
                    G["message"]="ХАРДКОР: только пистолет!"; reset_autosave()
                elif key=="skins":
                    G["skin_view"]=PROFILE["skin_idx"]; G["state"]="skins"
                elif key=="settings": G["state"]="settings"
                elif key=="patch": G["patch_scroll"]=0; G["state"]="patch"
                elif key=="part2": G["state"]="part2"
                elif key=="exit": return "quit"
    elif G["state"]=="play_menu":
        for rect,key in play_menu_buttons():
            if rect.collidepoint(pos):
                if key=="new":
                    G=new_game(); G["state"]="build"; G["started"]=True; reset_autosave()
                elif key=="load":
                    loaded=load_game()
                    if loaded: G=loaded; reset_autosave()
                elif key=="back": G["state"]="menu"
    return None

def reset_autosave():
    global autosave_timer
    autosave_timer=0.0


def shop_panel_rect():
    """Компактное модальное окно магазина (~56% ширины экрана), по центру."""
    pw, ph = 620, 470
    return pygame.Rect(WIDTH//2-pw//2, HEIGHT//2-ph//2, pw, ph)

def shop_close_rect():
    p=shop_panel_rect()
    return pygame.Rect(p.right-40, p.y+9, 28, 28)

def weapon_shop_buttons():
    p=shop_panel_rect(); rects=[]; x=p.x+30; y=p.y+52; bw=p.width-60
    for name in WEAPON_ORDER+["Дрон-помощник"]:
        rects.append((pygame.Rect(x,y,bw,46), name)); y+=52
    return rects

def turret_shop_buttons():
    p=shop_panel_rect(); rects=[]; x=p.x+30; y=p.y+52; bw=p.width-60
    for name in TURRET_ORDER+TRAP_ORDER:
        rects.append((pygame.Rect(x,y,bw,46), name)); y+=52
    return rects


def draw_map():
    # запечённый тайловый фон (трава) + текстурная тропинка
    if BG_CACHE is not None:
        screen.blit(BG_CACHE, (0,0))
    else:
        screen.fill(GRASS)
    bx,by = PATH[-1]
    sh=pygame.Surface((70,22),pygame.SRCALPHA); pygame.draw.ellipse(sh,(0,0,0,90),sh.get_rect())
    screen.blit(sh,(bx-35,by-6))
    base=pygame.Rect(bx-30, by-60, 60, 60)
    prev=screen.get_clip(); screen.set_clip(base)
    draw_vgradient(base,(200,70,70),(150,30,30))
    screen.set_clip(prev)
    pygame.draw.rect(screen, (90,20,20), base, 3, border_radius=6)
    screen.blit(font_s.render("БАЗА",True,WHITE),(bx-22,by-40))

def draw_seller(pos, name, color, can_interact, image=None):
    x,y=pos
    sh=pygame.Surface((48,18),pygame.SRCALPHA); pygame.draw.ellipse(sh,(0,0,0,110),sh.get_rect())
    screen.blit(sh,(x-24,y+14))
    if image is not None:
        screen.blit(image, image.get_rect(center=(int(x),int(y))))
    else:
        # процедурный NPC-продавец: торговец под навесом за прилавком
        light=tuple(min(255,int(c*1.3)) for c in color)
        dark=tuple(int(c*0.55) for c in color)
        pygame.draw.rect(screen,(70,60,55),(x-9,y-8,18,18),border_radius=4)      # туловище
        pygame.draw.circle(screen,(225,195,165),(int(x),int(y-12)),7)            # голова
        pygame.draw.circle(screen,(30,25,22),(int(x),int(y-12)),7,1)
        counter=pygame.Rect(x-22,y+6,44,12)                                      # прилавок
        prev=screen.get_clip(); screen.set_clip(counter)
        draw_vgradient(counter, light, dark)
        screen.set_clip(prev)
        pygame.draw.rect(screen,(25,20,18),counter,2,border_radius=3)
        for i in range(4):                                                       # полосатый навес
            cc=light if i%2==0 else WHITE
            pygame.draw.rect(screen,cc,(x-22+i*11,y-26,11,9))
        pygame.draw.rect(screen,(25,20,18),(x-22,y-26,44,9),1)
        pygame.draw.line(screen,(60,50,45),(x-20,y-17),(x-20,y+6),3)
        pygame.draw.line(screen,(60,50,45),(x+20,y-17),(x+20,y+6),3)
    t=font_s.render(name,True,WHITE)
    screen.blit(t,(x-t.get_width()/2, y-44))
    if can_interact:
        p=font_m.render("Нажми E",True,YELLOW)
        screen.blit(p,(x-p.get_width()/2, y+24))

def draw_hud():
    draw_vgradient(pygame.Rect(0,0,WIDTH,46),(40,40,60),(20,20,30))
    pygame.draw.line(screen,(95,120,180),(0,46),(WIDTH,46),2)
    h=G["hero"]
    chips=[(f"Деньги {G['money']}",YELLOW),((f"Волна {G['wave']}/30" if not G.get("endless") else f"Волна {G['wave']}"),LIGHT),
           (f"Жизни {G['lives']}",GREEN),(f"Башни {len(G['turrets'])}",LIGHT),
           (f"{h.weapon}",CYAN),(f"Карта {G['map']+1}",LIGHT),(f"Монеты {PROFILE['coins']}",YELLOW)]
    if G["hardcore"]: chips.append(("ХАРДКОР",(235,140,140)))
    if G.get("mutator"):
        _m=next((mm for mm in MUTATORS if mm["key"]==G["mutator"]), None)
        if _m: chips.append(("МУТАТОР: "+_m["name"], _m["color"]))
    x=12
    for text,color in chips:
        x+=draw_chip(x,9,text,color)+8
    hp_frac=max(0,h.hp)/h.max_hp
    bar=pygame.Rect(WIDTH-205,12,185,18)
    pygame.draw.rect(screen,(50,16,16),bar,border_radius=9)
    if hp_frac>0:
        fill=pygame.Rect(WIDTH-205,12,int(185*hp_frac),18)
        top=(90,220,110) if hp_frac>0.5 else (240,200,70) if hp_frac>0.25 else (235,80,70)
        bot=(40,150,60) if hp_frac>0.5 else (200,150,40) if hp_frac>0.25 else (170,30,30)
        prev=screen.get_clip(); screen.set_clip(fill)
        draw_vgradient(bar,top,bot)
        screen.set_clip(prev)
    pygame.draw.rect(screen,(20,20,30),bar,2,border_radius=9)
    screen.blit(font_s.render(f"HP {int(max(0,h.hp))}",True,WHITE),(WIDTH-145,11))

def draw_shop():
    overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); overlay.fill((0,0,0,180)); screen.blit(overlay,(0,0))
    panel=shop_panel_rect()
    accent = ORANGE if G["state"]=="shop_w" else CYAN
    draw_panel(panel, accent=accent)
    h=G["hero"]
    title = "Андрей Кол — Оружие" if G["state"]=="shop_w" else "Дима Трубаз — Турели"
    screen.blit(font_m.render(title,True,WHITE),(panel.x+16,panel.y+5))
    screen.blit(font_s.render(f"Деньги: {G['money']}",True,YELLOW),(panel.right-180,panel.y+9))
    draw_close_button(shop_close_rect())
    if G["state"]=="shop_w":
        for rect,name in weapon_shop_buttons():
            if name=="Дрон-помощник":
                has=G.get("drone") is not None
                base=(150,200,150) if has else (150,210,230)
                r=draw_fancy_button(rect,"Дрон-помощник",base,selected=has,font=font_m)
                if has:
                    screen.blit(font_s.render("куплен",True,(20,60,20)),(r.right-95, r.centery-9))
                else:
                    draw_stat_icon(screen,"coin", r.right-90, r.centery)
                    screen.blit(font_s.render(str(DRONE_COST),True,(20,20,28)),(r.right-80, r.centery-9))
                continue
            w=WEAPONS[name]; owned=name in G["owned_weapons"]
            locked=G["hardcore"] and name!="Пистолет"
            base=(95,95,108) if locked else (150,200,150) if owned else (235,205,140)
            r=draw_fancy_button(rect,name,base,selected=(h.weapon==name),font=font_m,icon_weapon=name)
            draw_stat_icon(screen,"dmg", r.right-150, r.centery)
            screen.blit(font_s.render(str(w["dmg"]),True,(20,20,28)),(r.right-140, r.centery-9))
            if locked:
                screen.blit(font_s.render("хардкор",True,(30,30,38)),(r.right-95, r.centery-9))
            elif owned:
                screen.blit(font_s.render("куплено",True,(20,60,20)),(r.right-95, r.centery-9))
            else:
                draw_stat_icon(screen,"coin", r.right-90, r.centery)
                screen.blit(font_s.render(str(w["cost"]),True,(20,20,28)),(r.right-80, r.centery-9))
    else:
        for rect,name in turret_shop_buttons():
            if name in TRAPS:
                tp=TRAPS[name]
                r=draw_fancy_button(rect,f"{name} • ловушка",(210,180,140),font=font_m)
                draw_stat_icon(screen,"dmg", r.right-150, r.centery)
                screen.blit(font_s.render(str(tp["dmg"]),True,(20,20,28)),(r.right-140, r.centery-9))
                draw_stat_icon(screen,"coin", r.right-90, r.centery)
                screen.blit(font_s.render(str(tp["cost"]),True,(20,20,28)),(r.right-80, r.centery-9))
                continue
            t=TURRETS[name]
            tag=""
            if t["slow"]>0: tag="мороз"
            elif t["poison"]>0: tag="яд"
            elif t["aoe"]>0: tag="взрыв"
            label=name if not tag else f"{name} • {tag}"
            r=draw_fancy_button(rect,label,(150,190,230),font=font_m)
            draw_stat_icon(screen,"dmg", r.right-150, r.centery)
            screen.blit(font_s.render(str(t["dmg"]),True,(20,20,28)),(r.right-140, r.centery-9))
            draw_stat_icon(screen,"coin", r.right-90, r.centery)
            screen.blit(font_s.render(str(t["cost"]),True,(20,20,28)),(r.right-80, r.centery-9))
    screen.blit(font_s.render("E / ESC или ✕ — закрыть",True,WHITE),(panel.x+18,panel.bottom-26))

def handle_shop_click(pos):
    h=G["hero"]
    if shop_close_rect().collidepoint(pos):
        G["state"]=G.get("shop_return","build"); return
    if G["state"]=="shop_w":
        for rect,name in weapon_shop_buttons():
            if rect.collidepoint(pos):
                if name=="Дрон-помощник":
                    if G.get("drone") is not None:
                        G["message"]="Дрон уже куплен!"
                    elif G["money"]>=DRONE_COST:
                        G["money"]-=DRONE_COST; G["drone"]=Drone(); play_sound("buy")
                        G["message"]="Дрон-помощник активирован!"
                    else:
                        G["message"]="Мало денег на дрона!"
                    return
                if G["hardcore"] and name!="Пистолет":
                    G["message"]="Хардкор: разрешён только пистолет!"; return
                if name in G["owned_weapons"]:
                    h.weapon=name
                elif G["money"]>=WEAPONS[name]["cost"]:
                    G["money"]-=WEAPONS[name]["cost"]; G["owned_weapons"].add(name); h.weapon=name; play_sound("buy")
                else:
                    G["message"]="Мало денег у Андрея Кола!"
                return
    elif G["state"]=="shop_t":
        for rect,name in turret_shop_buttons():
            if rect.collidepoint(pos):
                if name in TRAPS:
                    if G["money"]>=TRAPS[name]["cost"]:
                        G["selected_trap"]=name; G["selected_turret"]=None; G["sel_turret_obj"]=None
                        G["state"]=G.get("shop_return","build")
                        G["message"]="Поставь ловушку НА дорогу: "+name+"  •  ESC — отмена"
                    else:
                        G["message"]="Мало денег у Димы Трубаза!"
                    return
                if count_kind(name)>=type_limit(name):
                    G["message"]=f"Лимит {name}: максимум {type_limit(name)} шт.!"; return
                if G["money"]>=TURRETS[name]["cost"]:
                    G["selected_turret"]=name; G["sel_turret_obj"]=None
                    G["state"]=G.get("shop_return","build"); G["message"]="Кликни по карте, чтобы поставить: "+name+"  •  ✕ сверху или ESC — отмена"
                else:
                    G["message"]="Мало денег у Димы Трубаза!"
                return

def try_place_turret(pos):
    if not G["selected_turret"]: return
    x,y=pos
    if y<48: return
    kind=G["selected_turret"]; cost=TURRETS[kind]["cost"]
    if count_kind(kind)>=type_limit(kind):
        G["message"]=f"Лимит {kind}: максимум {type_limit(kind)} шт.!"; G["selected_turret"]=None; return
    if G["money"]<cost:
        G["message"]="Недостаточно денег!"; return
    if near_path(x,y):
        G["message"]="Нельзя ставить на дороге!"; return
    if dist(x,y,*ANDREY_POS)<34 or dist(x,y,*DIMA_POS)<34:
        G["message"]="Тут стоит продавец!"; return
    for t in G["turrets"]:
        if dist(x,y,t.x,t.y)<36:
            G["message"]="Слишком близко к турели!"; return
    nt=Turret(x,y,kind)
    G["turrets"].append(nt)
    G["money"]-=cost; G["message"]="Поставлено: "+kind+"  •  ✕ над башней — отменить и вернуть деньги"; play_sound("buy")
    G["last_placed"]=nt


def try_place_trap(pos):
    if not G.get("selected_trap"): return
    x,y=pos
    if y<48: return
    kind=G["selected_trap"]; cost=TRAPS[kind]["cost"]
    if G["money"]<cost:
        G["message"]="Недостаточно денег!"; return
    if not near_path(x,y):
        G["message"]="Ловушку нужно ставить НА дорогу!"; return
    G["traps"].append(Trap(x,y,kind))
    G["money"]-=cost; G["selected_trap"]=None
    G["message"]="Ловушка установлена: "+kind; play_sound("buy")


def last_cancel_rect():
    """Кнопка ✕ над только что поставленной башней — отменить установку с полным возвратом денег."""
    t=G.get("last_placed")
    if not t or t not in G["turrets"]:
        return None
    base_r=14+t.level*3
    return pygame.Rect(int(t.x+base_r-2), int(t.y-base_r-30), 26, 26)


def placement_cancel_rect():
    """Кнопка отмены ВЫБОРА башни (пока башня-призрак ещё ходит за курсором, до клика по карте)."""
    return pygame.Rect(WIDTH//2-160, 80, 320, 36)


def upgrade_panel_rects():
    p=pygame.Rect(WIDTH-310, HEIGHT-208, 290, 180)
    return {"panel":p,
            "prio":pygame.Rect(p.x+15,p.y+56,260,28),
            "up":pygame.Rect(p.x+15,p.y+90,260,32),
            "sell":pygame.Rect(p.x+15,p.y+126,260,26)}

def draw_upgrade_panel():
    t=G["sel_turret_obj"]
    if not t: return
    b=upgrade_panel_rects(); p=b["panel"]
    draw_panel(p, accent=t.color)
    screen.blit(font_m.render(f"{t.kind}  ур.{t.level}",True,WHITE),(p.x+14,p.y+5))
    screen.blit(font_s.render(f"Урон {int(t.dmg)} • Радиус {int(t.range)}",True,WHITE),(p.x+15,p.y+38))
    draw_button(b["prio"],f"Цель: {t.priority}",(150,200,210))
    if t.level<3:
        draw_button(b["up"],f"Улучшить — {t.upgrade_cost()} монет",(210,180,120))
    else:
        draw_button(b["up"],"МАКС. УРОВЕНЬ",(90,90,100))
    draw_button(b["sell"],f"Продать (+{t.sell_value()})",(210,140,140))

def handle_build_click(pos):
    # ✕ над только что поставленной башней — отмена установки с полным возвратом
    cr=last_cancel_rect()
    if cr and cr.collidepoint(pos):
        t=G["last_placed"]
        G["money"]+=TURRETS[t.kind]["cost"]
        if t in G["turrets"]: G["turrets"].remove(t)
        if G.get("sel_turret_obj") is t: G["sel_turret_obj"]=None
        G["last_placed"]=None
        G["message"]="Установка отменена — деньги возвращены"
        return
    b=upgrade_panel_rects()
    if G["sel_turret_obj"]:
        t=G["sel_turret_obj"]
        if b["prio"].collidepoint(pos):
            i=PRIORITIES.index(t.priority) if t.priority in PRIORITIES else 0
            t.priority=PRIORITIES[(i+1)%len(PRIORITIES)]; return
        if b["up"].collidepoint(pos):
            if t.level>=3:
                G["message"]="Максимальный уровень"; return
            c=t.upgrade_cost()
            if G["money"]>=c:
                G["money"]-=c; t.invested+=c; t.level+=1; t.apply_level()
                if G.get("last_placed") is t: G["last_placed"]=None
            else:
                G["message"]="Мало денег для улучшения!"
            return
        if b["sell"].collidepoint(pos):
            G["money"]+=t.sell_value()
            if t in G["turrets"]: G["turrets"].remove(t)
            if G.get("last_placed") is t: G["last_placed"]=None
            G["sel_turret_obj"]=None; return
        if b["panel"].collidepoint(pos):
            return
    for t in G["turrets"]:
        if dist(pos[0],pos[1],t.x,t.y)<24:
            G["sel_turret_obj"]=t; return
    G["sel_turret_obj"]=None


def update_boss_abilities(dt):
    """Абилки боссов: призыв помощников, ускорение, оглушающий удар битой."""
    new_minions=[]
    for e in G["enemies"]:
        if not (e.alive and getattr(e,"is_boss",False)):
            continue
        e.ability_timer-=dt
        if e.boss_kind=="stun":
            if e.ability_timer<=0:
                e.ability_timer=6.0; e.bat_swing=0.45
                G["hero"].stun=1.3; G["turret_stun"]=1.3
                G["effects"].append(Effect(e.x,e.y,150,(255,220,80)))
                add_shake(11); play_sound("boom")
                G["message"]="Валера оглушил всех битой!"
            elif e.bat_swing>0:
                e.bat_swing-=dt
        elif e.boss_kind=="summon":
            if e.ability_timer<=0:
                e.ability_timer=15.0
                for _ in range(3):
                    m=Enemy(100, 2.4, WHITE, 11, 5)
                    m.x=e.x+random.uniform(-26,26); m.y=e.y+random.uniform(-26,26); m.idx=e.idx
                    new_minions.append(m)
                G["effects"].append(Effect(e.x,e.y,70,PURPLE))
                G["message"]=f"{e.name} призвал помощников!"
        elif e.boss_kind=="shark":
            if e.ability_timer<=0:
                e.ability_timer=5.0; e.speed_boost=1.4
    if new_minions:
        G["enemies"].extend(new_minions)


def update_wave(dt, keys):
    h=G["hero"]; h.update(dt, keys)
    if pygame.mouse.get_pressed()[0] and not G["selected_turret"] and h.stun<=0:
        h.shoot()

    G["turret_stun"]=max(0.0, G.get("turret_stun",0)-dt)
    update_boss_abilities(dt)

    G["spawn_timer"]-=dt
    if G["spawn_queue"] and G["spawn_timer"]<=0:
        G["enemies"].append(G["spawn_queue"].pop(0)); G["spawn_timer"]=0.55

    for t in G["turrets"]:
        t.update(dt, G["enemies"], G["bullets"])

    for e in G["enemies"]:
        e.update(dt)
        if e.reached:
            if getattr(e,"is_boss",False):
                # урон базе зависит от остатка HP босса: чем меньше HP — тем меньше снимется
                frac=max(0.0, min(1.0, e.hp/e.max_hp))
                dmg=max(1, math.ceil(frac*20))
                G["lives"]-=dmg
                G["message"]=f"{e.name} прорвался к базе! −{dmg} жизней"
            else:
                G["lives"]-=1
        if e.alive and h.hurt_cd<=0 and dist(e.x,e.y,h.x,h.y)<e.radius+h.radius:
            h.hp-=8; h.hurt_cd=0.5; play(SND_HURT); add_hurt_flash(); add_shake(5)

    for b in G["bullets"]:
        b.update(dt)
        # мегалодон Рената отбивает пули, попавшие в него
        deflected=False
        for e in G["enemies"]:
            if e.alive and getattr(e,"boss_kind",None)=="shark" and dist(b.x,b.y,e.meg_x,e.meg_y)<24:
                nx,ny=b.x-e.meg_x,b.y-e.meg_y; dd=math.hypot(nx,ny) or 1
                sp=math.hypot(b.vx,b.vy) or b.speed
                b.vx=nx/dd*sp; b.vy=ny/dd*sp; b.target=None
                spawn_hit(G["particles"], b.x, b.y, (120,200,255)); play_hit()
                deflected=True; break
        if deflected:
            continue
        hit_barrel=False
        for bar in G["barrels"]:
            if bar.alive and dist(b.x,b.y,bar.x,bar.y)<bar.radius+b.radius:
                b.alive=False; bar.explode(); hit_barrel=True; break
        if hit_barrel:
            continue
        for e in G["enemies"]:
            if e.alive and dist(b.x,b.y,e.x,e.y)<e.radius+b.radius:
                dmg=b.dmg; bonus=False
                if getattr(b,"dtype","phys")=="phys" and e.slow_timer>0:
                    dmg*=1.5; bonus=True                       # СИНЕРГИЯ: мороз + физ. урон +50%
                fire_combo=(getattr(b,"dtype","phys")=="fire" and e.poison_timer>0)  # СИНЕРГИЯ: огонь + яд
                e.hit(dmg, b.slow, b.poison)
                play_hit()
                spawn_hit(G["particles"], b.x, b.y, b.color)
                if random.random()<0.4:
                    spawn_splat(e.x, e.y+e.radius*0.4)   # след крови/масла на земле
                G["floats"].append(FloatText(e.x, e.y-e.radius, dmg, (140,220,255) if bonus else b.color, crit=b.dmg>=80 or bonus))
                if fire_combo:
                    G["effects"].append(Effect(e.x,e.y,72,POISONC)); add_shake(5); play_sound("boom")
                    for _ in range(10):
                        a=random.uniform(0,math.tau); sp=random.uniform(2,5)
                        G["particles"].append(Particle(e.x,e.y,math.cos(a)*sp,math.sin(a)*sp,
                                              random.uniform(0.25,0.5),(180,240,120),random.randint(3,6),grav=0.03))
                    for e2 in G["enemies"]:
                        if e2.alive and e2 is not e and dist(e.x,e.y,e2.x,e2.y)<72:
                            e2.hit(b.dmg*1.5, 0, 0)
                    G["floats"].append(FloatText(e.x, e.y-e.radius-14, "ВЗРЫВ ЯДА!", POISONC))
                if b.aoe>0:
                    play_sound("boom")
                    add_shake(6)
                    G["effects"].append(Effect(b.x,b.y,b.aoe,ORANGE))
                    # огненно-дымное облако частиц при взрыве
                    for _ in range(14):
                        a=random.uniform(0,math.tau); sp=random.uniform(2,6)
                        G["particles"].append(Particle(b.x,b.y,math.cos(a)*sp,math.sin(a)*sp,
                                              random.uniform(0.3,0.6),(255,150,50),random.randint(3,6),grav=0.04))
                    for _ in range(8):
                        a=random.uniform(0,math.tau); sp=random.uniform(0.5,2.0)
                        G["particles"].append(Particle(b.x,b.y,math.cos(a)*sp,math.sin(a)*sp,
                                              random.uniform(0.5,0.9),(120,118,128),random.randint(5,9),grav=-0.02))
                    for e2 in G["enemies"]:
                        if e2.alive and e2 is not e and dist(b.x,b.y,e2.x,e2.y)<b.aoe:
                            e2.hit(b.dmg*0.6, b.slow, b.poison)
                b.alive=False
                break

    if not G["krakulya_done"]:
        for e in list(G["enemies"]):
            if (not e.alive) and (not e.reached) and e.name=="Диван Шир":
                kr=Enemy(max(1,e.max_hp//4), 2.0, WHITE, 30, 800, "Кракуля", is_boss=True)
                kr.boss_kind="summon"; kr.ability_timer=15.0
                kr.x, kr.y, kr.idx = e.x, e.y, e.idx
                G["enemies"].append(kr); G["krakulya_done"]=True
                G["message"]="Кракуля появился! Добей его!"
                break

    for e in G["enemies"]:
        if not e.alive and not e.reached:
            spawn_loot(e)

    for pk in G["pickups"]:
        pk.update(dt, h)
    G["pickups"]=[pk for pk in G["pickups"] if pk.alive]

    for tr in G["traps"]:
        tr.update(dt)
    G["traps"]=[tr for tr in G["traps"] if tr.alive]
    if G.get("drone"):
        G["drone"].update(dt, h, G["enemies"])
    for ls in G["lasers"]:
        ls[4]-=dt
    G["lasers"]=[ls for ls in G["lasers"] if ls[4]>0]

    G["enemies"]=[e for e in G["enemies"] if e.alive]
    G["bullets"]=[b for b in G["bullets"] if b.alive]
    G["effects"]=[ef for ef in G["effects"] if ef.update(dt)]
    G["particles"]=[p for p in G["particles"] if p.update(dt)]
    G["floats"]=[ft for ft in G["floats"] if ft.update(dt)]
    G["shells"]=[sh for sh in G["shells"] if sh.update(dt)]
    G["splats"]=[sp for sp in G["splats"] if sp.update(dt)]

    if h.hp<=0 or G["lives"]<=0:
        G["state"]="gameover"; return

    if not G["spawn_queue"] and not G["enemies"]:
        if not G.get("endless") and G["wave"]>=30:
            G["state"]="win"; PROFILE["coins"]+=5; save_profile()
        else:
            G["wave"]+=1; G["money"]+=120
            h.hp=min(h.max_hp, h.hp+30)
            G["state"]="build"; G["bullets"]=[]; G["effects"]=[]; G["last_placed"]=None
            G["mutator"]=None; G["mut_range"]=1.0; G["mut_gold"]=1; G["barrels"]=[]
            save_game(silent=True)
            G["message"]="Подойди к продавцам (E) или жми Пробел"


def draw_boss_bar():
    """Эпичная полоса здоровья босса вверху по центру с именем."""
    bosses=[e for e in G["enemies"] if getattr(e,"is_boss",False) and e.alive]
    if not bosses:
        return
    boss=max(bosses, key=lambda e:e.max_hp)
    name=(boss.name or f"БОСС ВОЛНЫ {G['wave']}").upper()
    frac=max(0.0, min(1.0, boss.hp/boss.max_hp))
    bw=int(WIDTH*0.6); bx=WIDTH//2-bw//2; by=98; bh=22
    nm=font_l.render(name, True, (255,90,90))
    out=font_l.render(name, True, (25,10,14))
    nx=WIDTH//2-nm.get_width()//2
    for dx,dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,2)]:
        screen.blit(out,(nx+dx, 50+dy))
    screen.blit(nm,(nx, 50))
    sh=pygame.Surface((bw+10,bh+10),pygame.SRCALPHA); sh.fill((0,0,0,150))
    screen.blit(sh,(bx-5,by-1))
    pygame.draw.rect(screen,(30,16,20),(bx,by,bw,bh),border_radius=9)
    if frac>0:
        fill=pygame.Rect(bx,by,int(bw*frac),bh)
        prev=screen.get_clip(); screen.set_clip(fill)
        draw_vgradient(pygame.Rect(bx,by,bw,bh),(255,120,90),(150,20,30))
        screen.set_clip(prev)
    for i in range(1,10):
        xx=bx+int(bw*i/10)
        pygame.draw.line(screen,(20,12,16),(xx,by),(xx,by+bh),1)
    pygame.draw.rect(screen,(255,205,205),(bx,by,bw,bh),3,border_radius=9)
    hp=font_s.render(f"{int(max(0,boss.hp))} / {int(boss.max_hp)}",True,WHITE)
    screen.blit(hp,(WIDTH//2-hp.get_width()//2, by+bh//2-8))

def draw_game():
    draw_map()
    for sp in G["splats"]:      # пятна крови/масла на земле (под всем)
        sp.draw(screen)
    for sh in G["shells"]:      # гильзы лежат на земле
        sh.draw(screen)
    for tr in G["traps"]:       # ловушки на дороге
        tr.draw(screen)
    for bar in G["barrels"]:    # взрывоопасные бочки
        bar.draw(screen)
    h=G["hero"]
    show_range=(G["state"]=="build")
    near_andrey=(G["state"] in ("build","wave") and dist(h.x,h.y,*ANDREY_POS)<INTERACT_R)
    near_dima=(G["state"] in ("build","wave") and dist(h.x,h.y,*DIMA_POS)<INTERACT_R)
    draw_seller(ANDREY_POS,"Андрей Кол",(210,150,60),near_andrey, ANDREY_IMG)
    draw_seller(DIMA_POS,"Дима Трубаз",(90,160,210),near_dima, DIMA_IMG)

    for t in G["turrets"]:
        sel=(t is G.get("sel_turret_obj"))
        t.draw(screen, show_range or sel, sel)
    for e in G["enemies"]:
        e.draw(screen)
    for b in G["bullets"]:
        b.draw(screen)
    for ef in G["effects"]:
        ef.draw(screen)
    for p in G["particles"]:
        p.draw(screen)
    for pk in G["pickups"]:
        pk.draw(screen)
    h.draw(screen)
    if G.get("drone"):
        G["drone"].draw(screen)
    for ls in G["lasers"]:      # лазерные лучи дрона
        x1,y1,x2,y2,_l=ls
        draw_additive_glow(screen,(x1+x2)/2,(y1+y2)/2,10,CYAN,intensity=90)
        pygame.draw.line(screen,(150,230,255),(x1,y1),(x2,y2),2)
    for ft in G["floats"]:
        ft.draw(screen)

    if G["state"] in ("build","wave") and G["selected_turret"]:
        mx,my=pygame.mouse.get_pos()
        ok=(not near_path(mx,my)) and my>=48
        rng=TURRETS[G["selected_turret"]]["range"]
        draw_range_ring(screen, mx, my, rng, GREEN if ok else RED, True)
        gcol=TURRETS[G["selected_turret"]]["color"]
        pygame.draw.circle(screen,gcol,(mx,my),16)
        pygame.draw.circle(screen,WHITE if ok else RED,(mx,my),16,2)
        draw_button(placement_cancel_rect(), "✕ Отмена установки (ESC)", (220,130,130), font=font_m)

    if G["state"] in ("build","wave") and G.get("selected_trap"):
        mx,my=pygame.mouse.get_pos()
        ok=near_path(mx,my) and my>=48
        gcol=TRAPS[G["selected_trap"]]["color"]
        pygame.draw.circle(screen,gcol,(mx,my),12)
        pygame.draw.circle(screen,WHITE if ok else RED,(mx,my),12,2)
        draw_button(placement_cancel_rect(), "✕ Отмена ловушки (ESC)", (220,130,130), font=font_m)

    draw_hud()
    draw_boss_bar()

    if G["message"]:
        t=font_m.render(G["message"],True,YELLOW)
        screen.blit(t,(WIDTH/2-t.get_width()/2, 126))

    if G["state"]=="build":
        hint="E — магазин / старт волны • Пробел — волна • ЛКМ по башне — прокачка • ✕ над новой башней — отмена • F5 — сохранить • ESC — меню"
        t=font_s.render(hint,True,WHITE)
        screen.blit(t,(WIDTH/2-t.get_width()/2, HEIGHT-26))

    # кнопка ✕ над только что поставленной башней — быстрая отмена установки
    if G["state"] in ("build","wave"):
        cr=last_cancel_rect()
        if cr is not None:
            draw_close_button(cr)

    if G["state"] in ("shop_w","shop_t"):
        draw_night_overlay()   # ночь сохраняется и в меню продавца
        draw_shop()
    if G["state"] in ("build","wave") and G["sel_turret_obj"]:
        draw_upgrade_panel()


def draw_mutator_warn():
    draw_game()
    overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); overlay.fill((0,0,0,160)); screen.blit(overlay,(0,0))
    mut=next((m for m in MUTATORS if m["key"]==G.get("mutator")), None)
    if not mut: return
    draw_title("МУТАТОР ВОЛНЫ!", HEIGHT//2-130, (255,210,90))
    draw_title(mut["name"], HEIGHT//2-46, mut["color"])
    d=font_m.render(mut["desc"], True, WHITE)
    screen.blit(d,(WIDTH//2-d.get_width()//2, HEIGHT//2+44))
    hint=font_s.render("Пробел / клик — в бой!", True, LIGHT)
    screen.blit(hint,(WIDTH//2-hint.get_width()//2, HEIGHT//2+92))


def draw_end(win):
    overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); overlay.fill((0,0,0,190)); screen.blit(overlay,(0,0))
    msg="ПОБЕДА! Кракуля повержен!" if win else "ПОРАЖЕНИЕ"
    col=GREEN if win else RED
    t=font_l.render(msg,True,col)
    screen.blit(t,(WIDTH/2-t.get_width()/2, HEIGHT/2-80))
    if win:
        c=font_m.render("+5 монет!",True,YELLOW)
        screen.blit(c,(WIDTH/2-c.get_width()/2, HEIGHT/2-20))
    t2=font_m.render("R — новая игра • ESC — в меню",True,WHITE)
    screen.blit(t2,(WIDTH/2-t2.get_width()/2, HEIGHT/2+30))


# ====================== АВТО-ОБНОВЛЕНИЕ В ИГРЕ ======================
# Периодически проверяет manifest.json на jsDelivr. Если там версия выше
# GAME_VERSION — показывает окно «Доступно обновление» с кнопкой СКАЧАТЬ.
# По нажатию скачивает свежий game.py поверх текущего и перезапускает игру.
_UPDATE_MANIFEST_URL = "https://cdn.jsdelivr.net/gh/Farg1338/game@main/manifest.json"
_UPDATE_PY_URL       = "https://cdn.jsdelivr.net/gh/Farg1338/game@main/game.py"
_UPDATE = {"latest": None, "checked": 0, "show": False, "phase": "idle", "err": ""}
try:
    _SELF_PATH = os.path.abspath(__file__)
except Exception:
    _SELF_PATH = os.path.abspath("game.py")

def _update_check_tick():
    now = pygame.time.get_ticks()
    if _UPDATE["phase"] == "restart":
        _restart_game(); return
    if _UPDATE["phase"] == "downloading":
        return
    first = (_UPDATE["checked"] == 0 and now > 4000)
    again = (_UPDATE["checked"] != 0 and now - _UPDATE["checked"] > 120000)
    if not (first or again):
        return
    _UPDATE["checked"] = now
    import threading
    def work():
        try:
            req = urllib.request.Request(_UPDATE_MANIFEST_URL + "?t=" + str(now),
                                         headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=15).read()
            d = json.loads(data.decode("utf-8"))
            _UPDATE["latest"] = int(d.get("version", 0))
            if _UPDATE["latest"] > GAME_VERSION:
                _UPDATE["show"] = True
        except Exception as ex:
            _UPDATE["err"] = str(ex)
    threading.Thread(target=work, daemon=True).start()

def _start_self_update():
    _UPDATE["phase"] = "downloading"
    import threading
    def work():
        try:
            req = urllib.request.Request(_UPDATE_PY_URL + "?t=" + str(pygame.time.get_ticks()),
                                         headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=40).read()
            if data and b"pygame" in data[:5000]:
                with open(_SELF_PATH, "wb") as f:
                    f.write(data)
                try:
                    with open(os.path.join(os.path.dirname(_SELF_PATH), "version.txt"), "w") as vf:
                        vf.write(str(_UPDATE.get("latest") or ""))
                except Exception:
                    pass
                _UPDATE["phase"] = "restart"
            else:
                _UPDATE["phase"] = "error"; _UPDATE["err"] = "пустой файл"; _UPDATE["show"] = False
        except Exception as ex:
            _UPDATE["phase"] = "error"; _UPDATE["err"] = str(ex); _UPDATE["show"] = False
    threading.Thread(target=work, daemon=True).start()

def _restart_game():
    try: save_game(silent=True)
    except Exception: pass
    try: pygame.quit()
    except Exception: pass
    try:
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception:
        os._exit(0)

def _update_btn_rects():
    pw, ph = 470, 158
    x = WIDTH // 2 - pw // 2; y = HEIGHT // 2 - ph // 2
    return {"panel": pygame.Rect(x, y, pw, ph),
            "download": pygame.Rect(x + 24, y + ph - 54, pw // 2 - 36, 40),
            "later": pygame.Rect(x + pw // 2 + 12, y + ph - 54, pw // 2 - 36, 40)}

def _draw_update_ui():
    if not _UPDATE["show"]:
        return
    r = _update_btn_rects(); p = r["panel"]
    dim = pygame.Surface((p.width + 16, p.height + 16), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 150)); screen.blit(dim, (p.x - 8, p.y - 8))
    draw_round_gradient(p, (66, 76, 120), (34, 38, 60), 16)
    pygame.draw.rect(screen, (245, 205, 70), p, 2, border_radius=16)
    t1 = font_m.render("Доступно обновление!", True, (255, 225, 120))
    screen.blit(t1, (p.centerx - t1.get_width() // 2, p.y + 16))
    t2 = font_s.render("Версия " + str(GAME_VERSION) + "  →  " + str(_UPDATE.get("latest")), True, WHITE)
    screen.blit(t2, (p.centerx - t2.get_width() // 2, p.y + 52))
    if _UPDATE["phase"] == "downloading":
        d = font_m.render("Скачивание...", True, (180, 220, 255))
        screen.blit(d, (p.centerx - d.get_width() // 2, p.bottom - 46))
    else:
        draw_button(r["download"], "СКАЧАТЬ", (130, 205, 150), font=font_m)
        draw_button(r["later"], "ПОЗЖЕ", (150, 175, 205), font=font_m)

def _update_handle_click(pos):
    if not _UPDATE["show"] or _UPDATE["phase"] == "downloading":
        return False
    r = _update_btn_rects()
    if r["download"].collidepoint(pos):
        _start_self_update(); return True
    if r["later"].collidepoint(pos):
        _UPDATE["show"] = False; return True
    return False

_real_eget_upd = pygame.event.get
def _event_get_upd(*a, **k):
    evs = _real_eget_upd(*a, **k)
    if a or k:
        return evs
    out = []
    for e in evs:
        if e.type == pygame.MOUSEBUTTONDOWN and getattr(e, "button", 1) == 1 and _update_handle_click(e.pos):
            continue
        out.append(e)
    return out
pygame.event.get = _event_get_upd
# ====================== /АВТО-ОБНОВЛЕНИЕ ======================

# ====================== ГЛАВНЫЙ ЦИКЛ ======================
running=True
while running:
    dt=clock.tick(FPS)/1000.0
    keys=pygame.key.get_pressed()
    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            running=False
        elif event.type==pygame.KEYDOWN:
            if event.key in (pygame.K_f, pygame.K_F11):
                pygame.display.toggle_fullscreen()
            elif event.key==pygame.K_ESCAPE:
                if G["state"]=="play_menu": G["state"]="menu"
                elif G["state"]=="mutator_warn": G["state"]="wave"
                elif G["state"]=="part2": G["state"]="menu"
                elif G["state"]=="patch": G["state"]="menu"
                elif G["state"]=="skins": save_profile(); G["state"]="menu"
                elif G["state"]=="settings": save_profile(); G["state"]="menu"
                elif G["state"] in ("shop_w","shop_t"): G["state"]=G.get("shop_return","build")
                elif G["state"] in ("build","wave") and (G["selected_turret"] or G.get("selected_trap") or G["sel_turret_obj"]):
                    G["selected_turret"]=None; G["selected_trap"]=None; G["sel_turret_obj"]=None
                elif G["state"] in ("build","wave"):
                    G["resume_state"]="build"; save_game(silent=True); G["state"]="menu"
                elif G["state"] in ("gameover","win"): G["state"]="menu"
                elif G["state"]=="menu": running=False
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                if G["state"]=="build": start_wave()
                elif G["state"]=="mutator_warn": G["state"]="wave"
            elif event.key==pygame.K_e:
                if G["state"] in ("build","wave"):
                    if dist(G["hero"].x,G["hero"].y,*ANDREY_POS)<INTERACT_R:
                        G["shop_return"]=G["state"]; G["state"]="shop_w"; G["message"]=""
                    elif dist(G["hero"].x,G["hero"].y,*DIMA_POS)<INTERACT_R:
                        G["shop_return"]=G["state"]; G["state"]="shop_t"; G["message"]=""
                    elif G["state"]=="build":
                        start_wave()  # авто-скип: сразу следующая волна
                elif G["state"] in ("shop_w","shop_t"):
                    G["state"]=G.get("shop_return","build")
            elif event.key==pygame.K_F5:
                if G["state"] in ("build","wave"): save_game()
            elif event.key==pygame.K_r:
                if G["state"] in ("gameover","win"):
                    G=new_game(); G["state"]="build"; G["started"]=True; reset_autosave()
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                if G["state"]=="patch":
                    d=40 if event.key in (pygame.K_DOWN,pygame.K_PAGEDOWN) else -40
                    if event.key in (pygame.K_PAGEUP,pygame.K_PAGEDOWN): d*=4
                    G["patch_scroll"]=max(0,min(G.get("_patch_max",0),G.get("patch_scroll",0)+d))
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            if G["state"] in ("menu","play_menu"):
                if handle_menu_click(event.pos)=="quit": running=False
            elif G["state"]=="skins": handle_skin_click(event.pos)
            elif G["state"]=="part2": G["state"]="menu"
            elif G["state"]=="mutator_warn": G["state"]="wave"
            elif G["state"]=="settings": handle_settings_click(event.pos)
            elif G["state"]=="patch":
                if patch_back_rect().collidepoint(event.pos): G["state"]="menu"
            elif G["state"] in ("shop_w","shop_t"): handle_shop_click(event.pos)
            elif G["state"] in ("build","wave"):
                if G["selected_turret"]:
                    if placement_cancel_rect().collidepoint(event.pos):
                        G["selected_turret"]=None; G["message"]="Установка отменена"
                    else:
                        try_place_turret(event.pos)
                elif G.get("selected_trap"):
                    if placement_cancel_rect().collidepoint(event.pos):
                        G["selected_trap"]=None; G["message"]="Установка ловушки отменена"
                    else:
                        try_place_trap(event.pos)
                else: handle_build_click(event.pos)
        elif event.type==pygame.MOUSEWHEEL:
            if G["state"]=="patch":
                G["patch_scroll"]=max(0,min(G.get("_patch_max",0),G.get("patch_scroll",0)-event.y*45))

    if G["state"]=="wave":
        update_wave(dt, keys)
    elif G["state"]=="mutator_warn":
        G["mut_warn_timer"]-=dt
        if G["mut_warn_timer"]<=0: G["state"]="wave"
    elif G["state"]=="build":
        h=G["hero"]; h.update(dt, keys)
        G["turret_stun"]=max(0.0, G.get("turret_stun",0)-dt)
        for pk in G["pickups"]:
            pk.update(dt, h)
        G["pickups"]=[pk for pk in G["pickups"] if pk.alive]
        G["particles"]=[p for p in G["particles"] if p.update(dt)]
        G["floats"]=[ft for ft in G["floats"] if ft.update(dt)]
        G["shells"]=[sh for sh in G["shells"] if sh.update(dt)]
        G["splats"]=[sp for sp in G["splats"] if sp.update(dt)]
        if G.get("drone"):
            G["drone"].update(dt, h, G["enemies"])
        for ls in G["lasers"]:
            ls[4]-=dt
        G["lasers"]=[ls for ls in G["lasers"] if ls[4]>0]

    if G["state"] in ("build","wave"):
        autosave_timer+=dt
        if autosave_timer>=AUTOSAVE_SECONDS and G["state"]=="build":
            save_game(silent=True); autosave_timer=0.0

    screen.fill(DARK)
    if G["state"] in ("menu","play_menu"): draw_menu()
    elif G["state"]=="part2": draw_part2()
    elif G["state"]=="skins": draw_skins()
    elif G["state"]=="settings": draw_settings()
    elif G["state"]=="patch": draw_patchnotes()
    elif G["state"]=="mutator_warn": draw_mutator_warn()
    else:
        draw_game()
        if G["state"]=="gameover": draw_end(False)
        elif G["state"]=="win": draw_end(True)

    if G["state"] in ("build","wave","mutator_warn"):
        draw_hurt_vignette()

    if SHAKE > 0.5:
        _frame = screen.copy()
        screen.fill(BLACK)
        screen.blit(_frame, (random.randint(-int(SHAKE),int(SHAKE)),
                             random.randint(-int(SHAKE),int(SHAKE))))
    SHAKE = max(0.0, SHAKE - 60.0*dt)
    HURT_FLASH = max(0.0, HURT_FLASH - 2.2*dt)

    pygame.display.flip()

pygame.quit()
sys.exit()
