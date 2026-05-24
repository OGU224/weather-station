"""Compagnon pixel-art style Undertale pour M5Stack Core2."""

import json

try:
    from M5 import Lcd
except ImportError:
    Lcd = None

PX = 4

PAL = {
    ".": None, "W": 0xFFFFFF, "K": 0x000000, "Y": 0xFFFF00, "C": 0x00DDFF,
    "R": 0xFF2222, "G": 0x00CC00, "P": 0xFF88AA, "A": 0x999999, "D": 0x555555,
    "B": 0x3388FF, "T": 0xAA5522, "E": 0xFFEECC, "L": 0x00AA00, "V": 0xAA77FF,
    "O": 0xFF8800, "S": 0x66BBFF, "H": 0xFF4466, "M": 0xFFAA00, "N": 0x222222,
    "Q": 0xDDDDDD, "F": 0x88FF88, "U": 0xBB0000, "I": 0x4444FF, "X": 0xFF66AA,
}

SAVE_FILE = "/flash/buddy_cfg.json"

# --- SPRITES 16x16 ---
GHOST_IDLE = ["................","......WWWW......","....WWWWWWWW....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","..WWKWWWWWWKWW..","..WWKKWWWWKKWW..","..WWWWWWWWWWWW..","..WWWWWKKWWWWW..","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","..WWW.WWWW.WWW..","..WW...WW...WW..","..W.........W...","................"]
GHOST_BLINK = ["................","......WWWW......","....WWWWWWWW....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","..WWKKWWWWKKWW..","..WWWWWWWWWWWW..","..WWWWWKKWWWWW..","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","..WWW.WWWW.WWW..","..WW...WW...WW..","..W.........W...","................"]
GHOST_HAPPY = ["................","......WWWW......","....WWWWWWWW....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","..WWKKWWWWKKWW..","..WWWWWWWWWWWW..","..WWWWKKKKWWWW..","..WWWKWWWWKWWW..","..WWWWWWWWWWWW..","..WWW.WWWW.WWW..","..WW...WW...WW..","..W.........W...","................"]
GHOST_ALERT = ["................","......WWWW......","....WWWWWWWW....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","..WWKWWWWWWKWW..","..WWKKWWWWKKWW..","..CWWWWWWWWWWC..","..CWWWKKKWWWWC..","..WWWKWWWKWWWW..","..WWWWWWWWWWWW..","..WWW.WWWW.WWW..","..WW...WW...WW..","..W.........W...","................"]
GHOST_SPEAK = ["................","......WWWW......","....WWWWWWWW....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","..WWKWWWWWWKWW..","..WWKKWWWWKKWW..","..WWWWWWWWWWWW..","..WWWWKKKWWWWW..","..WWWWKWKWWWWW..","..WWWWKKKWWWWW..","..WWW.WWWW.WWW..","..WW...WW...WW..","..W.........W...","................"]
GHOST_SLEEP = ["................","......WWWW......","....WWWWWWWW....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","..WWKKWWWWKKWW..","..WWWWWWWWWWWW..","..WWWWWKKWWWWW..","..WWWWWWWWWWWW..","..WWWWWWWWWWWWCC","..WWW.WWWW.WWCC.","..WW...WW...CC..","..W.........C...","................"]

