
import math
import os
import shutil
import sqlite3
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from PIL import Image, ImageTk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'clash_royale.db'
CARD_IMAGE_DIR = BASE_DIR / 'clash-royale-card-elixir'
LOGO_PATH = BASE_DIR / 'design_photo' / 'logo.png'
BANNER_PATH = BASE_DIR / 'design_photo' / 'banner.png'

RARITY_ORDER = {
    'common': 0,
    'rare': 1,
    'epic': 2,
    'legendary': 3,
    'champion': 4,
    'funny': 5,
}
TYPE_ORDER = {'Troop': 0, 'Spell': 1, 'Building': 2}
PROPERTY_LABELS = {
    'win_conditions': 'Win Conditions',
    'spells': 'Spells',
    'buildings': 'Buildings',
    'mini_tanks': 'Mini Tanks',
    'damage_units': 'Damage Units',
    'Funny': 'Funny',
}
PROPERTY_ORDER = list(PROPERTY_LABELS.values())

FILTER_OPTIONS = ['All', 'Troop', 'Spell', 'Building']
RARITY_OPTIONS = ['All', 'common', 'rare', 'epic', 'legendary', 'champion', 'funny']
SORT_OPTIONS = ['Name', 'Elixir', 'Rarity', 'Arena']

PLACEHOLDER_TEXT = 'No image'

# Soft, eye-comfortable palette for the wiki-style interface
APP_BG = '#f4f7fb'
SURFACE = '#ffffff'
SURFACE_ALT = '#f8fbfe'
BORDER = '#d9e3ee'
TEXT = '#102030'
SUBTEXT = '#5f6f82'
ACCENT = '#6e8fb2'
ACCENT_SOFT = '#e4eef8'
GOOD = '#2f855a'
WARN = '#b7791f'
BAD = '#b45309'


def ensure_db_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS categories ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'name TEXT NOT NULL, '
        'directory TEXT NOT NULL)'
    )
    cur.execute(
        'CREATE TABLE IF NOT EXISTS images ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'filename TEXT, '
        'elixir TEXT, '
        'arena TEXT, '
        'type TEXT, '
        'rarity TEXT, '
        'category_id INTEGER)'
    )
    cur.execute(
        'CREATE TABLE IF NOT EXISTS profile_cards ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'name TEXT, '
        'rarity TEXT, '
        'elixir INTEGER, '
        'card_type TEXT, '
        'arena TEXT, '
        'description TEXT, '
        'hitpoints INTEGER, '
        'damage INTEGER, '
        'card_range INTEGER, '
        'stun_duration REAL, '
        'shield TEXT, '
        'movement_speed TEXT, '
        'radius REAL, '
        'image_path TEXT, '
        'property TEXT)'
    )
    conn.commit()
    conn.close()


def normalize_numeric_text(value):
    if value is None:
        return ''
    value = str(value).strip()
    return value


def safe_int(value, label):
    value = normalize_numeric_text(value)
    if value == '':
        raise ValueError(label)
    return int(float(value))


def safe_float(value, label):
    value = normalize_numeric_text(value)
    if value == '':
        raise ValueError(label)
    return float(value)


def pretty_arena(arena):
    arena = normalize_numeric_text(arena)
    if arena == '':
        return 'Unknown'
    if arena == '?':
        return 'Arena ?'
    if arena.lower().startswith('arena'):
        return arena
    return f'Arena {arena}'


def pretty_property(value):
    return PROPERTY_LABELS.get(value, value if value else 'Unknown')


def pretty_title(value):
    if value is None:
        return 'Unknown'
    text = str(value).replace('_', ' ').strip()
    return text.title()


