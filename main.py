#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Редактор файла MT_DEFAULT.txt
- Выпадающие списки: mode, step_index, agc_mode, sql_en
- Ограничение длины name = 8
- page вычисляется автоматически: (номер_строки-1)//10+1
- Скрытые поля: res_*, filter_type, lna_grid, mixer_gr, rf_gain,
  lna_en, ssbtype, pan_wide, page — можно показать кнопкой "👁 Скрытые поля"
- Максимум 50 записей, цветовые группы по 10
- Легенда-подсказка: диапазоны частот (РФ), назначение, модуляция, шаг
- freq отображается с разделением по 3 знака (пробелом), в файл пишется числом
- Множественное выделение и массовая замена значений (кнопка "✏ Массовое…")
"""

import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from collections import OrderedDict

# ---------- Константы ----------
NAME_MAX_LEN = 8
MAX_RECORDS = 50
GROUP_SIZE = 10

# Поля, скрытые по умолчанию в форме (но сохраняемые в файл)
HIDDEN_FIELDS = {
    "res_1", "res_2", "res_3", "res_4", "res_5",
    "filter_type", "lna_grid", "mixer_gr",
    "rf_gain", "lna_en", "ssbtype", "pan_wide",
    "page", "agc_thresh_dB", "agc_gain_dB",
}

GROUP_COLORS = [
    "#E8F0FF", "#EAFBEA", "#FFF6E5",
    "#F5EAFB", "#FFF0F0", "#EAF8FB",
]

MODE_MAP = {0: "USB", 1: "LSB", 2: "AM", 3: "NFM", 4: "WFM"}

# ---------- Описания полей (для подсказок в форме) ----------
FIELD_DESCRIPTIONS = {
    "name":          "Имя ячейки (≤ 8 символов)",
    "page":          "Страница памяти (авто)",
    "freq":          "Частота, Гц",
    "mode":          "Вид модуляции",
    "step_index":    "Шаг перестройки",
    "filter_type":   "Тип фильтра (вероятно лучше не менять)",
    "lna_grid":      "Состояние LNA (вероятно лучше не менять)",
    "mixer_gr":      "Усиление смесителя (вероятно лучше не менять)",
    "agc_mode":      "Режим АРУ",
    "agc_thresh_dB": "Порог АРУ, дБ (вероятно лучше не менять)",
    "agc_gain_dB":   "Усиление АРУ, дБ (вероятно лучше не менять)",
    "rf_gain":       "Усиление ВЧ-тракта (вероятно лучше не менять)",
    "lna_en":        "Включение LNA (вероятно лучше не менять)",
    "ssbtype":       "Тип SSB (вероятно лучше не менять)",
    "pan_wide":      "Ширина панорамы (вероятно лучше не менять)",
    "skip_scan":     "Пропускать при сканировании",
    "sql_en":        "Шумоподавитель",
    "sql_thresh":    "Порог шумоподавителя",
    "res_1":         "Резерв",
    "res_2":         "Резерв",
    "res_3":         "Резерв",
    "res_4":         "Резерв",
    "res_5":         "Резерв",
}

STEP_MAP = {
    2: "1 кГц (LW/MW)",
    3: "2.5 кГц (КВ)",
    7: "12.5 кГц (УКВ)",
    8: "50 кГц (FM)",
    9: "10 кГц (AIR/LW/MW)",
    10: "25 кГц (2m/70cm)",
}
AGC_MAP = {2: "AGC-M", 3: "AGC-S"}
SQL_EN_MAP = {0: "OFF", 1: "ON"}

# ---------- Справочник диапазонов (РФ) ----------
# (диапазон, частоты, назначение, модуляция, шаг)
BAND_GUIDE = [
    # --- ДВ / СВ / КВ вещание и любительские ---
    ("LW (ДВ)",         "148.5 – 283.5 кГц",   "Вещание, дальнее прохождение",             "AM",                  "1 кГц"),
    ("MW (СВ)",         "526.5 – 1606.5 кГц",  "Вещание",                                  "AM",                  "1 кГц (сетка 9 кГц)"),
    ("160 m",           "1.810 – 2.000 МГц",   "Любительский, ночное прохождение",         "LSB, CW",             "1 кГц"),
    ("90 m",            "3.200 – 3.400 МГц",   "Тропическое вещание (в РФ почти не исп.)", "AM",                  "5 кГц"),
    ("80 m",            "3.500 – 3.800 МГц",   "Любительский",                             "LSB, CW",             "1 кГц"),
    ("75 m",            "3.900 – 4.000 МГц",   "Вещание",                                  "AM",                  "5 кГц"),
    ("60 m",            "5.250 – 5.450 МГц",   "Вещание",                                  "AM",                  "5 кГц"),
    ("49 m",            "5.900 – 6.200 МГц",   "Вещание",                                  "AM",                  "5 кГц"),
    ("40 m",            "7.000 – 7.200 МГц",   "Любительский",                             "LSB, CW",             "1 кГц"),
    ("41 m",            "7.200 – 7.450 МГц",   "Вещание",                                  "AM",                  "5 кГц"),
    ("31 m",            "9.400 – 9.900 МГц",   "Вещание",                                  "AM",                  "5 кГц"),
    ("30 m",            "10.100 – 10.150 МГц", "Любительский (вторичная)",                 "CW, USB",             "1 кГц"),
    ("25 m",            "11.600 – 12.100 МГц", "Вещание",                                  "AM",                  "5 кГц"),
    ("22 m",            "13.570 – 13.870 МГц", "Вещание",                                  "AM",                  "5 кГц"),
    ("20 m",            "14.000 – 14.350 МГц", "Любительский",                             "USB, CW",             "1 кГц"),
    ("19 m",            "15.100 – 15.800 МГц", "Вещание",                                  "AM",                  "5 кГц"),
    ("16 m",            "17.480 – 17.900 МГц", "Вещание",                                  "AM",                  "5 кГц"),
    ("17 m",            "18.068 – 18.168 МГц", "Любительский",                             "USB, CW",             "1 кГц"),
    ("15 m",            "21.000 – 21.450 МГц", "Любительский",                             "USB, CW",             "1 кГц"),
    ("13 m",            "21.450 – 21.850 МГц", "Вещание",                                  "AM",                  "5 кГц"),
    ("12 m",            "24.890 – 24.990 МГц", "Любительский",                             "USB, CW",             "1 кГц"),
    ("11 m",            "25.600 – 26.100 МГц", "Вещание / CB (ограниченно в РФ)",          "AM",                  "5 кГц"),

    # --- CB 27 МГц ---
    ("CB (27 МГц)",     "26.965 – 27.405 МГц", "Си-Би, дальнобойщики (27.135 МГц)",        "AM, FM",              "10 кГц"),

    # --- Любительские УКВ ---
    ("10 m",            "28.000 – 29.700 МГц", "Любительский",                             "USB, CW, FM (29.6)",  "1 кГц"),
    ("6 m",             "50.000 – 54.000 МГц", "Любительский (с разрешения)",              "USB, CW, FM",         "2.5 кГц"),
    ("OIRT FM",         "65.8 – 74.0 МГц",     "Вещание OIRT (в РФ почти не используется)", "WFM",                "30/50 кГц"),
    ("VHF FM (CCIR)",   "87.5 – 108.0 МГц",    "Вещание (в РФ: 87.5 – 108)",               "WFM",                 "50 кГц"),

    # --- Авиация ---
    ("AIR",             "118.0 – 137.0 МГц",   "Авиационная связь",                        "AM",                  "25 кГц"),

    # --- Метеоспутники ---
    ("Meteo Sat",       "137.0 – 138.0 МГц",   "Приём метеоспутников (NOAA/Метеор, APT/LRPT)", "NFM",             "25 кГц"),

    # --- Любительские УКВ ---
    ("2 m",             "144.0 – 146.0 МГц",   "Любительский",                             "NFM, USB, CW",        "12.5/25 кГц"),

    # --- Железнодорожная связь ---
    ("RZD",             "151.7125 – 156.0125 МГц", "Железнодорожная радиосвязь (РЖД)",     "NFM",                 "12.5 кГц"),

    # --- Морская и речная связь ---
    ("Marine VHF",      "156.0 – 174.0 МГц",   "Морская подвижная служба (16 канал = 156.8 МГц, 70 канал = 156.525 МГц ЦИВ)", "NFM", "25 кГц"),
    ("River VHF",       "300.0125 – 300.5125 МГц", "Речная связь (бедствие на 300.2 МГц)", "NFM",                 "12.5 кГц"),

    # --- LPD / PMR (безлицензионные) ---
    ("LPD",             "433.075 – 434.775 МГц","Маломощные безлицензионные (LPD)",        "NFM",                 "12.5 кГц"),
    ("70 cm",           "430.0 – 440.0 МГц",   "Любительский",                             "NFM, USB, CW",        "12.5/25 кГц"),
    ("PMR",             "446.00625 – 446.09375 МГц", "Маломощные безлицензионные (PMR)",  "NFM",                 "12.5 кГц"),
]


# ---------- Преобразования mode ----------
def mode_to_label(code):
    return f"{code} — {MODE_MAP[code]}" if code in MODE_MAP else f"{code} — ?"

def mode_from_label(label: str):
    label = label.strip()
    m = re.match(r"^(\d+)\s*—", label)
    if m: return int(m.group(1))
    if label.isdigit(): return int(label)
    for code, name in MODE_MAP.items():
        if label.upper() == name: return code
    return label


# ---------- step_index ----------
def step_to_label(code):
    return f"{code} — {STEP_MAP[code]}" if code in STEP_MAP else f"{code} — ?"

def step_from_label(label: str):
    label = label.strip()
    m = re.match(r"^(\d+)\s*—", label)
    if m: return int(m.group(1))
    if label.isdigit(): return int(label)
    for code, name in STEP_MAP.items():
        if label == name: return code
    return label


# ---------- agc_mode ----------
def agc_to_label(code):
    return f"{code} — {AGC_MAP[code]}" if code in AGC_MAP else f"{code} — ?"

def agc_from_label(label: str):
    label = label.strip()
    m = re.match(r"^(\d+)\s*—", label)
    if m: return int(m.group(1))
    if label.isdigit(): return int(label)
    for code, name in AGC_MAP.items():
        if label.upper() == name.upper(): return code
    return label


# ---------- sql_en ----------
def sqlen_to_label(code):
    return f"{code} — {SQL_EN_MAP[code]}" if code in SQL_EN_MAP else f"{code} — ?"

def sqlen_from_label(label: str):
    label = label.strip()
    m = re.match(r"^(\d+)\s*—", label)
    if m: return int(m.group(1))
    if label.isdigit(): return int(label)
    for code, name in SQL_EN_MAP.items():
        if label.upper() == name.upper(): return code
    return label


# ---------- Форматирование freq ----------
_FREQ_SEPARATORS = (" ", "\u00A0", "\u202F", "\u2009", ",")

def format_int_thousands(n):
    if n is None or isinstance(n, bool):
        return str(n) if n is not None else ""
    try:
        n_int = int(n)
    except (TypeError, ValueError):
        return str(n)
    return f"{n_int:,}".replace(",", " ")

def parse_int_thousands(s):
    if s is None:
        return None
    if isinstance(s, (int, float)) and not isinstance(s, bool):
        return int(s)
    t = str(s).strip()
    for ch in _FREQ_SEPARATORS:
        t = t.replace(ch, "")
    try:
        return int(t)
    except ValueError:
        return s


# ---------- page ----------
def page_for_index(idx: int) -> int:
    return idx // GROUP_SIZE + 1

def apply_pages(records):
    for i, rec in enumerate(records):
        rec["page"] = page_for_index(i)


# ---------- Утилита ----------
def truncate_name(s, limit=NAME_MAX_LEN):
    if s is None: return s
    s = str(s)
    return s if len(s) <= limit else s[:limit]


# ---------- Парсинг / сериализация ----------
OBJ_RE = re.compile(r'\{[^{}]*\}')

def parse_line(line: str) -> OrderedDict:
    rec = OrderedDict()
    for m in OBJ_RE.finditer(line.strip()):
        try:
            d = json.loads(m.group(0))
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка в фрагменте {m.group(0)!r}: {e}")
        if len(d) != 1:
            raise ValueError(f"Ожидался один ключ: {m.group(0)!r}")
        k, v = next(iter(d.items()))
        rec[k] = v
    return rec

def serialize_record(rec: OrderedDict) -> str:
    return "".join(json.dumps({k: v}, ensure_ascii=False, separators=(",", ":"))
                   for k, v in rec.items())

def load_file(path: Path):
    records = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line: continue
            try:
                records.append(parse_line(line))
            except ValueError as e:
                raise ValueError(f"Строка {i}: {e}")
    return records

def save_file(path: Path, records):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(serialize_record(rec))
            f.write("\n")


# ---------- Диалог массового редактирования ----------
class BulkEditDialog(tk.Toplevel):
    """Диалог: выбрать поля и задать новые значения для всех выделенных записей."""

    VISIBLE_ORDER = [
        "name", "freq", "mode", "step_index", "agc_mode",
        "agc_thresh_dB", "agc_gain_dB", "skip_scan",
        "sql_en", "sql_thresh",
    ]
    HIDDEN_ORDER = [
        "page", "filter_type", "lna_grid", "mixer_gr",
        "rf_gain", "lna_en", "ssbtype", "pan_wide",
        "res_1", "res_2", "res_3", "res_4", "res_5",
    ]

    def __init__(self, parent, count, on_apply):
        super().__init__(parent)
        self.title(f"Массовое редактирование ({count} записей)")
        self.geometry("640x620")
        self.transient(parent)
        self.grab_set()

        self.on_apply = on_apply

        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(
            top,
            text=f"Будет изменено записей: {count}.\n"
                 "Отметьте поля, которые нужно заменить, и задайте новые значения.",
        ).pack(anchor="w")

        self.show_hidden = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            top, text="Показывать скрытые поля",
            variable=self.show_hidden, command=self._render,
        ).pack(anchor="w", pady=(6, 0))

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        self._canvas = tk.Canvas(body, borderwidth=0, highlightthickness=0)
        vsb = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._inner = ttk.Frame(self._canvas)
        self._inner_id = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>",
                         lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfigure(self._inner_id, width=e.width))

        self.field_enabled = OrderedDict()
        self.field_value = OrderedDict()
        self.field_widgets = OrderedDict()

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(btns, text="Применить", command=self._on_apply).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Отмена", command=self.destroy).pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Button(btns, text="Ничего не выбрано / Снять всё",
                   command=self._clear_all).pack(side=tk.LEFT)

        self._render()

    def _all_keys(self):
        keys = list(self.VISIBLE_ORDER)
        if self.show_hidden.get():
            keys += self.HIDDEN_ORDER
        return keys

    def _render(self):
        for w in self._inner.winfo_children():
            w.destroy()
        self.field_widgets.clear()

        keys = self._all_keys()
        for row, k in enumerate(keys):
            is_hidden = k in self.HIDDEN_ORDER

            if k not in self.field_enabled:
                self.field_enabled[k] = tk.BooleanVar(value=False)
            if k not in self.field_value:
                self.field_value[k] = tk.StringVar(value="")

            cb = ttk.Checkbutton(self._inner, text="",
                                 variable=self.field_enabled[k])
            cb.grid(row=row, column=0, sticky="w", padx=(0, 4), pady=2)

            lbl_fg = "gray" if is_hidden else "black"
            ttk.Label(self._inner, text=k, width=16, anchor="w",
                      foreground=lbl_fg
                      ).grid(row=row, column=1, sticky="w", padx=(0, 6), pady=2)

            if k == "mode":
                widget = ttk.Combobox(
                    self._inner, textvariable=self.field_value[k], state="readonly",
                    values=[mode_to_label(c) for c in MODE_MAP])
            elif k == "step_index":
                widget = ttk.Combobox(
                    self._inner, textvariable=self.field_value[k], state="readonly",
                    values=[step_to_label(c) for c in STEP_MAP])
            elif k == "agc_mode":
                widget = ttk.Combobox(
                    self._inner, textvariable=self.field_value[k], state="readonly",
                    values=[agc_to_label(c) for c in AGC_MAP])
            elif k == "sql_en":
                widget = ttk.Combobox(
                    self._inner, textvariable=self.field_value[k], state="readonly",
                    values=[sqlen_to_label(c) for c in SQL_EN_MAP])
            elif k == "name":
                widget = ttk.Entry(self._inner, textvariable=self.field_value[k])
                vcmd = (self.register(lambda p: len(p) <= NAME_MAX_LEN), "%P")
                widget.configure(validate="key", validatecommand=vcmd)
            elif k == "freq":
                widget = ttk.Entry(self._inner, textvariable=self.field_value[k])
                vcmd = (self.register(self._validate_freq_input), "%P")
                widget.configure(validate="key", validatecommand=vcmd)
            else:
                widget = ttk.Entry(self._inner, textvariable=self.field_value[k])

            widget.grid(row=row, column=2, sticky="ew", pady=2)
            self.field_widgets[k] = widget

        self._inner.columnconfigure(2, weight=1)

        hint = ttk.Label(
            self._inner,
            text="Будут изменены только отмеченные поля. Пустое значение — ввести пустую строку.\n"
                 "Для mode/step_index/agc_mode/sql_en выберите из списка. "
                 "page всё равно пересчитается автоматически.",
            foreground="gray", wraplength=560, justify="left")
        hint.grid(row=len(keys), column=0, columnspan=3, sticky="w", pady=(8, 0))

    @staticmethod
    def _validate_freq_input(proposed: str):
        if proposed == "":
            return True
        cleaned = proposed
        for ch in _FREQ_SEPARATORS:
            cleaned = cleaned.replace(ch, "")
        if cleaned == "":
            return True
        return cleaned.lstrip("-").isdigit()

    def _clear_all(self):
        for v in self.field_enabled.values():
            v.set(False)

    def _on_apply(self):
        changes = OrderedDict()
        for k in self._all_keys():
            if self.field_enabled[k].get():
                changes[k] = self.field_value[k].get()
        if not changes:
            messagebox.showinfo("Массовое редактирование",
                                "Не отмечено ни одного поля для замены.")
            return
        self.on_apply(changes)
        self.destroy()


# ---------- GUI ----------
class Editor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MT_DEFAULT.txt редактор")
        self.geometry("1520x720")

        self.records = []
        self.path = None
        self.current_index = None
        self._name_counter = None

        self.show_hidden = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)

        ttk.Button(toolbar, text="Открыть", command=self.on_open).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Сохранить", command=self.on_save).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(toolbar, text="Сохранить как…", command=self.on_save_as).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(toolbar, text="Добавить", command=self.on_add).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Дублировать", command=self.on_duplicate).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(toolbar, text="Удалить", command=self.on_delete).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(toolbar, text="Вверх", command=lambda: self.move(-1)).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="Вниз", command=lambda: self.move(+1)).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(toolbar, text="✏ Массовое…", command=self.open_bulk_edit).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="📖 Легенда", command=self.show_legend).pack(side=tk.LEFT, padx=(8, 0))

        self._hidden_btn = ttk.Checkbutton(
            toolbar, text="👁 Скрытые поля",
            variable=self.show_hidden,
            command=self._on_toggle_hidden,
            style="Toolbutton",
        )
        self._hidden_btn.pack(side=tk.LEFT, padx=(8, 0))

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = ttk.Frame(paned)
        paned.add(left, weight=1)

        cols = ("#", "name", "page", "freq", "mode", "step", "agc", "sql", "sql_thresh")
        self.tree = ttk.Treeview(left, columns=cols, show="headings",
                                 selectmode="extended")
        widths = (40, 140, 50, 130, 70, 140, 90, 70, 100)
        headers = ("#", "name", "page", "freq", "mode", "step", "agc", "sql", "sql_thresh")
        for c, h, w in zip(cols, headers, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w")

        for gi, color in enumerate(GROUP_COLORS):
            self.tree.tag_configure(f"group{gi}", background=color)

        vsb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        self.fields_frame = ttk.Frame(right)
        self.fields_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.field_vars = OrderedDict()
        self.field_widgets = OrderedDict()
        self._build_fields_placeholder()

        self.status = tk.StringVar(value="Файл не загружен")
        ttk.Label(self, textvariable=self.status, anchor="w", relief=tk.SUNKEN
                  ).pack(side=tk.BOTTOM, fill=tk.X)

    # --- массовое редактирование ---
    def open_bulk_edit(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Массовое редактирование",
                                "Сначала выделите одну или несколько строк в таблице.\n"
                                "Ctrl+клик — добавить к выделению, Shift+клик — диапазон, "
                                "Ctrl+A — все.")
            return
        indices = sorted(int(i) for i in selected if 0 <= int(i) < len(self.records))
        if not indices:
            messagebox.showinfo("Массовое редактирование", "Выделенные строки пусты.")
            return

        self._commit_editor_to_current()
        BulkEditDialog(self, len(indices),
                       lambda changes, idxs=indices: self._apply_bulk(changes, idxs))

    def _apply_bulk(self, changes: OrderedDict, indices):
        prepared = OrderedDict()
        for k, raw in changes.items():
            sample = self.records[indices[0]].get(k)
            if k == "mode":
                prepared[k] = mode_from_label(raw)
            elif k == "step_index":
                prepared[k] = step_from_label(raw)
            elif k == "agc_mode":
                prepared[k] = agc_from_label(raw)
            elif k == "sql_en":
                prepared[k] = sqlen_from_label(raw)
            elif k == "name":
                prepared[k] = truncate_name(raw)
            elif k == "freq":
                prepared[k] = parse_int_thousands(raw)
            else:
                prepared[k] = self._coerce(raw, sample)

        for idx in indices:
            rec = self.records[idx]
            for k, v in prepared.items():
                rec[k] = v

        apply_pages(self.records)
        self._refresh_list(select_index=self.current_index if self.current_index is not None else None)

        if self.current_index is not None and self.current_index in indices:
            self._load_record_to_editor(self.records[self.current_index])

        self._update_status(f"Массово изменено записей: {len(indices)}; полей: {len(prepared)}")

    # --- переключение показа скрытых полей ---
    def _on_toggle_hidden(self):
        if self.current_index is not None:
            self._commit_editor_to_current()
            self._load_record_to_editor(self.records[self.current_index])
        self._update_status("Режим: показаны скрытые поля"
                            if self.show_hidden.get() else
                            "Режим: скрытые поля спрятаны")

    def show_legend(self):
        win = tk.Toplevel(self)
        win.title("Легенда — диапазоны, модуляция и шаг (РФ)")
        win.geometry("1100x600")
        win.transient(self)

        top = ttk.Frame(win)
        top.pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(top, text="Поиск:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        ttk.Entry(top, textvariable=search_var, width=30).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Label(top, foreground="gray",
                  text="  Основано на регламенте IARU R1 (включает РФ), вещательных сетках "
                       "и Решениях ГКРЧ. Частоты могут отличаться по регионам и разрешениям."
                  ).pack(side=tk.LEFT, padx=(12, 0))

        cols = ("band", "freq", "purpose", "mode", "step")
        headers = ("Диапазон", "Частоты", "Назначение (РФ)", "Модуляция", "Шаг")
        widths = (120, 220, 340, 180, 140)
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c, h, w in zip(cols, headers, widths):
            tree.heading(c, text=h)
            tree.column(c, width=w, anchor="w")
        vsb = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=(0, 6))
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 6))
        tree.tag_configure("even", background="#F7F9FF")
        tree.tag_configure("odd",  background="#FFFFFF")

        def fill(filter_text=""):
            tree.delete(*tree.get_children())
            ft = filter_text.strip().lower()
            for i, row in enumerate(BAND_GUIDE):
                if ft and ft not in " ".join(row).lower():
                    continue
                tree.insert("", "end", values=row,
                            tags=("even" if i % 2 == 0 else "odd",))
        fill()
        search_var.trace_add("write", lambda *_: fill(search_var.get()))
        ttk.Button(win, text="Закрыть", command=win.destroy).pack(side=tk.BOTTOM, pady=(0, 6))

    def _build_fields_placeholder(self):
        for w in self.fields_frame.winfo_children():
            w.destroy()
        ttk.Label(self.fields_frame, text="Выберите запись слева или откройте файл.",
                  foreground="gray").pack(anchor="w")

    def _update_status(self, extra: str = ""):
        base = f"Строк: {len(self.records)}/{MAX_RECORDS}"
        if self.path:
            base += f"   Файл: {self.path}"
        base += f"   |   Скрытые: {'вкл' if self.show_hidden.get() else 'выкл'}"
        if extra:
            base += f"   |   {extra}"
        self.status.set(base)

    def on_open(self):
        path = filedialog.askopenfilename(
            title="Открыть MT_DEFAULT.txt",
            filetypes=[("MT файлы", "*.txt"), ("Все файлы", "*.*")])
        if not path: return
        try:
            recs = load_file(Path(path))
        except Exception as e:
            messagebox.showerror("Ошибка", str(e)); return

        truncated = False
        if len(recs) > MAX_RECORDS:
            truncated = True
            recs = recs[:MAX_RECORDS]
        apply_pages(recs)

        self.path = Path(path)
        self.records = recs
        self.current_index = None
        self._refresh_list()

        extra = ""
        if truncated:
            extra = f"⚠ Загружены первые {MAX_RECORDS} строк (в файле было больше)."
            messagebox.showwarning("Ограничение",
                f"В файле больше {MAX_RECORDS} строк. Загружены первые {MAX_RECORDS}.")
        self._update_status(extra)

    def on_save(self):
        if not self.records:
            messagebox.showinfo("Нет данных", "Нечего сохранять."); return
        if not self.path:
            self.on_save_as(); return
        self._commit_editor_to_current()
        apply_pages(self.records)
        try:
            save_file(self.path, self.records)
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e)); return
        self._update_status(f"Сохранено: {self.path}")

    def on_save_as(self):
        path = filedialog.asksaveasfilename(
            title="Сохранить как", defaultextension=".txt",
            filetypes=[("MT файлы", "*.txt"), ("Все файлы", "*.*")])
        if not path: return
        self.path = Path(path)
        self.on_save()

    def _refresh_list(self, select_index=None):
        selected_before = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())

        existing_iids = set()
        for i, rec in enumerate(self.records):
            iid = str(i)
            existing_iids.add(iid)
            group_idx = (i // GROUP_SIZE) % len(GROUP_COLORS)
            freq_val = rec.get("freq", "")
            freq_disp = (format_int_thousands(freq_val)
                         if isinstance(freq_val, int) else str(freq_val))
            self.tree.insert(
                "", "end", iid=iid,
                values=(i + 1,
                        rec.get("name", ""),
                        rec.get("page", ""),
                        freq_disp,
                        self._mode_display(rec.get("mode")),
                        self._step_display(rec.get("step_index")),
                        self._agc_display(rec.get("agc_mode")),
                        self._sql_display(rec.get("sql_en")),
                        rec.get("sql_thresh", "")),
                tags=(f"group{group_idx}",))

        valid_selection = tuple(i for i in selected_before if i in existing_iids)
        if valid_selection:
            try:
                self.tree.selection_set(valid_selection)
            except tk.TclError:
                pass

        if select_index is not None and 0 <= select_index < len(self.records):
            iid = str(select_index)
            try:
                self.tree.focus(iid)
                self.tree.see(iid)
                if not valid_selection:
                    self.tree.selection_set(iid)
            except tk.TclError:
                pass

    @staticmethod
    def _mode_display(code):
        if code is None: return ""
        if isinstance(code, int) and code in MODE_MAP:
            return f"{MODE_MAP[code]} ({code})"
        return str(code)

    @staticmethod
    def _step_display(code):
        if code is None: return ""
        if isinstance(code, int) and code in STEP_MAP:
            return f"{STEP_MAP[code]} ({code})"
        return str(code)

    @staticmethod
    def _agc_display(code):
        if code is None: return ""
        if isinstance(code, int) and code in AGC_MAP:
            return f"{AGC_MAP[code]} ({code})"
        return str(code)

    @staticmethod
    def _sql_display(code):
        if code is None: return ""
        if isinstance(code, int) and code in SQL_EN_MAP:
            return f"{SQL_EN_MAP[code]} ({code})"
        return str(code)

    def on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel: return
        idx = int(min(int(i) for i in sel))
        if idx == self.current_index: return
        self._commit_editor_to_current()
        self.current_index = idx
        self._load_record_to_editor(self.records[idx])

    def _load_record_to_editor(self, rec: OrderedDict):
        for w in self.fields_frame.winfo_children():
            w.destroy()
        self.field_vars.clear();
        self.field_widgets.clear()
        self._name_counter = None

        raw_name = rec.get("name")
        short_name = truncate_name(raw_name)
        if raw_name is not None and short_name != str(raw_name):
            self._update_status(f"⚠ name обрезано до {NAME_MAX_LEN}: "
                                f"{raw_name!r} → {short_name!r}")

        show_hidden = self.show_hidden.get()

        # столбцы: 0 — имя поля, 1 — виджет, 2 — описание
        self.fields_frame.columnconfigure(1, weight=1)

        row = 0
        for k, v in rec.items():
            if k in HIDDEN_FIELDS and not show_hidden:
                continue

            # имя поля: скрытые — серым, остальные — обычным
            label_fg = "gray" if k in HIDDEN_FIELDS else "black"
            ttk.Label(self.fields_frame, text=k, width=16, anchor="w",
                      foreground=label_fg
                      ).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=2)

            # сам виджет
            if k == "mode":
                var = tk.StringVar(value=mode_to_label(v))
                widget = ttk.Combobox(self.fields_frame, textvariable=var,
                                      state="readonly",
                                      values=[mode_to_label(c) for c in MODE_MAP])
            elif k == "step_index":
                var = tk.StringVar(value=step_to_label(v))
                widget = ttk.Combobox(self.fields_frame, textvariable=var,
                                      state="readonly",
                                      values=[step_to_label(c) for c in STEP_MAP])
            elif k == "agc_mode":
                var = tk.StringVar(value=agc_to_label(v))
                widget = ttk.Combobox(self.fields_frame, textvariable=var,
                                      state="readonly",
                                      values=[agc_to_label(c) for c in AGC_MAP])
            elif k == "sql_en":
                var = tk.StringVar(value=sqlen_to_label(v))
                widget = ttk.Combobox(self.fields_frame, textvariable=var,
                                      state="readonly",
                                      values=[sqlen_to_label(c) for c in SQL_EN_MAP])
            elif k == "name":
                var = tk.StringVar(value=short_name if short_name is not None else "")
                widget = ttk.Entry(self.fields_frame, textvariable=var)
                self._attach_name_validation(widget, var)
            elif k == "freq":
                var = tk.StringVar(value=format_int_thousands(v))
                widget = ttk.Entry(self.fields_frame, textvariable=var)
                self._attach_freq_formatting(widget, var)
            else:
                var = tk.StringVar(value=str(v))
                widget = ttk.Entry(self.fields_frame, textvariable=var)

            widget.grid(row=row, column=1, sticky="ew", pady=2)
            self.field_vars[k] = var
            self.field_widgets[k] = widget

            # описание справа от поля (для скрытых — тоже серым)
            desc_text = FIELD_DESCRIPTIONS.get(k, "")
            desc_fg = "gray" if k in HIDDEN_FIELDS else "#555555"
            ttk.Label(self.fields_frame, text=desc_text, anchor="w",
                      foreground=desc_fg
                      ).grid(row=row, column=2, sticky="w", padx=(10, 0), pady=2)

            row += 1

        # счётчик для name — под ним, во второй колонке
        self._name_counter = ttk.Label(
            self.fields_frame,
            text=self._name_counter_text(self.field_vars.get("name")),
            foreground="gray")
        self._name_counter.grid(row=row, column=1, sticky="w", pady=(4, 0))
        row += 1

        if "name" in self.field_vars:
            self.field_vars["name"].trace_add(
                "write",
                lambda *_: self._name_counter.config(
                    text=self._name_counter_text(self.field_vars["name"])))

        # сводная подсказка внизу формы
        note = ("Серым помечены скрытые поля (режим «👁 Скрытые поля» включён). "
                "page всё равно пересчитывается автоматически."
                if show_hidden else
                "Часть технических полей скрыта. Нажмите «👁 Скрытые поля», чтобы показать их.")
        ttk.Label(self.fields_frame,
                  text="mode: 0 — USB, 1 — LSB, 2 — AM, 3 — NFM, 4 — WFM.  "
                       "step_index: 2, 3, 7, 8, 9, 10.  "
                       "agc_mode: 2 — AGC-M, 3 — AGC-S.  "
                       "sql_en: 0 — OFF, 1 — ON.  "
                       f"name: не более {NAME_MAX_LEN} символов.  "
                       "freq: можно вводить с пробелами или без — сохраняется числом.  "
                       "Для массовой замены: выделите строки (Ctrl/Shift) и нажмите «✏ Массовое…».  "
                       + note,
                  foreground="gray", wraplength=900, justify="left"
                  ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 0))

    @staticmethod
    def _name_counter_text(var):
        if var is None: return ""
        return f"name: {len(var.get())}/{NAME_MAX_LEN}"

    def _attach_name_validation(self, widget, var):
        def on_validate(proposed: str):
            if len(proposed) > NAME_MAX_LEN:
                widget.bell(); return False
            return True
        vcmd = (self.register(on_validate), "%P")
        widget.configure(validate="key", validatecommand=vcmd)

    def _attach_freq_formatting(self, widget, var):
        def on_validate(proposed: str):
            if proposed == "":
                return True
            cleaned = proposed
            for ch in _FREQ_SEPARATORS:
                cleaned = cleaned.replace(ch, "")
            if cleaned == "":
                return True
            return cleaned.lstrip("-").isdigit()

        vcmd = (self.register(on_validate), "%P")
        widget.configure(validate="key", validatecommand=vcmd)

        def reformat(event=None):
            raw = var.get()
            parsed = parse_int_thousands(raw)
            if not isinstance(parsed, int):
                return
            new_text = format_int_thousands(parsed)
            if new_text == raw:
                return
            try:
                cur = widget.index(tk.INSERT)
            except tk.TclError:
                cur = len(raw)
            digits_before = sum(1 for ch in raw[:cur] if ch.isdigit())
            var.set(new_text)
            count = 0
            new_cur = len(new_text)
            for i, ch in enumerate(new_text):
                if ch.isdigit():
                    count += 1
                if count == digits_before:
                    new_cur = i + 1
                    break
            widget.icursor(new_cur)

        widget.bind("<FocusOut>", reformat)
        widget.bind("<Return>", reformat)

    def _commit_editor_to_current(self):
        if self.current_index is None: return
        old = self.records[self.current_index]
        new = OrderedDict(old)
        for k, var in self.field_vars.items():
            raw = var.get()
            orig = old.get(k)
            if k == "mode":          new[k] = mode_from_label(raw)
            elif k == "step_index":  new[k] = step_from_label(raw)
            elif k == "agc_mode":    new[k] = agc_from_label(raw)
            elif k == "sql_en":      new[k] = sqlen_from_label(raw)
            elif k == "name":        new[k] = truncate_name(raw)
            elif k == "freq":        new[k] = parse_int_thousands(raw)
            else:                    new[k] = self._coerce(raw, orig)
        new["page"] = page_for_index(self.current_index)
        self.records[self.current_index] = new

        freq_val = new.get("freq", "")
        freq_disp = (format_int_thousands(freq_val)
                     if isinstance(freq_val, int) else str(freq_val))
        gi = (self.current_index // GROUP_SIZE) % len(GROUP_COLORS)
        self.tree.item(str(self.current_index),
                       values=(self.current_index + 1,
                               new.get("name", ""),
                               new.get("page", ""),
                               freq_disp,
                               self._mode_display(new.get("mode")),
                               self._step_display(new.get("step_index")),
                               self._agc_display(new.get("agc_mode")),
                               self._sql_display(new.get("sql_en")),
                               new.get("sql_thresh", "")),
                       tags=(f"group{gi}",))

    @staticmethod
    def _coerce(raw: str, original):
        if isinstance(original, bool):
            return raw.strip().lower() in ("1", "true", "yes", "on")
        if isinstance(original, int):
            try: return int(raw)
            except ValueError: return raw
        if isinstance(original, float):
            try: return float(raw)
            except ValueError: return raw
        return raw

    def _check_limit(self) -> bool:
        if len(self.records) >= MAX_RECORDS:
            self._update_status(f"⚠ Достигнут лимит {MAX_RECORDS} строк")
            messagebox.showwarning("Лимит", f"Нельзя добавить больше {MAX_RECORDS} строк.")
            return False
        return True

    def on_add(self):
        if not self._check_limit(): return
        if not self.records:
            base = OrderedDict([
                ("name", ""), ("page", 1), ("freq", 1000000), ("mode", 1),
                ("step_index", 3), ("filter_type", 1), ("lna_grid", 0),
                ("mixer_gr", 0), ("agc_mode", 2), ("agc_thresh_dB", 75),
                ("agc_gain_dB", 20), ("rf_gain", 4), ("lna_en", 0),
                ("ssbtype", 0), ("pan_wide", 1), ("skip_scan", 0),
                ("sql_en", 0), ("sql_thresh", -120),
                ("res_1", 0), ("res_2", 0), ("res_3", 0), ("res_4", 0), ("res_5", 0),
            ])
            new = OrderedDict(base)
        else:
            idx = self.current_index if self.current_index is not None else len(self.records) - 1
            new = OrderedDict(self.records[idx])
            new["name"] = truncate_name((str(new.get("name", "")) + " (new)").strip())
        self._commit_editor_to_current()
        self.records.append(new)
        apply_pages(self.records)
        self._refresh_list(select_index=len(self.records) - 1)
        self.current_index = None
        self.on_select()
        self._update_status("Добавлена запись")

    def on_duplicate(self):
        if self.current_index is None: return
        if not self._check_limit(): return
        self._commit_editor_to_current()
        new = OrderedDict(self.records[self.current_index])
        new["name"] = truncate_name(str(new.get("name", "")) + " (copy)")
        self.records.insert(self.current_index + 1, new)
        apply_pages(self.records)
        self._refresh_list(select_index=self.current_index + 1)
        self.current_index = None
        self.on_select()
        self._update_status("Запись дублирована")

    def on_delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        if len(sel) > 1:
            if not messagebox.askyesno("Удалить",
                                       f"Удалить {len(sel)} записей?"):
                return
            idxs = sorted((int(i) for i in sel), reverse=True)
            for i in idxs:
                if 0 <= i < len(self.records):
                    del self.records[i]
            self.current_index = None
            apply_pages(self.records)
            self._refresh_list(select_index=min(idxs[-1], len(self.records) - 1)
                               if self.records else None)
            if self.records:
                self.tree.selection_set(str(min(idxs[-1], len(self.records) - 1)))
                self.on_select()
            else:
                self._build_fields_placeholder()
            self._update_status(f"Удалено записей: {len(sel)}")
            return
        if not messagebox.askyesno("Удалить", "Удалить выбранную запись?"): return
        idx = int(sel[0])
        del self.records[idx]
        apply_pages(self.records)
        self.current_index = None
        self._refresh_list(select_index=min(idx, len(self.records) - 1) if self.records else None)
        if self.records: self.on_select()
        else: self._build_fields_placeholder()
        self._update_status("Запись удалена")

    def move(self, delta: int):
        if self.current_index is None: return
        i = self.current_index
        j = i + delta
        if not (0 <= j < len(self.records)): return
        self._commit_editor_to_current()
        self.records[i], self.records[j] = self.records[j], self.records[i]
        apply_pages(self.records)
        self._refresh_list(select_index=j)
        self.current_index = None
        self.on_select()


if __name__ == "__main__":
    Editor().mainloop()