SKULL_IDLE = ["................",".....WWWWWW.....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWKKKKWKKKKW..","..WWKCCKWKCCWW..","..WWKKKKWKKKKW..","..WWWWWWWWWWWW..","..WWWWWKKWWWWW..","..WKWKWKWKWKWW..","..WWWWWWWWWWWW..","...WWWWWWWWWW...","....SSSSSSSS....","...SSSSSSSSSS...","...SSYSSSSSSS...","....SS...SS....."]
SKULL_BLINK = ["................",".....WWWWWW.....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWKKKKWKKKKW..","..WWWWWWWWWWWW..","..WWKKKKWKKKKW..","..WWWWWWWWWWWW..","..WWWWWKKWWWWW..","..WKWKWKWKWKWW..","..WWWWWWWWWWWW..","...WWWWWWWWWW...","....SSSSSSSS....","...SSSSSSSSSS...","...SSYSSSSSSS...","....SS...SS....."]
SKULL_HAPPY = ["................",".....WWWWWW.....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWKKKKWKKKKW..","..WWKYYKWKYYWW..","..WWKKKKWKKKKW..","..WWWWWWWWWWWW..","..WWWWWKKWWWWW..","..WKWKWKWKWKWW..","..WWWWWWWWWWWW..","...WWWWWWWWWW...","....SSSSSSSS....","...SSSSSSSSSS...","...SSYSSSSSSS...","....SS...SS....."]
SKULL_ALERT = ["................",".....WWWWWW.....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWKKKKWKKKKW..","..WWKRRKWKRRWW..","..WWKKKKWKKKKW..","..WWWWWWWWWWWW..","..WWWWWKKWWWWW..","..WWWWWWWWWWWW..","..WWWWWWWWWWWW..","...WWWWWWWWWW...","....SSSSSSSS....","...SSSSSSSSSS...","...SSYSSSSSSS...","....SS...SS....."]
SKULL_SPEAK = ["................",".....WWWWWW.....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWKKKKWKKKKW..","..WWKCCKWKCCWW..","..WWKKKKWKKKKW..","..WWWWWWWWWWWW..","..WWWWKKKWWWWW..","..WKWKWWWKWKWW..","..WWWWWWWWWWWW..","...WWWWWWWWWW...","....SSSSSSSS....","...SSSSSSSSSS...","...SSYSSSSSSS...","....SS...SS....."]
SKULL_SLEEP = ["................",".....WWWWWW.....","...WWWWWWWWWW...","..WWWWWWWWWWWW..","..WWKKKKWKKKKW..","..WWWWWWWWWWWW..","..WWKKKKWKKKKW..","..WWWWWWWWWWWW..","..WWWWWKKWWWWW..","..WKWKWKWKWKWW..","..WWWWWWWWWWWW..","...WWWWWWWWWW.CC","....SSSSSSSS.CC.","...SSSSSSSSCC...","...SSYSSSSC.....","....SS...SS....."]

FLOWER_IDLE = ["......YYYY......","...YY.YYYY.YY...","..YYYEEEEEEYYY..","..YEEEEEEEEEEY..","..YEEKEEEEKEY...","..YEKKEEEEKKKY..","..YEEEEEEEEEY...","..YYEEKKKKEEYY..","...YYYYYYYYYY...","......LLLL......",".....LLLLLL.....","...LL..LL.......","......LL..LL....","....TTTTTTTT....","....TTTTTTTT....","....TTTTTTTT...."]
FLOWER_BLINK = ["......YYYY......","...YY.YYYY.YY...","..YYYEEEEEEYYY..","..YEEEEEEEEEEY..","..YEEEEEEEEEY...","..YEKKEEEEKKKY..","..YEEEEEEEEEY...","..YYEEKKKKEEYY..","...YYYYYYYYYY...","......LLLL......",".....LLLLLL.....","...LL..LL.......","......LL..LL....","....TTTTTTTT....","....TTTTTTTT....","....TTTTTTTT...."]
FLOWER_HAPPY = ["......YYYY......","...YY.YYYY.YY...","..YYYEEEEEEYYY..","..YEEEEEEEEEEY..","..YEEWEEEWKEY...","..YEKKEEEEKKKY..","..YEEPPEEEPPEY..","..YYEEKKKKEEYY..","..YYEKWWWKEYYY..","......LLLL......",".....LLLLLL.....","...LL..LL.......","......LL..LL....","....TTTTTTTT....","....TTTTTTTT....","....TTTTTTTT...."]
FLOWER_ALERT = ["......DDDD......","...DD.DDDD.DD...","..DDDEEEEEEDDD..","..DEEEEEEEEEEY..","..DEEKEEEEKED...","..DEKKEEEEKKKY..","..DEEEEEEEEEY...","..DDEEKWWKEEDD..","..DDEKWWWKEDDD..","......LLLL......",".....LLLLLL.....","...LL..LL.......","......LL..LL....","....TTTTTTTT....","....TTTTTTTT....","....TTTTTTTT...."]
FLOWER_SPEAK = ["......YYYY......","...YY.YYYY.YY...","..YYYEEEEEEYYY..","..YEEEEEEEEEEY..","..YEEKEEEEKEY...","..YEKKEEEEKKKY..","..YEEEEEEEEEY...","..YYEEKKKKEEYY..","..YYEEKEKKEYYY..","......LLLL......",".....LLLLLL.....","...LL..LL.......","......LL..LL....","....TTTTTTTT....","....TTTTTTTT....","....TTTTTTTT...."]
FLOWER_SLEEP = ["......DDDD......","...DD.DDDD.DD...","..DDDEEEEEEDDD..","..DEEEEEEEEEEY..","..DEEEEEEEEEY...","..DEKKEEEEKKKY..","..DEEEEEEEEEY...","..DDEEKKKKEEDD..","...DDDDDDDDD..CC","......LLLL...CC.",".....LLLLLL.CC..","...LL..LL..C....","......LL..LL....","....TTTTTTTT....","....TTTTTTTT....","....TTTTTTTT...."]

