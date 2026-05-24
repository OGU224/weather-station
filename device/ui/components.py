"""Composants UI style Undertale pour M5Stack Core2.
Rendu 100% direct sur le Framebuffer via Lcd (sans aucun Widget).
"""

try:
    from M5 import Lcd
except ImportError:
    Lcd = None

# === Couleurs principales du theme Undertale ===
BLACK = 0x000000
WHITE = 0xFFFFFF
YELLOW = 0xFFFF00
RED = 0xFF0000
CYAN = 0x00FFFF
GREEN = 0x00FF00
GRAY = 0x888888
DARK_GRAY = 0x444444
HEART_RED = 0xFF2222
HP_GREEN = 0x00FF00
HP_RED = 0xFF0000
ORANGE = 0xFF8800

# === References des polices standard ===
FONT_SM = None
FONT_MD = None
FONT_LG = None


def init():
    """Initialise les references de polices de LovyanGFX/M5GFX."""
    global FONT_SM, FONT_MD, FONT_LG
    if Lcd:
        FONT_SM = Lcd.FONTS.DejaVu12
        FONT_MD = Lcd.FONTS.DejaVu18
        FONT_LG = Lcd.FONTS.DejaVu24


def hide_all_components():
    """Nettoie l'ecran complet en noir."""
    if Lcd:
        Lcd.fillScreen(BLACK)


# ============================================================
#  BOITE DE DIALOGUE — cadre blanc, fond noir, texte blanc
# ============================================================

def draw_dialogue_box(x, y, w, h, border=3):
    """Dessine le cadre de la boite de dialogue Undertale."""
    if not Lcd:
        return
    for i in range(border):
        Lcd.drawRect(x + i, y + i, w - 2 * i, h - 2 * i, WHITE)
    Lcd.fillRect(x + border, y + border, w - 2 * border, h - 2 * border, BLACK)


def draw_dialogue_text(text, x=12, y=148, w=296, max_lines=3):
    """Affiche du texte directement sur le LCD avec un padding de nettoyage."""
    if not Lcd:
        return

    words = str(text).split(" ")
    lines = []
    current = "* "
    max_chars = 28

    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = current + word + " "
        else:
            lines.append(current.rstrip())
            current = "* " + word + " "
    if current.strip():
        lines.append(current.rstrip())

    lines = lines[:max_lines]

    if FONT_SM:
        Lcd.setFont(FONT_SM)

    for i, line in enumerate(lines):
        ly = y + i * 16
        cleaned_line = _clean(line)
        
        # Le fond noir specifie ici efface l'ancien texte sans clignotement
        Lcd.setTextColor(WHITE, BLACK)
        Lcd.drawString(cleaned_line, x, ly)

    # Efface les lignes inutilisees si le nouveau texte est plus court
    Lcd.setTextColor(BLACK, BLACK)
    for i in range(len(lines), max_lines):
        ly = y + i * 16
        Lcd.fillRect(x, ly, w, 16, BLACK)


# ============================================================
#  BARRE HP — humidite affichee comme points de vie
# ============================================================

def draw_hp_bar(humidity, x=10, y=200, w=200):
    """Dessine la barre HP representant l'humidite."""
    if not Lcd:
        return

    hum = max(0, min(100, int(humidity or 0)))
    bar_h = 10
    fill_w = int(w * hum / 100)
    color = HP_GREEN if hum >= 40 else HP_RED

    if FONT_SM:
        Lcd.setFont(FONT_SM)
        
    # Ecriture du label HP statique
    Lcd.setTextColor(YELLOW, BLACK)
    Lcd.drawString("HP", x, y - 2)

    # Rendu de la jauge
    Lcd.fillRect(x + 28, y, w, bar_h, 0x440000)
    Lcd.drawRect(x + 28, y, w, bar_h, color)
    if fill_w > 0:
        Lcd.fillRect(x + 29, y + 1, fill_w - 2, bar_h - 2, color)

    # Valeur numerique
    val_text = "{:3d} / 100".format(hum)
    vx = x + 28 + w + 6
    Lcd.setTextColor(WHITE, BLACK)
    Lcd.drawString(val_text, vx, y - 2)