def build_image_path(filename):
    if not filename:
        return None
    filename = os.path.basename(str(filename))
    candidates = [
        CARD_IMAGE_DIR / filename,
        BASE_DIR / filename,
        Path(filename),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(CARD_IMAGE_DIR / filename)


def ensure_file_inside_cards(file_path):
    file_path = Path(file_path)
    CARD_IMAGE_DIR.mkdir(exist_ok=True)
    target = CARD_IMAGE_DIR / file_path.name
    if file_path.resolve() != target.resolve():
        shutil.copy2(file_path, target)
    return target.name


class ClashPediaApp:
    def __init__(self):
        ensure_db_schema()

        self.window = ttk.Window(themename='litera')
        self.window.title('ClashPedia')
        self.window.geometry('1500x920')
        self.window.minsize(1280, 800)
        self.window.configure(bg=APP_BG)

        self.cards = self.load_cards()
        self.cards_by_file = {
            os.path.basename(card.get('image_path') or ''): card for card in self.cards
        }
        self.decks = {f'Deck {i + 1}': [] for i in range(10)}
        self.results = {f'Result_{i + 1}': [] for i in range(10)}

        self._thumb_cache = {}
        self._image_refs = []

        self.nav_buttons = {}
        self.active_view = None
        self.current_card_filter = 'All'
        self.current_sort = 'Name'
        self.current_search = tk.StringVar(value='')

        self.build_shell()
        self.show_view('Home')

    def load_cards(self):
        if not DB_PATH.exists():
            return []

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            rows = cur.execute('SELECT * FROM profile_cards').fetchall()
        except sqlite3.Error:
            rows = []
        conn.close()

        cards = []
        for row in rows:
            card = dict(row)
            filename = os.path.basename(str(card.get('image_path') or ''))
            card['filename'] = filename
            card['full_image_path'] = build_image_path(filename)
            cards.append(card)

        cards.sort(key=lambda c: str(c.get('name') or '').lower())
        return cards

    def refresh_cards(self):
        self.cards = self.load_cards()
        self.cards_by_file = {
            os.path.basename(card.get('image_path') or ''): card for card in self.cards
        }

    def build_shell(self):

        root = self.window

        top = tk.Frame(root, bg='#eef4fa', height=92, highlightbackground=BORDER, highlightthickness=1)
        top.pack(side=TOP, fill=X)
        top.pack_propagate(False)

        left_brand = tk.Frame(top, bg='#eef4fa')
        left_brand.pack(side=LEFT, fill=Y, padx=18, pady=12)

        logo_img = self.load_photo(LOGO_PATH, (70, 70))
        if logo_img is not None:
            logo = tk.Label(left_brand, image=logo_img, bg='#eef4fa')
            logo.image = logo_img
            logo.pack(side=LEFT, padx=(0, 12))
        text_box = tk.Frame(left_brand, bg='#eef4fa')
        text_box.pack(side=LEFT)
        tk.Label(
            text_box,
            text='ClashPedia',
            fg=TEXT,
            bg='#eef4fa',
            font=('Segoe UI', 22, 'bold'),
        ).pack(anchor='w')
        tk.Label(
            text_box,
            text='Clash Royale encyclopedia • cards • decks • profiles',
            fg=SUBTEXT,
            bg='#eef4fa',
            font=('Segoe UI', 10),
        ).pack(anchor='w')

        hero_hint = tk.Frame(top, bg='#eef4fa')
        hero_hint.pack(side=RIGHT, padx=18, pady=18)
        tk.Label(
            hero_hint,
            text='Wiki-style card browser',
            fg=TEXT,
            bg=ACCENT_SOFT,
            font=('Segoe UI', 11, 'bold'),
            padx=12,
            pady=6,
        ).pack()

        body = tk.Frame(root, bg=APP_BG)
        body.pack(fill=BOTH, expand=True)

        sidebar = tk.Frame(body, bg='#fbfdff', width=240, bd=0, highlightthickness=1, highlightbackground=BORDER)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)

        self.content = tk.Frame(body, bg=APP_BG)
        self.content.pack(side=LEFT, fill=BOTH, expand=True)

        tk.Label(
            sidebar,
            text='Navigation',
            bg='#fbfdff',
            fg=TEXT,
            font=('Segoe UI', 11, 'bold'),
            padx=16,
            pady=14,
        ).pack(anchor='w')

        items = [
            ('Home', 'Home'),
            ('Cards', 'Cards'),
            ('Deck Builder', 'Decks'),
            ('Profile Maker', 'Profile'),
        ]
        for label, view in items:
            btn = tk.Button(
                sidebar,
                text=label,
                relief='flat',
                bd=0,
                anchor='w',
                padx=16,
                pady=14,
                font=('Segoe UI', 11),
                bg='#fbfdff',
                fg=TEXT,
                activebackground=ACCENT_SOFT,
                activeforeground=TEXT,
                command=lambda v=view: self.show_view(v),
            )
            btn.pack(fill=X, padx=10, pady=4)
            self.nav_buttons[view] = btn

        footer = tk.Frame(sidebar, bg='#fbfdff')
        footer.pack(side=BOTTOM, fill=X, padx=16, pady=18)
        tk.Label(
            footer,
            text='Clash Royale Wiki inspired layout',
            bg='#fbfdff',
            fg=SUBTEXT,
            wraplength=190,
            justify='left',
            font=('Segoe UI', 9),
        ).pack(anchor='w')

    def set_active_nav(self, active_view):
        for view, btn in self.nav_buttons.items():
            if view == active_view:
                btn.configure(bg='#dbeafe', fg='#0f172a')
            else:
                btn.configure(bg='#f8fafc', fg='#0f172a')

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_view(self, view):
        self.active_view = view
        self.set_active_nav(view)
        self.clear_content()

        if view == 'Home':
            self.render_home()
        elif view == 'Cards':
            self.render_cards_page()
        elif view == 'Decks':
            self.render_deck_builder_page()
        elif view == 'Profile':
            self.render_profile_maker_page()

    def load_photo(self, path, size=(96, 96)):
        if path is None:
            return None
        path = Path(path)
        if not path.exists():
            return None
        key = (str(path), size)
        cached = self._thumb_cache.get(key)
        if cached is not None:
            return cached
        try:
            image = Image.open(path).convert('RGBA')
            image.thumbnail(size, Image.LANCZOS)
            canvas = Image.new('RGBA', size, (255, 255, 255, 0))
            x = (size[0] - image.width) // 2
            y = (size[1] - image.height) // 2
            canvas.paste(image, (x, y), image)
            photo = ImageTk.PhotoImage(canvas)
            self._thumb_cache[key] = photo
            return photo
        except Exception:
            return None

    def card_tile(self, parent, card, on_click=None, compact=False):

        frame = tk.Frame(
            parent,
            bg=SURFACE,
            bd=1,
            relief='solid',
            highlightthickness=0,
            width=188 if compact else 220,
            height=compact and 250 or 290,
        )
        frame.pack_propagate(False)
        if on_click:
            frame.configure(cursor='hand2')
            frame.bind('<Button-1>', lambda e: on_click(card) if on_click else None)

        image_path = card.get('full_image_path')
        if image_path and Path(image_path).exists():
            size = (98, 132) if compact else (126, 168)
            photo = self.load_photo(image_path, size)
            if photo is not None:
                img = tk.Label(frame, image=photo, bg=SURFACE)
                img.image = photo
                img.pack(padx=10, pady=(10, 6))
                img.bind('<Button-1>', lambda e: on_click(card) if on_click else None)
                self._image_refs.append(photo)
        else:
            placeholder = tk.Frame(frame, width=126 if not compact else 98, height=132 if compact else 168, bg='#edf3f8', bd=0)
            placeholder.pack(padx=10, pady=(10, 6))
            placeholder.pack_propagate(False)
            tk.Label(
                placeholder,
                text=PLACEHOLDER_TEXT,
                bg='#edf3f8',
                fg=SUBTEXT,
                wraplength=90,
                justify='center',
                font=('Segoe UI', 9),
            ).pack(expand=True)

        name = card.get('name') or 'Unknown'
        tk.Label(
            frame,
            text=name,
            bg=SURFACE,
            fg=TEXT,
            font=('Segoe UI', 10, 'bold'),
            wraplength=160 if compact else 190,
            justify='center',
        ).pack(fill=X, padx=8)

        meta = f"{card.get('card_type', '')} • {card.get('rarity', '')}"
        tk.Label(
            frame,
            text=meta.strip(' •'),
            bg=SURFACE,
            fg=SUBTEXT,
            font=('Segoe UI', 8),
        ).pack(fill=X, padx=8, pady=(2, 0))

        elixir = card.get('elixir')
        if elixir not in (None, ''):
            badge = tk.Label(
                frame,
                text=f'{elixir} elixir',
                bg=ACCENT_SOFT,
                fg=TEXT,
                font=('Segoe UI', 8, 'bold'),
                padx=8,
                pady=2,
            )
            badge.pack(pady=(6, 8))

        if on_click:
            for child in frame.winfo_children():
                child.bind('<Button-1>', lambda e: on_click(card))

        return frame

    def card_image_for_detail(self, card):
        path = card.get('full_image_path')
        if path and Path(path).exists():
            return self.load_photo(path, (170, 228))
        return None

    def render_home(self):
        page = ScrolledFrame(self.content, autohide=True, padding=16)
        page.pack(fill=BOTH, expand=True)

        hero = tk.Frame(page, bg=SURFACE, bd=1, relief='solid')
        hero.pack(fill=X, pady=(0, 16))
        hero_left = tk.Frame(hero, bg=SURFACE)
        hero_left.pack(side=LEFT, fill=BOTH, expand=True, padx=24, pady=22)

        tk.Label(
            hero_left,
            text='ClashPedia',
            bg=SURFACE,
            fg='#0f172a',
            font=('Segoe UI', 28, 'bold'),
        ).pack(anchor='w')
        tk.Label(
            hero_left,
            text='A cleaner Clash Royale encyclopedia for browsing cards, checking deck balance, and making profiles.',
            bg=SURFACE,
            fg='#475569',
            font=('Segoe UI', 12),
            wraplength=760,
            justify='left',
        ).pack(anchor='w', pady=(8, 0))
        tk.Label(
            hero_left,
            text='Cards are organized like a wiki: by type, rarity, elixir, and arena.',
            bg=SURFACE,
            fg='#1d4ed8',
            font=('Segoe UI', 10, 'bold'),
        ).pack(anchor='w', pady=(10, 0))

        hero_stats = tk.Frame(hero, bg='#eff6ff', bd=0)
        hero_stats.pack(side=RIGHT, fill=Y, padx=18, pady=18)
        stats = [
            ('Cards', len(self.cards)),
            ('Deck slots', 8),
            ('Deck sets', 10),
            ('Properties', len(PROPERTY_ORDER)),
        ]
        for label, value in stats:
            box = tk.Frame(hero_stats, bg=SURFACE, bd=1, relief='solid')
            box.pack(fill=X, pady=6)
            tk.Label(box, text=str(value), bg=SURFACE, fg='#0f172a', font=('Segoe UI', 18, 'bold')).pack(pady=(8, 0))
            tk.Label(box, text=label, bg=SURFACE, fg='#64748b', font=('Segoe UI', 9)).pack(pady=(0, 8))

        section = tk.Frame(page, bg=SURFACE, bd=1, relief='solid')
        section.pack(fill=X, pady=(0, 16))
        tk.Label(
            section,
            text='What this app matches from the real Clash Royale wiki',
            bg=SURFACE,
            fg='#0f172a',
            font=('Segoe UI', 14, 'bold'),
        ).pack(anchor='w', padx=18, pady=(14, 8))

        bullets = (
            '• Card browsing grouped by troop, spell, and building types.\n'
            '• Card details with name, rarity, elixir, arena, property, and description.\n'
            '• Battle decks with a clear 8-card limit and deck evaluation.\n'
            '• A profile maker for adding new cards with the same database structure.'
        )
        tk.Label(
            section,
            text=bullets,
            bg=SURFACE,
            fg='#334155',
            justify='left',
            font=('Segoe UI', 11),
            padx=18,
            pady=10,
        ).pack(anchor='w')

        preview = tk.Frame(page, bg=SURFACE, bd=1, relief='solid')
        preview.pack(fill=X)
        tk.Label(
            preview,
            text='Featured categories',
            bg=SURFACE,
            fg='#0f172a',
            font=('Segoe UI', 14, 'bold'),
        ).pack(anchor='w', padx=18, pady=(14, 6))

        row = tk.Frame(preview, bg=SURFACE)
        row.pack(fill=X, padx=18, pady=(0, 18))
        for label, subtitle in [
            ('Troop Cards', 'Units deployed onto the battlefield'),
            ('Spell Cards', 'Direct damage and control'),
            ('Building Cards', 'Defensive structures'),
            ('Battle Decks', '8-card deck builder'),
        ]:
            tile = tk.Frame(row, bg='#f8fafc', bd=1, relief='solid')
            tile.pack(side=LEFT, expand=True, fill=BOTH, padx=6)
            tk.Label(tile, text=label, bg='#f8fafc', fg='#0f172a', font=('Segoe UI', 11, 'bold')).pack(anchor='w', padx=12, pady=(12, 4))
            tk.Label(tile, text=subtitle, bg='#f8fafc', fg='#64748b', wraplength=220, justify='left').pack(anchor='w', padx=12, pady=(0, 12))

    def filtered_cards(self, search_text='', card_type='All', rarity='All'):
        cards = list(self.cards)
        text = search_text.strip().lower()
        if text:
            cards = [
                c for c in cards
                if text in str(c.get('name', '')).lower()
                or text in str(c.get('property', '')).lower()
                or text in str(c.get('rarity', '')).lower()
                or text in str(c.get('card_type', '')).lower()
            ]
        if card_type != 'All':
            cards = [c for c in cards if c.get('card_type') == card_type]
        if rarity != 'All':
            cards = [c for c in cards if c.get('rarity') == rarity]
        return self.sort_cards(cards)

    def sort_cards(self, cards):
        sort_key = self.current_sort

        def arena_value(card):
            arena = str(card.get('arena', '')).strip()
            if arena == '?':
                return 999
            try:
                return int(arena)
            except ValueError:
                return 999

        if sort_key == 'Elixir':
            return sorted(cards, key=lambda c: (int(c.get('elixir') or 999), str(c.get('name') or '').lower()))
        if sort_key == 'Rarity':
            return sorted(cards, key=lambda c: (RARITY_ORDER.get(str(c.get('rarity') or '').lower(), 99), str(c.get('name') or '').lower()))
        if sort_key == 'Arena':
            return sorted(cards, key=lambda c: (arena_value(c), str(c.get('name') or '').lower()))
        return sorted(cards, key=lambda c: str(c.get('name') or '').lower())

    def render_cards_page(self):

        outer = ScrolledFrame(self.content, autohide=True, padding=16)
        outer.pack(fill=BOTH, expand=True)

        header = tk.Frame(outer, bg=SURFACE, bd=1, relief='solid')
        header.pack(fill=X)
        tk.Label(header, text='Cards', bg=SURFACE, fg=TEXT, font=('Segoe UI', 20, 'bold')).pack(anchor='w', padx=18, pady=(16, 4))
        tk.Label(
            header,
            text='Browse the card database with wiki-style filters and a live detail panel.',
            bg=SURFACE,
            fg=SUBTEXT,
            font=('Segoe UI', 10),
        ).pack(anchor='w', padx=18, pady=(0, 14))

        controls = tk.Frame(outer, bg=SURFACE, bd=1, relief='solid')
        controls.pack(fill=X, pady=16)

        search_row = tk.Frame(controls, bg=SURFACE)
        search_row.pack(fill=X, padx=18, pady=(16, 10))

        tk.Label(search_row, text='Search', bg=SURFACE, fg=TEXT, font=('Segoe UI', 10, 'bold')).pack(side=LEFT, padx=(0, 10))
        search_entry = ttk.Entry(search_row, textvariable=self.current_search, width=36)
        search_entry.pack(side=LEFT, padx=(0, 16))
        search_entry.focus_set()

        type_var = tk.StringVar(value='All')
        rarity_var = tk.StringVar(value='All')

        sort_var = tk.StringVar(value=self.current_sort)
        sort_box = ttk.Combobox(search_row, values=SORT_OPTIONS, textvariable=sort_var, state='readonly', width=16)
        sort_box.pack(side=RIGHT)
        tk.Label(search_row, text='Sort by', bg=SURFACE, fg=TEXT, font=('Segoe UI', 10, 'bold')).pack(side=RIGHT, padx=(0, 10))

        filter_row = tk.Frame(controls, bg=SURFACE)
        filter_row.pack(fill=X, padx=18, pady=(0, 16))

        tk.Label(filter_row, text='Type', bg=SURFACE, fg=TEXT, font=('Segoe UI', 10, 'bold')).pack(side=LEFT, padx=(0, 10))
        type_buttons = {}
        for label in FILTER_OPTIONS:
            btn = tk.Button(
                filter_row,
                text=label,
                relief='flat',
                padx=12,
                pady=6,
                bg=ACCENT_SOFT if label == 'All' else '#f3f7fb',
                fg=TEXT,
                activebackground='#d3e5f6',
                command=lambda v=label: set_type(v),
            )
            btn.pack(side=LEFT, padx=4)
            type_buttons[label] = btn

        tk.Label(filter_row, text='Rarity', bg=SURFACE, fg=TEXT, font=('Segoe UI', 10, 'bold')).pack(side=LEFT, padx=(18, 10))
        rarity_buttons = {}
        for label in RARITY_OPTIONS:
            btn = tk.Button(
                filter_row,
                text=label.title() if label != 'All' else 'All',
                relief='flat',
                padx=12,
                pady=6,
                bg=ACCENT_SOFT if label == 'All' else '#f3f7fb',
                fg=TEXT,
                activebackground='#d3e5f6',
                command=lambda v=label: set_rarity(v),
            )
            btn.pack(side=LEFT, padx=4)
            rarity_buttons[label] = btn

        body = tk.Frame(outer, bg=APP_BG)
        body.pack(fill=BOTH, expand=True)

        catalog_box = tk.Frame(body, bg=SURFACE, bd=1, relief='solid')
        catalog_box.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 12))
        detail_box = tk.Frame(body, bg=SURFACE, bd=1, relief='solid', width=430)
        detail_box.pack(side=RIGHT, fill=Y)
        detail_box.pack_propagate(False)

        tk.Label(catalog_box, text='Card catalog', bg=SURFACE, fg=TEXT, font=('Segoe UI', 13, 'bold')).pack(anchor='w', padx=16, pady=(14, 8))
        catalog_scroll = ScrolledFrame(catalog_box, autohide=True, padding=12)
        catalog_scroll.pack(fill=BOTH, expand=True)

        tk.Label(detail_box, text='Card details', bg=SURFACE, fg=TEXT, font=('Segoe UI', 15, 'bold')).pack(anchor='w', padx=16, pady=(16, 8))
        detail_scroll = ScrolledFrame(detail_box, autohide=True, padding=0)
        detail_scroll.pack(fill=BOTH, expand=True, padx=16, pady=(0, 16))
        detail_content = tk.Frame(detail_scroll, bg=SURFACE)
        detail_content.pack(fill=BOTH, expand=True)

        detail_title = tk.Label(detail_content, text='Select a card', bg=SURFACE, fg=TEXT, font=('Segoe UI', 16, 'bold'))
        detail_title.pack(anchor='w', pady=(0, 10))

        detail_image_label = tk.Label(detail_content, bg=SURFACE)
        detail_image_label.pack(anchor='center', pady=(0, 12))

        detail_meta = tk.Frame(detail_content, bg=SURFACE)
        detail_meta.pack(fill=X, pady=(0, 10))

        detail_desc_title = tk.Label(detail_content, text='Description', bg=SURFACE, fg=TEXT, font=('Segoe UI', 11, 'bold'))
        detail_desc_title.pack(anchor='w', pady=(8, 4))
        detail_desc = tk.Label(detail_content, bg=SURFACE, fg='#334155', justify='left', wraplength=360, font=('Segoe UI', 10))
        detail_desc.pack(anchor='w')

        detail_stats_box = tk.Frame(detail_content, bg=SURFACE)
        detail_stats_box.pack(fill=X, pady=(10, 0))

        def clear_detail_meta():
            for child in detail_meta.winfo_children():
                child.destroy()
            for child in detail_stats_box.winfo_children():
                child.destroy()

        def add_pill(parent, text, bg='#eef5fb'):
            pill = tk.Label(parent, text=text, bg=bg, fg=TEXT, font=('Segoe UI', 9, 'bold'), padx=10, pady=4)
            pill.pack(side=LEFT, padx=(0, 8), pady=4)
            return pill

        def show_detail(card):
            detail_title.configure(text=card.get('name') or 'Unknown')
            clear_detail_meta()

            photo = self.card_image_for_detail(card)
            if photo is not None:
                detail_image_label.configure(image=photo, text='')
                detail_image_label.image = photo
                self._image_refs.append(photo)
            else:
                detail_image_label.configure(image='', text=PLACEHOLDER_TEXT, fg=SUBTEXT)

            add_pill(detail_meta, f"Rarity: {pretty_title(card.get('rarity'))}")
            add_pill(detail_meta, f"Type: {card.get('card_type') or 'Unknown'}")
            add_pill(detail_meta, f"Elixir: {card.get('elixir') or 'Unknown'}", bg=ACCENT_SOFT)
            add_pill(detail_meta, f"Arena: {pretty_arena(card.get('arena'))}")

            detail_desc.configure(
                text=str(card.get('description') or 'No description available.').strip().replace('“', '"').replace('”', '"')
            )

            stats = []
            if card.get('hitpoints') not in (None, ''):
                stats.append(('Hitpoints', card.get('hitpoints')))
            if card.get('damage') not in (None, ''):
                stats.append(('Damage', card.get('damage')))
            if card.get('card_range') not in (None, ''):
                stats.append(('Range', card.get('card_range')))
            if card.get('stun_duration') not in (None, ''):
                stats.append(('Stun', card.get('stun_duration')))
            if card.get('shield') not in (None, '', '-'):
                stats.append(('Shield', card.get('shield')))
            if card.get('movement_speed') not in (None, '', '-'):
                stats.append(('Movement', card.get('movement_speed')))
            if card.get('radius') not in (None, '', '-'):
                stats.append(('Radius', card.get('radius')))

            if stats:
                tk.Label(detail_stats_box, text='Stats', bg=SURFACE, fg=TEXT, font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 8))
                grid = tk.Frame(detail_stats_box, bg=SURFACE)
                grid.pack(fill=X)
                for index, (label, value) in enumerate(stats):
                    chip = tk.Frame(grid, bg='#f3f7fb', bd=1, relief='solid')
                    chip.grid(row=index // 2, column=index % 2, sticky='nsew', padx=4, pady=4)
                    tk.Label(chip, text=label, bg='#f3f7fb', fg=SUBTEXT, font=('Segoe UI', 8)).pack(anchor='w', padx=8, pady=(6, 0))
                    tk.Label(chip, text=str(value), bg='#f3f7fb', fg=TEXT, font=('Segoe UI', 10, 'bold'), wraplength=150, justify='left').pack(anchor='w', padx=8, pady=(0, 6))
                for c in range(2):
                    grid.columnconfigure(c, weight=1)

        def set_type(value):
            type_var.set(value)
            update_filters()

        def set_rarity(value):
            rarity_var.set(value)
            update_filters()

        def update_button_states():
            for label, btn in type_buttons.items():
                btn.configure(bg=ACCENT_SOFT if type_var.get() == label else '#f3f7fb')
            for label, btn in rarity_buttons.items():
                btn.configure(bg=ACCENT_SOFT if rarity_var.get() == label else '#f3f7fb')

        def render_catalog():
            for widget in catalog_scroll.winfo_children():
                widget.destroy()

            cards = self.filtered_cards(
                search_text=self.current_search.get(),
                card_type=type_var.get(),
                rarity=rarity_var.get(),
            )

            if not cards:
                tk.Label(
                    catalog_scroll,
                    text='No cards found.',
                    bg=SURFACE,
                    fg=SUBTEXT,
                    font=('Segoe UI', 11),
                ).pack(pady=40)
                return

            columns = 3
            for index, card in enumerate(cards):
                tile = self.card_tile(catalog_scroll, card, on_click=show_detail, compact=False)
                r = index // columns
                c = index % columns
                tile.grid(row=r, column=c, padx=10, pady=10, sticky='nsew')

            for c in range(columns):
                catalog_scroll.columnconfigure(c, weight=1)

            show_detail(cards[0])

        def update_filters():
            self.current_sort = sort_var.get()
            update_button_states()
            render_catalog()

        sort_box.bind('<<ComboboxSelected>>', lambda e: update_filters())
        self.current_search.trace_add('write', lambda *args: render_catalog())
        render_catalog()

        def show_detail(card):
            detail_title.configure(text=card.get('name') or 'Unknown')
            for child in detail_content.winfo_children():
                if child is not detail_image_label and child is not detail_text:
                    child.destroy()

            photo = self.card_image_for_detail(card)
            if photo is not None:
                detail_image_label.configure(image=photo)
                detail_image_label.image = photo
                self._image_refs.append(photo)
            else:
                detail_image_label.configure(image='', text=PLACEHOLDER_TEXT)

            lines = [
                f"Rarity: {pretty_title(card.get('rarity'))}",
                f"Type: {card.get('card_type') or 'Unknown'}",
                f"Elixir: {card.get('elixir') or 'Unknown'}",
                f"Arena: {pretty_arena(card.get('arena'))}",
                f"Property: {pretty_property(card.get('property'))}",
                '',
                'Description:',
                str(card.get('description') or 'No description available.').strip().replace('“', '"').replace('”', '"'),
            ]
            stats = []
            if card.get('hitpoints') not in (None, ''):
                stats.append(f"Hitpoints: {card.get('hitpoints')}")
            if card.get('damage') not in (None, ''):
                stats.append(f"Damage: {card.get('damage')}")
            if card.get('card_range') not in (None, ''):
                stats.append(f"Range: {card.get('card_range')}")
            if card.get('stun_duration') not in (None, ''):
                stats.append(f"Stun: {card.get('stun_duration')}")
            if card.get('shield') not in (None, '', '-'):
                stats.append(f"Shield: {card.get('shield')}")
            if card.get('movement_speed') not in (None, '', '-'):
                stats.append(f"Movement: {card.get('movement_speed')}")
            if card.get('radius') not in (None, '', '-'):
                stats.append(f"Radius: {card.get('radius')}")

            if stats:
                lines.extend(['', 'Stats:'] + stats)

            detail_text.configure(text='\n'.join(lines))

        def set_type(value):
            type_var.set(value)
            update_filters()

        def set_rarity(value):
            rarity_var.set(value)
            update_filters()

        def update_button_states():
            for label, btn in type_buttons.items():
                btn.configure(bg='#dbeafe' if type_var.get() == label else '#f8fafc')
            for label, btn in rarity_buttons.items():
                btn.configure(bg='#dbeafe' if rarity_var.get() == label else '#f8fafc')

        def render_catalog():
            for widget in catalog_scroll.winfo_children():
                widget.destroy()

            cards = self.filtered_cards(
                search_text=self.current_search.get(),
                card_type=type_var.get(),
                rarity=rarity_var.get(),
            )

            if not cards:
                tk.Label(
                    catalog_scroll,
                    text='No cards found.',
                    bg=SURFACE,
                    fg='#64748b',
                    font=('Segoe UI', 11),
                ).pack(pady=40)
                return

            columns = 4
            for index, card in enumerate(cards):
                tile = self.card_tile(catalog_scroll, card, on_click=show_detail, compact=True)
                r = index // columns
                c = index % columns
                tile.grid(row=r, column=c, padx=8, pady=8, sticky='nsew')

            for c in range(columns):
                catalog_scroll.columnconfigure(c, weight=1)

            show_detail(cards[0])

        def update_filters():
            self.current_sort = sort_var.get()
            update_button_states()
            render_catalog()

        sort_box.bind('<<ComboboxSelected>>', lambda e: update_filters())
        self.current_search.trace_add('write', lambda *args: render_catalog())
        render_catalog()


    def build_deck_preview(self, parent, cards, compact=True):
        for widget in parent.winfo_children():
            widget.destroy()

        preview_wrap = tk.Frame(parent, bg=SURFACE)
        preview_wrap.pack(fill=BOTH, expand=True)

        slots = cards[:8]
        for index in range(8):
            row = index // 4
            col = index % 4
            slot = tk.Frame(
                preview_wrap,
                bg='#f8fafc',
                bd=1,
                relief='solid',
                width=80,
                height=112,
            )
            slot.grid(row=row, column=col, padx=4, pady=4, sticky='nsew')
            slot.pack_propagate(False)

            if index < len(slots):
                card = slots[index]
                photo = self.load_photo(card.get('full_image_path'), (58, 78)) if card.get('full_image_path') else None
                if photo is not None:
                    label = tk.Label(slot, image=photo, bg='#f8fafc')
                    label.image = photo
                    label.pack(pady=(5, 0))
                    self._image_refs.append(photo)
                else:
                    tk.Label(slot, text=PLACEHOLDER_TEXT, bg='#f8fafc', fg='#64748b', wraplength=68, justify='center', font=('Segoe UI', 7)).pack(expand=True)
                tk.Label(slot, text=str(card.get('name') or ''), bg='#f8fafc', fg='#0f172a', wraplength=62, justify='center', font=('Segoe UI', 7, 'bold')).pack(pady=(0, 4))
            else:
                tk.Label(slot, text=f'Slot {index + 1}', bg='#f8fafc', fg='#94a3b8', font=('Segoe UI', 8)).pack(expand=True)

        for col in range(4):
            preview_wrap.columnconfigure(col, weight=1)

    def render_deck_builder_page(self):

        page = ScrolledFrame(self.content, autohide=True, padding=16)
        page.pack(fill=BOTH, expand=True)

        header = tk.Frame(page, bg=SURFACE, bd=1, relief='solid')
        header.pack(fill=X)
        tk.Label(header, text='Deck Builder', bg=SURFACE, fg=TEXT, font=('Segoe UI', 20, 'bold')).pack(anchor='w', padx=18, pady=(16, 4))
        tk.Label(
            header,
            text='Click a deck block to open the editor, then add cards from the catalog.',
            bg=SURFACE,
            fg=SUBTEXT,
            font=('Segoe UI', 10),
        ).pack(anchor='w', padx=18, pady=(0, 14))

        info = tk.Frame(page, bg='#eef5fb', bd=1, relief='solid')
        info.pack(fill=X, pady=16)
        tk.Label(
            info,
            text='How to build a deck: click the deck block, browse cards, click cards to add them, click cards in the tray to remove them, then save.',
            bg='#eef5fb',
            fg=TEXT,
            font=('Segoe UI', 10, 'bold'),
            wraplength=1200,
            justify='left',
            padx=16,
            pady=12,
        ).pack(anchor='w')

        gallery = tk.Frame(page, bg=SURFACE, bd=1, relief='solid')
        gallery.pack(fill=BOTH, expand=True)

        top_bar = tk.Frame(gallery, bg=SURFACE)
        top_bar.pack(fill=X, padx=16, pady=(14, 8))
        tk.Label(top_bar, text='Saved deck slots', bg=SURFACE, fg=TEXT, font=('Segoe UI', 13, 'bold')).pack(side=LEFT)
        tk.Label(top_bar, text='8 cards each', bg=SURFACE, fg=SUBTEXT, font=('Segoe UI', 9)).pack(side=RIGHT)

        deck_grid = tk.Frame(gallery, bg=SURFACE)
        deck_grid.pack(fill=BOTH, expand=True, padx=10, pady=(0, 12))

        for index in range(10):
            deck_name = f'Deck {index + 1}'
            deck_cards = list(self.decks.get(deck_name, []))
            breakdown = self.deck_breakdown(deck_cards)

            card = tk.Frame(deck_grid, bg='#fbfdff', bd=1, relief='solid', width=390, height=320, highlightthickness=1, highlightbackground=BORDER)
            card.grid(row=index // 2, column=index % 2, padx=10, pady=10, sticky='nsew')
            card.pack_propagate(False)

            open_editor = lambda n=deck_name: self.open_deck_editor(n)
            card.bind('<Button-1>', lambda e, n=deck_name: self.open_deck_editor(n))
            for child in card.winfo_children():
                child.bind('<Button-1>', lambda e, n=deck_name: self.open_deck_editor(n))

            title_btn = tk.Button(
                card,
                text=deck_name + '\nClick to edit',
                command=open_editor,
                relief='flat',
                bg=ACCENT_SOFT,
                fg=TEXT,
                activebackground='#d3e5f6',
                font=('Segoe UI', 14, 'bold'),
                padx=12,
                pady=12,
                justify='left',
                anchor='w',
                wraplength=300,
            )
            title_btn.pack(fill=X, padx=12, pady=(12, 8))

            stats_row = tk.Frame(card, bg='#fbfdff')
            stats_row.pack(fill=X, padx=12)
            stat_items = [
                ('Cards', f'{len(deck_cards)}/8'),
                ('Avg elixir', f"{breakdown['avg']:.1f}"),
                ('Eval', self.deck_balance_label(deck_cards)),
            ]
            for label, value in stat_items:
                box = tk.Frame(stats_row, bg=SURFACE, bd=1, relief='solid')
                box.pack(side=LEFT, expand=True, fill=BOTH, padx=4)
                tk.Label(box, text=label, bg=SURFACE, fg=SUBTEXT, font=('Segoe UI', 8)).pack(anchor='w', padx=8, pady=(6, 0))
                tk.Label(box, text=value, bg=SURFACE, fg=TEXT, font=('Segoe UI', 10, 'bold'), wraplength=110, justify='left').pack(anchor='w', padx=8, pady=(0, 6))

            preview = tk.Frame(card, bg='#fbfdff')
            preview.pack(fill=X, padx=12, pady=(10, 0))
            self.build_deck_preview(preview, deck_cards)

            note_text = ' • '.join(breakdown['notes']) if breakdown['notes'] else 'Ready for battle'
            tk.Label(card, text=note_text, bg='#fbfdff', fg=SUBTEXT, font=('Segoe UI', 9), wraplength=340, justify='left').pack(anchor='w', padx=12, pady=(8, 10))

            action_row = tk.Frame(card, bg='#fbfdff')
            action_row.pack(fill=X, padx=12, pady=(0, 12))
            ttk.Button(action_row, text='Edit', bootstyle='primary', command=open_editor).pack(side=LEFT)
            ttk.Button(action_row, text='Analyze', bootstyle='secondary', command=lambda n=deck_name: self.open_result_page(n)).pack(side=LEFT, padx=8)

        for c in range(2):
            deck_grid.columnconfigure(c, weight=1)

    def average_elixir(self, cards):
        values = []
        for card in cards:
            try:
                values.append(float(card.get('elixir') or 0))
            except (TypeError, ValueError):
                continue
        if not values:
            return 0.0
        return sum(values) / len(values)

    def deck_breakdown(self, cards):
        counts = {
            'Troop': 0,
            'Spell': 0,
            'Building': 0,
            'Win Conditions': 0,
            'Spells': 0,
            'Buildings': 0,
            'Mini Tanks': 0,
            'Damage Units': 0,
            'Funny': 0,
        }
        for card in cards:
            card_type = str(card.get('card_type') or '').title()
            if card_type in counts:
                counts[card_type] += 1

            prop = pretty_property(card.get('property'))
            if prop in counts:
                counts[prop] += 1

        avg = self.average_elixir(cards)

        notes = []
        verdict = 'Needs cards'
        if not cards:
            notes.append('Add cards to begin')
        else:
            if len(cards) < 8:
                notes.append(f'{8 - len(cards)} slot(s) open')
            if counts['Win Conditions'] < 1:
                notes.append('Add a win condition')
            if counts['Spells'] < 1:
                notes.append('Add at least one spell')
            if counts['Buildings'] > 2:
                notes.append('Too many buildings')
            if not notes and len(cards) == 8:
                notes.append('Balanced mix of cards')
            if len(cards) == 8 and 3.0 <= avg <= 4.5 and counts['Win Conditions'] >= 1 and counts['Spells'] >= 1:
                verdict = 'Balanced'
            elif len(cards) == 8:
                verdict = 'Playable'
            else:
                verdict = 'Incomplete'

        return {
            'avg': avg,
            'counts': counts,
            'verdict': verdict,
            'notes': notes,
        }

    def deck_balance_label(self, cards):
        breakdown = self.deck_breakdown(cards)
        verdict = breakdown['verdict']
        if verdict == 'Balanced':
            return 'Balanced deck'
        if verdict == 'Playable':
            return 'Playable deck'
        if verdict == 'Incomplete':
            return 'Missing cards'
        return 'Needs work'

    def open_result_page(self, deck_name):
        result_window = tk.Toplevel(self.window)
        result_window.title(f'{deck_name} - Deck Analysis')
        result_window.geometry('1120x840')
        result_window.transient(self.window)

        selected = list(self.decks.get(deck_name, []))

        outer = ScrolledFrame(result_window, autohide=True, padding=16)
        outer.pack(fill=BOTH, expand=True)

        header = tk.Frame(outer, bg=SURFACE, bd=1, relief='solid')
        header.pack(fill=X)
        tk.Label(header, text=deck_name, bg=SURFACE, fg='#0f172a', font=('Segoe UI', 20, 'bold')).pack(anchor='w', padx=18, pady=(16, 4))
        tk.Label(header, text='Deck balance summary based on the existing property groups in the database.', bg=SURFACE, fg='#64748b', font=('Segoe UI', 10)).pack(anchor='w', padx=18, pady=(0, 14))

        if not selected:
            empty = tk.Frame(outer, bg=SURFACE, bd=1, relief='solid')
            empty.pack(fill=X, pady=16)
            tk.Label(empty, text='This deck is still empty.', bg=SURFACE, fg='#334155', font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=18, pady=(16, 6))
            tk.Label(empty, text='Open the deck editor and add cards to analyze the deck.', bg=SURFACE, fg='#64748b', font=('Segoe UI', 10)).pack(anchor='w', padx=18, pady=(0, 16))
            return

        categories = {label: [] for label in PROPERTY_ORDER}
        elixirs = []

        for card in selected:
            prop = pretty_property(card.get('property'))
            if prop in categories:
                categories[prop].append(card)
            try:
                elixirs.append(float(card.get('elixir') or 0))
            except (TypeError, ValueError):
                pass

        summary_row = tk.Frame(outer, bg='#eef2f7')
        summary_row.pack(fill=X, pady=16)

        stats = [
            ('Cards', f'{len(selected)}/8'),
            ('Average elixir', f'{self.average_elixir(selected):.1f}' if selected else '0.0'),
            ('Unique properties', str(sum(1 for cards in categories.values() if cards))),
        ]
        for label, value in stats:
            box = tk.Frame(summary_row, bg=SURFACE, bd=1, relief='solid')
            box.pack(side=LEFT, expand=True, fill=BOTH, padx=6)
            tk.Label(box, text=value, bg=SURFACE, fg='#0f172a', font=('Segoe UI', 18, 'bold')).pack(pady=(12, 0))
            tk.Label(box, text=label, bg=SURFACE, fg='#64748b', font=('Segoe UI', 9)).pack(pady=(0, 12))

        evaluation = {
            'Win Conditions': (1, 2),
            'Spells': (1, 3),
            'Buildings': (0, 2),
            'Mini Tanks': (0, 2),
            'Damage Units': (2, 4),
        }

        eval_box = tk.Frame(outer, bg=SURFACE, bd=1, relief='solid')
        eval_box.pack(fill=X, pady=(0, 16))
        tk.Label(eval_box, text='Balance check', bg=SURFACE, fg='#0f172a', font=('Segoe UI', 13, 'bold')).pack(anchor='w', padx=16, pady=(14, 8))

        for label, (min_count, max_count) in evaluation.items():
            count = len(categories.get(label, []))
            status = 'Good' if min_count <= count <= max_count else 'Needs work'
            line = tk.Frame(eval_box, bg=SURFACE)
            line.pack(fill=X, padx=16, pady=4)
            tk.Label(line, text=label, bg=SURFACE, fg='#334155', font=('Segoe UI', 10, 'bold')).pack(side=LEFT)
            tk.Label(line, text=f'{count} cards', bg=SURFACE, fg='#64748b', font=('Segoe UI', 10)).pack(side=LEFT, padx=10)
            tk.Label(line, text=status, bg=SURFACE, fg='#1d4ed8' if status == 'Good' else '#b45309', font=('Segoe UI', 10, 'bold')).pack(side=RIGHT)

        deck_cards = tk.Frame(outer, bg=SURFACE, bd=1, relief='solid')
        deck_cards.pack(fill=BOTH, expand=True)
        tk.Label(deck_cards, text='Deck cards', bg=SURFACE, fg='#0f172a', font=('Segoe UI', 13, 'bold')).pack(anchor='w', padx=16, pady=(14, 8))

        deck_scroll = ScrolledFrame(deck_cards, autohide=True, padding=12)
        deck_scroll.pack(fill=BOTH, expand=True)

        for index, card in enumerate(selected):
            tile = self.card_tile(deck_scroll, card, compact=True)
            tile.grid(row=index // 4, column=index % 4, padx=8, pady=8, sticky='nsew')
        for c in range(4):
            deck_scroll.columnconfigure(c, weight=1)

    def open_deck_editor(self, deck_name):

        editor = tk.Toplevel(self.window)
        editor.title(f'Edit {deck_name}')
        editor.geometry('1520x940')
        editor.transient(self.window)
        editor.grab_set()

        selected = list(self.decks.get(deck_name, []))

        outer = tk.Frame(editor, bg=APP_BG)
        outer.pack(fill=BOTH, expand=True)

        header = tk.Frame(outer, bg=SURFACE, bd=1, relief='solid')
        header.pack(fill=X, padx=16, pady=16)

        tk.Label(header, text=f'Editing {deck_name}', bg=SURFACE, fg=TEXT, font=('Segoe UI', 20, 'bold')).pack(anchor='w', padx=18, pady=(16, 4))
        tk.Label(header, text='Click cards to add them into the deck tray. Click a card in the tray to remove it.', bg=SURFACE, fg=SUBTEXT, font=('Segoe UI', 10)).pack(anchor='w', padx=18, pady=(0, 6))

        deck_info = tk.Frame(header, bg=SURFACE)
        deck_info.pack(fill=X, padx=18, pady=(0, 16))
        count_label = tk.Label(deck_info, text='', bg=SURFACE, fg=TEXT, font=('Segoe UI', 11, 'bold'))
        count_label.pack(side=LEFT)
        avg_label = tk.Label(deck_info, text='', bg=SURFACE, fg=SUBTEXT, font=('Segoe UI', 10))
        avg_label.pack(side=LEFT, padx=14)
        balance_label = tk.Label(deck_info, text='', bg=ACCENT_SOFT, fg=TEXT, font=('Segoe UI', 10, 'bold'), padx=10, pady=4)
        balance_label.pack(side=RIGHT)

        body = tk.Frame(outer, bg=APP_BG)
        body.pack(fill=BOTH, expand=True, padx=16, pady=(0, 16))

        catalog_frame = tk.Frame(body, bg=SURFACE, bd=1, relief='solid')
        catalog_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 12))

        tray_frame = tk.Frame(body, bg=SURFACE, bd=1, relief='solid', width=380)
        tray_frame.pack(side=RIGHT, fill=Y)
        tray_frame.pack_propagate(False)

        tk.Label(tray_frame, text='Deck tray', bg=SURFACE, fg=TEXT, font=('Segoe UI', 13, 'bold')).pack(anchor='w', padx=16, pady=(14, 8))
        tk.Label(tray_frame, text='This is where cards are added. Click a card to remove it.', bg=SURFACE, fg=SUBTEXT, font=('Segoe UI', 10)).pack(anchor='w', padx=16, pady=(0, 10))

        tray_scroll = ScrolledFrame(tray_frame, autohide=True, padding=12)
        tray_scroll.pack(fill=BOTH, expand=True)

        filter_var = tk.StringVar(value='All')
        search_var = tk.StringVar(value='')

        def update_status():
            breakdown = self.deck_breakdown(selected)
            count_label.configure(text=f'{len(selected)}/8 cards')
            avg_label.configure(text=f"Average elixir: {breakdown['avg']:.1f}")
            balance_label.configure(text=self.deck_balance_label(selected))

        def refresh_tray():
            for widget in tray_scroll.winfo_children():
                widget.destroy()

            if not selected:
                tk.Label(tray_scroll, text='No cards added yet.', bg=SURFACE, fg=SUBTEXT, font=('Segoe UI', 10)).pack(pady=18)
                return

            for index, card in enumerate(selected):
                row = tk.Frame(tray_scroll, bg=SURFACE, bd=1, relief='solid')
                row.pack(fill=X, pady=6)
                photo = self.load_photo(card.get('full_image_path'), (64, 86)) if card.get('full_image_path') else None
                if photo is not None:
                    img = tk.Label(row, image=photo, bg=SURFACE)
                    img.image = photo
                    img.pack(side=LEFT, padx=8, pady=8)
                    self._image_refs.append(photo)
                else:
                    tk.Frame(row, width=64, height=86, bg='#edf3f8').pack(side=LEFT, padx=8, pady=8)
                info = tk.Frame(row, bg=SURFACE)
                info.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 8), pady=8)
                tk.Label(info, text=card.get('name') or 'Unknown', bg=SURFACE, fg=TEXT, font=('Segoe UI', 10, 'bold'), wraplength=180, justify='left').pack(anchor='w')
                tk.Label(info, text=f"{card.get('card_type')} • {card.get('elixir')} elixir", bg=SURFACE, fg=SUBTEXT, font=('Segoe UI', 8)).pack(anchor='w', pady=(2, 0))
                remove_btn = tk.Button(
                    row,
                    text='Remove',
                    relief='flat',
                    bg='#fde8e8',
                    fg='#991b1b',
                    activebackground='#fecaca',
                    command=lambda c=card: remove_card(c),
                )
                remove_btn.pack(side=RIGHT, padx=8, pady=16)

        def matches_filters(card):
            text = search_var.get().strip().lower()
            if text:
                if text not in str(card.get('name', '')).lower() and text not in str(card.get('property', '')).lower() and text not in str(card.get('card_type', '')).lower():
                    return False
            if filter_var.get() != 'All' and card.get('card_type') != filter_var.get():
                return False
            return True

        def refresh_catalog():
            for widget in catalog_scroll.winfo_children():
                widget.destroy()

            filtered = [c for c in self.sort_cards(self.cards) if matches_filters(c)]

            if not filtered:
                tk.Label(catalog_scroll, text='No cards found.', bg=SURFACE, fg=SUBTEXT, font=('Segoe UI', 10)).pack(pady=18)
                return

            columns = 4
            for index, card in enumerate(filtered):
                tile = self.card_tile(catalog_scroll, card, on_click=lambda c, card=card: add_card(card), compact=True)
                tile.grid(row=index // columns, column=index % columns, padx=8, pady=8, sticky='nsew')
            for c in range(columns):
                catalog_scroll.columnconfigure(c, weight=1)

        def add_card(card):
            if card in selected:
                messagebox.showwarning('Repeated Card', 'This card is already in the deck.')
                return
            if len(selected) >= 8:
                messagebox.showwarning('Deck Full', 'A deck can only have 8 cards.')
                return
            selected.append(card)
            update_status()
            refresh_tray()

        def remove_card(card):
            if card in selected:
                selected.remove(card)
                update_status()
                refresh_tray()

        def save_deck():
            if len(selected) != 8:
                messagebox.showwarning('Incomplete Deck', 'Choose exactly 8 cards before saving.')
                return
            self.decks[deck_name] = list(selected)
            result_key = f"Result_{deck_name.split(' ')[1]}"
            self.results[result_key] = list(selected)
            self.build_deck_builder_page()
            messagebox.showinfo('Deck Saved', f'{deck_name} has been saved.')

        def clear_deck():
            selected.clear()
            update_status()
            refresh_tray()

        def apply_filters():
            refresh_catalog()

        top_filters = tk.Frame(catalog_frame, bg=SURFACE)
        top_filters.pack(fill=X, padx=16, pady=(14, 10))
        tk.Label(top_filters, text='Catalog filters', bg=SURFACE, fg=TEXT, font=('Segoe UI', 10, 'bold')).pack(side=LEFT, padx=(0, 10))

        for label in FILTER_OPTIONS:
            tk.Button(
                top_filters,
                text=label,
                relief='flat',
                padx=12,
                pady=6,
                bg=ACCENT_SOFT if label == 'All' else '#f3f7fb',
                fg=TEXT,
                activebackground='#d3e5f6',
                command=lambda v=label: (filter_var.set(v), apply_filters()),
            ).pack(side=LEFT, padx=4)

        tk.Label(top_filters, text='Search', bg=SURFACE, fg=TEXT, font=('Segoe UI', 10, 'bold')).pack(side=LEFT, padx=(18, 8))
        ttk.Entry(top_filters, textvariable=search_var, width=28).pack(side=LEFT)

        cat_scroll = ScrolledFrame(catalog_frame, autohide=True, padding=12)
        cat_scroll.pack(fill=BOTH, expand=True)

        catalog_scroll = cat_scroll

        search_var.trace_add('write', lambda *args: refresh_catalog())
        filter_var.trace_add('write', lambda *args: refresh_catalog())

        button_row = tk.Frame(tray_frame, bg=SURFACE)
        button_row.pack(fill=X, padx=16, pady=(0, 16))
        ttk.Button(button_row, text='Save deck', bootstyle='primary', command=save_deck).pack(side=LEFT)
        ttk.Button(button_row, text='Clear', bootstyle='secondary', command=clear_deck).pack(side=LEFT, padx=8)
        ttk.Button(button_row, text='Close', bootstyle='light', command=editor.destroy).pack(side=RIGHT)

        update_status()
        refresh_tray()
        refresh_catalog()

        def update_status():
            count_label.configure(text=f'{len(selected)}/8 cards')
            avg_label.configure(text=f'Average elixir: {self.average_elixir(selected):.1f}' if selected else 'Average elixir: 0.0')

        def refresh_tray():
            for widget in tray_scroll.winfo_children():
                widget.destroy()

            if not selected:
                tk.Label(tray_scroll, text='No cards added yet.', bg=SURFACE, fg='#64748b', font=('Segoe UI', 10)).pack(pady=18)
                return

            for index, card in enumerate(selected):
                row = tk.Frame(tray_scroll, bg=SURFACE, bd=1, relief='solid')
                row.pack(fill=X, pady=6)
                photo = self.load_photo(card.get('full_image_path'), (64, 86)) if card.get('full_image_path') else None
                if photo is not None:
                    img = tk.Label(row, image=photo, bg=SURFACE)
                    img.image = photo
                    img.pack(side=LEFT, padx=8, pady=8)
                    self._image_refs.append(photo)
                else:
                    tk.Frame(row, width=64, height=86, bg='#edf2f7').pack(side=LEFT, padx=8, pady=8)
                info = tk.Frame(row, bg=SURFACE)
                info.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 8), pady=8)
                tk.Label(info, text=card.get('name') or 'Unknown', bg=SURFACE, fg='#0f172a', font=('Segoe UI', 10, 'bold'), wraplength=180, justify='left').pack(anchor='w')
                tk.Label(info, text=f"{card.get('card_type')} • {card.get('elixir')} elixir", bg=SURFACE, fg='#64748b', font=('Segoe UI', 8)).pack(anchor='w', pady=(2, 0))
                remove_btn = tk.Button(
                    row,
                    text='Remove',
                    relief='flat',
                    bg='#fee2e2',
                    fg='#991b1b',
                    activebackground='#fecaca',
                    command=lambda c=card: remove_card(c),
                )
                remove_btn.pack(side=RIGHT, padx=8, pady=16)

        def matches_filters(card):
            text = search_var.get().strip().lower()
            if text:
                if text not in str(card.get('name', '')).lower() and text not in str(card.get('property', '')).lower() and text not in str(card.get('card_type', '')).lower():
                    return False
            if filter_var.get() != 'All' and card.get('card_type') != filter_var.get():
                return False
            return True

        def refresh_catalog():
            for widget in catalog_scroll.winfo_children():
                widget.destroy()

            filtered = [c for c in self.sort_cards(self.cards) if matches_filters(c)]

            if not filtered:
                tk.Label(catalog_scroll, text='No cards found.', bg=SURFACE, fg='#64748b', font=('Segoe UI', 10)).pack(pady=18)
                return

            columns = 5
            for index, card in enumerate(filtered):
                tile = self.card_tile(catalog_scroll, card, on_click=lambda c, card=card: add_card(card), compact=True)
                tile.grid(row=index // columns, column=index % columns, padx=8, pady=8, sticky='nsew')
            for c in range(columns):
                catalog_scroll.columnconfigure(c, weight=1)

        def add_card(card):
            if card in selected:
                messagebox.showwarning('Repeated Card', 'This card is already in the deck.')
                return
            if len(selected) >= 8:
                messagebox.showwarning('Deck Full', 'A deck can only have 8 cards.')
                return
            selected.append(card)
            update_status()
            refresh_tray()

        def remove_card(card):
            if card in selected:
                selected.remove(card)
                update_status()
                refresh_tray()

        def save_deck():
            if len(selected) != 8:
                messagebox.showwarning('Incomplete Deck', 'Choose exactly 8 cards before saving.')
                return
            self.decks[deck_name] = list(selected)
            result_key = f"Result_{deck_name.split(' ')[1]}"
            self.results[result_key] = list(selected)
            self.build_deck_builder_page()
            messagebox.showinfo('Deck Saved', f'{deck_name} has been saved.')

        def clear_deck():
            selected.clear()
            update_status()
            refresh_tray()

        def apply_filters():
            refresh_catalog()

        top_filters = tk.Frame(catalog_frame, bg=SURFACE)
        top_filters.pack(fill=X, padx=16, pady=(14, 10))
        tk.Label(top_filters, text='Catalog filters', bg=SURFACE, fg='#334155', font=('Segoe UI', 10, 'bold')).pack(side=LEFT, padx=(0, 10))

        for label in FILTER_OPTIONS:
            tk.Button(
                top_filters,
                text=label,
                relief='flat',
                padx=12,
                pady=6,
                bg='#dbeafe' if label == 'All' else '#f8fafc',
                fg='#0f172a',
                activebackground='#bfdbfe',
                command=lambda v=label: (filter_var.set(v), apply_filters()),
            ).pack(side=LEFT, padx=4)

        tk.Label(top_filters, text='Search', bg=SURFACE, fg='#334155', font=('Segoe UI', 10, 'bold')).pack(side=LEFT, padx=(18, 8))
        ttk.Entry(top_filters, textvariable=search_var, width=28).pack(side=LEFT)

        cat_scroll = ScrolledFrame(catalog_frame, autohide=True, padding=12)
        cat_scroll.pack(fill=BOTH, expand=True)

        catalog_scroll = cat_scroll

        search_var.trace_add('write', lambda *args: refresh_catalog())
        filter_var.trace_add('write', lambda *args: refresh_catalog())

        button_row = tk.Frame(tray_frame, bg=SURFACE)
        button_row.pack(fill=X, padx=16, pady=(0, 16))
        ttk.Button(button_row, text='Save deck', bootstyle='primary', command=save_deck).pack(side=LEFT)
        ttk.Button(button_row, text='Clear', bootstyle='secondary', command=clear_deck).pack(side=LEFT, padx=8)
        ttk.Button(button_row, text='Close', bootstyle='light', command=editor.destroy).pack(side=RIGHT)

        update_status()
        refresh_tray()
        refresh_catalog()

    def build_deck_builder_page(self):
        # kept as a separate renderer so saving can refresh the dashboard cleanly
        self.show_view('Decks')

    def render_profile_maker_page(self):
        page = ScrolledFrame(self.content, autohide=True, padding=16)
        page.pack(fill=BOTH, expand=True)

        header = tk.Frame(page, bg=SURFACE, bd=1, relief='solid')
        header.pack(fill=X)
        tk.Label(header, text='Profile Maker', bg=SURFACE, fg='#0f172a', font=('Segoe UI', 20, 'bold')).pack(anchor='w', padx=18, pady=(16, 4))
        tk.Label(header, text='Add a new card using the same fields already used by the database.', bg=SURFACE, fg='#64748b', font=('Segoe UI', 10)).pack(anchor='w', padx=18, pady=(0, 14))

        form_box = tk.Frame(page, bg=SURFACE, bd=1, relief='solid')
        form_box.pack(fill=BOTH, expand=True, pady=16)

        tk.Label(form_box, text='Card details', bg=SURFACE, fg='#0f172a', font=('Segoe UI', 13, 'bold')).pack(anchor='w', padx=18, pady=(14, 10))
        form = tk.Frame(form_box, bg=SURFACE)
        form.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        def row(parent, r, label, widget):
            tk.Label(parent, text=label, bg=SURFACE, fg='#334155', font=('Segoe UI', 10, 'bold')).grid(row=r, column=0, sticky='w', padx=(0, 10), pady=8)
            widget.grid(row=r, column=1, sticky='ew', pady=8)

        form.columnconfigure(1, weight=1)

        name_var = tk.StringVar()
        rarity_var = tk.StringVar(value='common')
        elixir_var = tk.StringVar()
        type_var = tk.StringVar(value='Troop')
        arena_var = tk.StringVar()
        property_var = tk.StringVar(value='damage_units')
        hitpoints_var = tk.StringVar()
        damage_var = tk.StringVar()
        range_var = tk.StringVar()
        stun_var = tk.StringVar()
        shield_var = tk.StringVar()
        speed_var = tk.StringVar()
        radius_var = tk.StringVar()
        image_var = tk.StringVar()

        name_entry = ttk.Entry(form, textvariable=name_var)
        rarity_combo = ttk.Combobox(form, textvariable=rarity_var, values=[r for r in RARITY_OPTIONS if r != 'All'], state='readonly')
        elixir_entry = ttk.Entry(form, textvariable=elixir_var)
        type_combo = ttk.Combobox(form, textvariable=type_var, values=['Troop', 'Spell', 'Building'], state='readonly')
        arena_entry = ttk.Entry(form, textvariable=arena_var)
        property_combo = ttk.Combobox(form, textvariable=property_var, values=['win_conditions', 'spells', 'buildings', 'mini_tanks', 'damage_units', 'Funny'], state='readonly')
        description_text = tk.Text(form, height=5, wrap='word')
        hitpoints_entry = ttk.Entry(form, textvariable=hitpoints_var)
        damage_entry = ttk.Entry(form, textvariable=damage_var)
        range_entry = ttk.Entry(form, textvariable=range_var)
        stun_entry = ttk.Entry(form, textvariable=stun_var)
        shield_entry = ttk.Entry(form, textvariable=shield_var)
        speed_entry = ttk.Entry(form, textvariable=speed_var)
        radius_entry = ttk.Entry(form, textvariable=radius_var)
        image_label = tk.Label(form, text='No image selected', bg=SURFACE, fg='#64748b', anchor='w')

        widgets = [
            ('Card name', name_entry),
            ('Rarity', rarity_combo),
            ('Elixir', elixir_entry),
            ('Card type', type_combo),
            ('Arena', arena_entry),
            ('Property', property_combo),
            ('Description', description_text),
            ('Hitpoints', hitpoints_entry),
            ('Damage', damage_entry),
            ('Range', range_entry),
            ('Stun duration', stun_entry),
            ('Shield', shield_entry),
            ('Movement speed', speed_entry),
            ('Radius', radius_entry),
            ('Image', image_label),
        ]

        for idx, (label, widget) in enumerate(widgets):
            row(form, idx, label, widget)

        preview_box = tk.Frame(form, bg='#f8fafc', bd=1, relief='solid', width=180, height=240)
        preview_box.grid(row=0, column=2, rowspan=6, padx=(18, 0), pady=8, sticky='n')
        preview_box.pack_propagate(False)
        preview_label = tk.Label(preview_box, text='Preview', bg='#f8fafc', fg='#64748b')
        preview_label.pack(expand=True)

        def pick_image():
            file_path = filedialog.askopenfilename(
                title='Select card image',
                filetypes=[('Image files', '*.png *.jpg *.jpeg *.webp')],
            )
            if not file_path:
                return
            image_var.set(file_path)
            image_label.configure(text=os.path.basename(file_path))
            photo = self.load_photo(file_path, (140, 190))
            for widget in preview_box.winfo_children():
                widget.destroy()
            if photo is not None:
                img = tk.Label(preview_box, image=photo, bg='#f8fafc')
                img.image = photo
                img.pack(expand=True, pady=6)
                self._image_refs.append(photo)
            else:
                tk.Label(preview_box, text=os.path.basename(file_path), bg='#f8fafc', fg='#64748b', wraplength=150).pack(expand=True)

        def save_card():
            try:
                name = name_var.get().strip()
                rarity = rarity_var.get().strip()
                elixir = safe_int(elixir_var.get(), 'Elixir')
                card_type = type_var.get().strip()
                arena = arena_var.get().strip()
                description = description_text.get('1.0', 'end').strip()
                hitpoints = safe_int(hitpoints_var.get(), 'Hitpoints')
                damage = safe_int(damage_var.get(), 'Damage')
                card_range = safe_int(range_var.get(), 'Range')
                stun_duration = safe_float(stun_var.get(), 'Stun duration')
                shield = shield_var.get().strip()
                movement_speed = speed_var.get().strip()
                radius = safe_float(radius_var.get(), 'Radius')
                property_name = property_var.get().strip()
            except ValueError as exc:
                messagebox.showwarning('Input error', f'Please complete the {exc.args[0]} field with a valid number.')
                return

            if not name or not rarity or not card_type or not arena or not description:
                messagebox.showwarning('Input error', 'Please complete the required fields before saving.')
                return

            image_path = image_var.get().strip()
            if not image_path:
                messagebox.showwarning('Input error', 'Please choose an image for the card.')
                return

            try:
                image_filename = ensure_file_inside_cards(image_path)
            except Exception as exc:
                messagebox.showerror('Image error', f'Could not save the image file.\n{exc}')
                return

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO profile_cards (name, rarity, elixir, card_type, arena, description, hitpoints, damage, card_range, stun_duration, shield, movement_speed, radius, image_path, property) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    name,
                    rarity,
                    elixir,
                    card_type,
                    arena,
                    description,
                    hitpoints,
                    damage,
                    card_range,
                    stun_duration,
                    shield,
                    movement_speed,
                    radius,
                    image_filename,
                    property_name,
                ),
            )
            conn.commit()
            conn.close()

            self.refresh_cards()
            messagebox.showinfo('Saved', 'Card saved successfully.')
            name_var.set('')
            elixir_var.set('')
            arena_var.set('')
            description_text.delete('1.0', 'end')
            hitpoints_var.set('')
            damage_var.set('')
            range_var.set('')
            stun_var.set('')
            shield_var.set('')
            speed_var.set('')
            radius_var.set('')
            image_var.set('')
            image_label.configure(text='No image selected')
            for widget in preview_box.winfo_children():
                widget.destroy()
            tk.Label(preview_box, text='Preview', bg='#f8fafc', fg='#64748b').pack(expand=True)

        actions = tk.Frame(form_box, bg=SURFACE)
        actions.pack(fill=X, padx=18, pady=(0, 18))

        ttk.Button(actions, text='Upload image', bootstyle='secondary', command=pick_image).pack(side=LEFT)
        ttk.Button(actions, text='Save card', bootstyle='primary', command=save_card).pack(side=LEFT, padx=8)

        note = tk.Label(
            form_box,
            text='Tip: use the same names and categories already used by the existing Clash Royale data for the cleanest results.',
            bg=SURFACE,
            fg='#64748b',
            font=('Segoe UI', 9),
        )
        note.pack(anchor='w', padx=18, pady=(0, 16))

    def run(self):
        self.window.mainloop()


if __name__ == '__main__':
    app = ClashPediaApp()
    app.run()