CAT_IDLE = ["..WW........WW..","..WWW......WWW..","..PPWW....WWPP..","...WWWWWWWWWW...","...WWWWWWWWWW...","...WKKWWWWKKW...","...WGKWWWWGKW...","..AWWWWPPWWWWA..",".AAWWWWWWWWWWAA.","...WWWWWWWWWW...","...WWWWWWWWWW...","...WWWWWWWWWW...","...WWWWWWWWWW...","...WW......WW...","...WW......WW.W.","............WW.."]
CAT_BLINK = ["..WW........WW..","..WWW......WWW..","..PPWW....WWPP..","...WWWWWWWWWW...","...WWWWWWWWWW...","...WWWWWWWWWW...","...WKKWWWWKKW...","..AWWWWPPWWWWA..",".AAWWWWWWWWWWAA.","...WWWWWWWWWW...","...WWWWWWWWWW...","...WWWWWWWWWW...","...WWWWWWWWWW...","...WW......WW...","...WW......WW.W.","............WW.."]
CAT_HAPPY = ["..WW........WW..","..WWW......WWW..","..PPWW....WWPP..","...WWWWWWWWWW...","...WWWWWWWWWW...","...WWWWWWWWWW...","...WKKWWWWKKW...","..AWWWWPPWWWWA..",".AAWWKWWWKWWAA..","...WWWKKKKWWW...","...WWWWWWWWWW...","...WWWWWWWWWW...","...WWWWWWWWWW...","...WW......WW...","...WW......WW.W.","............WW.."]
CAT_ALERT = ["..WW........WW..","..WWWW....WWWW..","..PPWWW..WWWPP..","...WWWWWWWWWW...","...WWWWWWWWWW...","...WKWWWWWWKW...","...WKKWWWWKKW...","..AWWWWPPWWWWA..",".AAWWWWWWWWWWAA.","...WWWKKKWWWW...","...WWKWWWKWWW...","...WWWWWWWWWW...","...WWWWWWWWWW...","...WW......WW...","...WW......WWW..","............W..."]
CAT_SPEAK = ["..WW........WW..","..WWW......WWW..","..PPWW....WWPP..","...WWWWWWWWWW...","...WWWWWWWWWW...","...WKKWWWWKKW...","...WGKWWWWGKW...","..AWWWWPPWWWWA..",".AAWWWKKKWWWAA..","...WWWKWKWWWW...","...WWWKKKWWWW...","...WWWWWWWWWW...","...WWWWWWWWWW...","...WW......WW...","...WW......WW.W.","............WW.."]
CAT_SLEEP = ["..WW........WW..","..WW.......WWW..","..PPWW....WWPP..","...WWWWWWWWWW...","...WWWWWWWWWW...","...WWWWWWWWWW...","...WKKWWWWKKW...","..AWWWWWWWWWWA..",".AAWWWWWWWWWWAA.","...WWWWKKWWWW...","...WWWWWWWWWW.CC","...WWWWWWWWWWCC.","...WWWWWWWWCC...","...WW.....CC....","...WW....WW.W...","............WW.."]