# ============================================================
#  MENU UNDERTALE — barre du bas avec coeur selecteur
# ============================================================

MENU_ITEMS = ["DATA", "FCST", "ASK", "WIFI"]


def draw_menu(selected=0, y=224):
    """Dessine la barre de menu style Undertale."""
    if not Lcd:
        return

    n = len(MENU_ITEMS)
    slot_w = 320 // n
    Lcd.fillRect(0, y - 4, 320, 20, BLACK)

    if FONT_SM:
        Lcd.setFont(FONT_SM)

    for i, item in enumerate(MENU_ITEMS):
        ix = i * slot_w + 23
        color = YELLOW if i == selected else WHITE
        Lcd.setTextColor(color, BLACK)
        Lcd.drawString(item, ix, y)

    # Nettoyage et dessin du coeur selecteur geometrique
    for j in range(n):
        Lcd.fillRect(j * slot_w + 2, y, 14, 14, BLACK)
        
    cx = selected * slot_w + 4
    cy = y + 1
    Lcd.fillRect(cx + 1, cy, 2, 1, HEART_RED)
    Lcd.fillRect(cx + 4, cy, 2, 1, HEART_RED)
    Lcd.fillRect(cx, cy + 1, 7, 1, HEART_RED)
    Lcd.fillRect(cx, cy + 2, 7, 1, HEART_RED)
    Lcd.fillRect(cx + 1, cy + 3, 5, 1, HEART_RED)
    Lcd.fillRect(cx + 2, cy + 4, 3, 1, HEART_RED)
    Lcd.fillRect(cx + 3, cy + 5, 1, 1, HEART_RED)


# ============================================================
#  BARRE DU HAUT
# ============================================================

def draw_topbar(left_text="", right_text="", bg=BLACK):
    """Dessine la barre superieure."""
    if not Lcd:
        return
    Lcd.fillRect(0, 0, 320, 16, bg)

    if FONT_SM:
        Lcd.setFont(FONT_SM)

    Lcd.setTextColor(GRAY, bg)
    Lcd.drawString(_clean(left_text), 4, 1)
    
    Lcd.setTextColor(YELLOW, bg)
    Lcd.drawString(_clean(right_text), 230, 1)


def draw_heart_cursor(x, y):
    """Dessine un petit coeur rouge en pixel art."""
    if not Lcd:
        return
    Lcd.fillRect(x + 1, y, 2, 1, HEART_RED)
    Lcd.fillRect(x + 4, y, 2, 1, HEART_RED)
    Lcd.fillRect(x, y + 1, 7, 1, HEART_RED)
    Lcd.fillRect(x, y + 2, 7, 1, HEART_RED)
    Lcd.fillRect(x + 1, y + 3, 5, 1, HEART_RED)
    Lcd.fillRect(x + 2, y + 4, 3, 1, HEART_RED)
    Lcd.fillRect(x + 3, y + 5, 1, 1, HEART_RED)


def _clean(text):
    """Nettoie les chaines pour LovyanGFX."""
    s = str(text or "")
    replacements = [
        ("\xe9", "e"), ("\xe8", "e"), ("\xea", "e"), ("\xeb", "e"),
        ("\xe0", "a"), ("\xe2", "a"), ("\xf9", "u"), ("\xfb", "u"),
        ("\xf4", "o"), ("\xee", "i"), ("\xef", "i"), ("\xe7", "c"),
        ("\xb0", "o"), ("\u2019", "'"), ("\u2013", "-"),
    ]
    for old, new in replacements:
        s = s.replace(old, new)
    return "".join(c for c in s if ord(c) < 128)


def clear_screen(color=BLACK):
    if Lcd:
        Lcd.fillScreen(color)