ROBOT_IDLE = [".......YY.......",".......AA.......","...AAAAAAAAAA...","...ANNNNNNNNNA..","...ANNNNNNNNNA..","...ANGGNNGGNA...","...ANGGNNGGNA...","...ANNNNNNNNNA..","...ANGGGGGGNNA..","...AAAAAAAAAA...","...AAAAAAAAAA...","..AA.ADDDA.AA...","..AA.ARRRA.AA...","..AA.ADDDA.AA...","....AA..AA......","....AA..AA......"]
ROBOT_BLINK = [".......YY.......",".......AA.......","...AAAAAAAAAA...","...ANNNNNNNNNA..","...ANNNNNNNNNA..","...ANNNNNNNNNA..","...ANGGNNGGNA...","...ANNNNNNNNNA..","...ANGGGGGGNNA..","...AAAAAAAAAA...","...AAAAAAAAAA...","..AA.ADDDA.AA...","..AA.ARRRA.AA...","..AA.ADDDA.AA...","....AA..AA......","....AA..AA......"]
ROBOT_HAPPY = [".......YY.......",".......AA.......","...AAAAAAAAAA...","...ANNNNNNNNNA..","...ANNNNNNNNNA..","...ANYYNNYYYA...","...ANYYNNYYYA...","...ANNNNNNNNNA..","...ANYYYYYNNA...","...AAAAAAAAAA...","...AAAAAAAAAA...","..AA.ADDDA.AA...","..AA.ARRRA.AA...","..AA.ADDDA.AA...","....AA..AA......","....AA..AA......"]
ROBOT_ALERT = [".......RR.......",".......AA.......","...AAAAAAAAAA...","...ANNNNNNNNNA..","...ANNNNNNNNNA..","...ANRRNNRRNA...","...ANRRNNRRNA...","...ANNNNNNNNNA..","...ANRRRRRRNNA..","...AAAAAAAAAA...","...AAAAAAAAAA...","..AA.ADDDA.AA...","..AA.ARRRA.AA...","..AA.ADDDA.AA...","....AA..AA......","....AA..AA......"]
ROBOT_SPEAK = [".......YY.......",".......AA.......","...AAAAAAAAAA...","...ANNNNNNNNNA..","...ANNNNNNNNNA..","...ANGGNNGGNA...","...ANGGNNGGNA...","...ANNNNNNNNNA..","...ANGNGNGNNNA..","...AAAAAAAAAA...","...AAAAAAAAAA...","..AA.ADDDA.AA...","..AA.ARRRA.AA...","..AA.ADDDA.AA...","....AA..AA......","....AA..AA......"]
ROBOT_SLEEP = ["................",".......AA.......","...AAAAAAAAAA...","...ANNNNNNNNNA..","...ANNNNNNNNNA..","...ANNNNNNNNNA..","...ANDDNNDDNA...","...ANNNNNNNNNA..","...ANNDDDDNNA...","...AAAAAAAAAA.CC","...AAAAAAAAAA.CC","..AA.ADDDA.AACC.","..AA.ADDDA.AAC..","..AA.ADDDA.AA...","....AA..AA......","....AA..AA......"]

MUSH_IDLE = ["......RRRRRR....","....RRRRRRRRRR..","..RRWWRRRRRWWRR.","..RRRRRRRRRRRRRR",".RRRRRWWRRRRRRR.","..RRRRRRRRRRRRRR.","..EEEEEEEEEEEE..","..EEEEEEEEEEEE..","...EEKKEEEKKEE..","...EEKKEEEKKE...","..PPEE.KK.EEPP..","...EEEKKKKEEE...","....EEEEEEEE....",".....EEEEEE.....","....TTTTTTTT....","....TTTTTTTT...."]
MUSH_BLINK = ["......RRRRRR....","....RRRRRRRRRR..","..RRWWRRRRRWWRR.","..RRRRRRRRRRRRRR",".RRRRRWWRRRRRRR.","..RRRRRRRRRRRRRR.","..EEEEEEEEEEEE..","..EEEEEEEEEEEE..","...EEEEEEEEEE...","...EEKKEEEKKE...","..PPEE.KK.EEPP..","...EEEKKKKEEE...","....EEEEEEEE....",".....EEEEEE.....","....TTTTTTTT....","....TTTTTTTT...."]
MUSH_HAPPY = ["......RRRRRR....","....RRRRRRRRRR..","..RRWWRRRRRWWRR.","..RRRRRRRRRRRRRR",".RRRRRWWRRRRRRR.","..RRRRRRRRRRRRRR.","..EEEEEEEEEEEE..","..EEEEEEEEEEEE..","...EEWWEEWWEE...","...EEKKEEEKKE...","..PPEE.KK.EEPP..","...EEKWWWKEEE...","....EKWWWKEE....",".....EEEEEE.....","....TTTTTTTT....","....TTTTTTTT...."]
MUSH_ALERT = ["......OOOOOO....","....OOOOOOOOOO..","..OOWWOOOOOOWOO.","..OOOOOOOOOOOOOO",".OOOOOWWOOOOOOO.","..OOOOOOOOOOOOOO.","..EEEEEEEEEEEE..","..EEEEEEEEEEEE..","...EEKEEEEKEE...","...EEKKEEEKKE...","..PPEE.KK.EEPP..","...EEEKWWKEEE...","....EEKWWKEE....",".....EEEEEE.....","....TTTTTTTT....","....TTTTTTTT...."]
MUSH_SPEAK = ["......RRRRRR....","....RRRRRRRRRR..","..RRWWRRRRRWWRR.","..RRRRRRRRRRRRRR",".RRRRRWWRRRRRRR.","..RRRRRRRRRRRRRR.","..EEEEEEEEEEEE..","..EEEEEEEEEEEE..","...EEKKEEEKKEE..","...EEKKEEEKKE...","..PPEE.KK.EEPP..","...EEEKKKKEEE...","...EEEKEKEEE....",".....EEEEEE.....","....TTTTTTTT....","....TTTTTTTT...."]
MUSH_SLEEP = ["......DDDDDD....","....DDDDDDDDDD..","..DDWWDDDDDWWDD.","..DDDDDDDDDDDDDD",".DDDDDWWDDDDDDD.","..DDDDDDDDDDDDRR.","..EEEEEEEEEEEE..","..EEEEEEEEEEEE..","...EEEEEEEEEE...","...EEKKEEEKKE...","..PPEE.KK.EEPP..","...EEEKKKKEEE.CC","....EEEEEEEE.CC.",".....EEEEEE.CC..","....TTTTTTTT....","....TTTTTTTT...."]

CHARACTERS = [
    {"name": "Ghost", "color": 0xFFFFFF, "sprites": {"idle": GHOST_IDLE, "blink": GHOST_BLINK, "happy": GHOST_HAPPY, "alert": GHOST_ALERT, "speak": GHOST_SPEAK, "sleep": GHOST_SLEEP}, "desc": "Shy and gentle. Cries when it rains."},
    {"name": "Skull", "color": 0x00DDFF, "sprites": {"idle": SKULL_IDLE, "blink": SKULL_BLINK, "happy": SKULL_HAPPY, "alert": SKULL_ALERT, "speak": SKULL_SPEAK, "sleep": SKULL_SLEEP}, "desc": "Chill jokester. Glowing eye puns."},
    {"name": "Flower", "color": 0xFFFF00, "sprites": {"idle": FLOWER_IDLE, "blink": FLOWER_BLINK, "happy": FLOWER_HAPPY, "alert": FLOWER_ALERT, "speak": FLOWER_SPEAK, "sleep": FLOWER_SLEEP}, "desc": "Expressive bloom. Wilts in dry air."},
    {"name": "Cat", "color": 0xFFFFFF, "sprites": {"idle": CAT_IDLE, "blink": CAT_BLINK, "happy": CAT_HAPPY, "alert": CAT_ALERT, "speak": CAT_SPEAK, "sleep": CAT_SLEEP}, "desc": "Curious furball. Naps when comfy."},
    {"name": "Robot", "color": 0x00FF00, "sprites": {"idle": ROBOT_IDLE, "blink": ROBOT_BLINK, "happy": ROBOT_HAPPY, "alert": ROBOT_ALERT, "speak": ROBOT_SPEAK, "sleep": ROBOT_SLEEP}, "desc": "Precise and logical. LED emotions."},
    {"name": "Mushroom", "color": 0xFF2222, "sprites": {"idle": MUSH_IDLE, "blink": MUSH_BLINK, "happy": MUSH_HAPPY, "alert": MUSH_ALERT, "speak": MUSH_SPEAK, "sleep": MUSH_SLEEP}, "desc": "Sweet and soft. Loves humidity."},
]


def draw_sprite(sprite, x, y, bg_color=0x000000, px=PX):
    if not Lcd:
        return
    for r, row in enumerate(sprite):
        for c, ch in enumerate(row):
            col = PAL.get(ch)
            if col is not None:
                Lcd.fillRect(x + c * px, y + r * px, px, px, col)
            else:
                Lcd.fillRect(x + c * px, y + r * px, px, px, bg_color)


def clear_sprite_area(x, y, bg=0x000000, px=PX):
    if Lcd:
        Lcd.fillRect(x, y, 16 * px, 16 * px, bg)


def load_selection():
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.loads(f.read())
            idx = int(data.get("character", 0))
            if 0 <= idx < len(CHARACTERS):
                return idx
    except:
        pass
    return 0


def save_selection(idx):
    try:
        with open(SAVE_FILE, "w") as f:
            f.write(json.dumps({"character": idx}))
    except:
        pass


class Buddy:
    IDLE  = "idle"
    ALERT = "alert"
    SPEAK = "speak"
    HAPPY = "happy"
    SLEEP = "sleep"

    def __init__(self):
        self.char_idx = load_selection()
        self.state = self.IDLE
        self.frame = 0
        self._prev_sprite_key = None

    @property
    def character(self): return CHARACTERS[self.char_idx]
    @property
    def name(self): return self.character["name"]
    @property
    def color(self): return self.character["color"]
    @property
    def desc(self): return self.character["desc"]

    def select(self, idx):
        self.char_idx = idx % len(CHARACTERS)
        save_selection(self.char_idx)
        self.reset_motion_cache()

    def reset_motion_cache(self):
        self._prev_sprite_key = None

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self.frame = 0

    def update(self):
        self.frame = (self.frame + 1) % 120
        new_key = self._current_sprite_key()
        dx, dy = self.get_offset()
        changed = (new_key, dx, dy) != self._prev_sprite_key
        return changed

    def _current_sprite_key(self):
        if self.state == self.IDLE and 54 <= self.frame <= 58: return "blink"
        if self.state == self.HAPPY and 54 <= self.frame <= 58: return "blink"
        if self.state == self.SPEAK: return "speak" if (self.frame // 8) % 2 == 0 else "idle"
        return self.state

    def _current_sprite(self):
        key = self._current_sprite_key()
        sprites = self.character["sprites"]
        return sprites.get(key, sprites["idle"]), key

    def get_offset(self):
        f = self.frame
        if self.state == self.IDLE: return (0, -2 if (f // 20) % 2 == 0 else 0)
        if self.state == self.HAPPY: return (0, [-3, -1, 0, -1][f // 10 % 4])
        if self.state == self.ALERT: return ([-2, 0, 2, 0][f % 4], 0)
        if self.state == self.SPEAK: return (0, -1 if (f // 12) % 2 == 0 else 0)
        return (0, 0)

    def draw(self, cx, cy, bg=0x000000, px=PX):
        sprite, key = self._current_sprite()
        dx, dy = self.get_offset()
        new_state = (key, dx, dy)
        
        if new_state == self._prev_sprite_key:
            return
            
        sx = cx - (8 * px) + dx
        sy = cy - (8 * px) + dy
        old = self._prev_sprite_key
        
        if old and (old[1] != dx or old[2] != dy):
            old_sx = cx - (8 * px) + old[1]
            old_sy = cy - (8 * px) + old[2]
            clear_sprite_area(old_sx, old_sy, bg, px)
            
        draw_sprite(sprite, sx, sy, bg, px)
        self._prev_sprite_key = new_state

    def draw_small(self, cx, cy, bg=0x000000): 
        # L'appel à draw() héritera de la logique de cache de draw()
        self.draw(cx, cy, bg, px=3)
