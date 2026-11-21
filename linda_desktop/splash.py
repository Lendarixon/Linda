# -*- coding: utf-8 -*-
"""Стартовый сплэш как у Word/Blender: маленькое окно-заставка без рамки
(и без кнопки в панели задач), пока сервер поднимается и модели греются.

Только stdlib (tkinter). Окно живёт в главном потоке: mainloop + опрос
/api/status через after(300). Закрытие — только кодом, когда
startup.phase станет ready/skipped/error. Любая неполадка tkinter
(нет дисплея и т.п.) — молча пропускаем сплэш, старт идёт как раньше.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time


def _frozen_tcl() -> None:
    """В упакованном приложении tcl/tk лежат рядом: _internal/tcl8.6 и tk8.6
    (one-dir на диске) либо во временной распаковке (_MEIPASS, one-file).
    Указать их ДО импорта tkinter, иначе окно не создастся.

    _tkinter.pyd грузится с диска (_internal в sys.path), его tcl86t/tk86t
    Windows-искатель без подсказки не находит: добавляем каталоги через
    add_dll_directory и предзагружаем DLL явно по полному пути."""
    cands: list[str] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cands.append(meipass)
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        cands.append(os.path.join(exe_dir, "_internal"))
        cands.append(exe_dir)
    for base in cands:
        if os.path.isdir(base):
            try:
                os.add_dll_directory(base)
            except Exception:  # noqa: BLE001
                pass
    if os.name == "nt":
        try:
            import ctypes as _ct
            for base in cands:
                for _dll in ("tcl86t.dll", "tk86t.dll"):
                    _p = os.path.join(base, _dll)
                    if os.path.isfile(_p):
                        try:
                            _ct.WinDLL(_p)
                        except Exception:  # noqa: BLE001
                            pass
        except Exception:  # noqa: BLE001
            pass
    for base in cands:
        for var, stem in (("TCL_LIBRARY", "tcl"), ("TK_LIBRARY", "tk")):
            if os.environ.get(var):
                continue
            hit = next((c for c in (os.path.join(base, stem), os.path.join(base, stem + "8.6"),
                                    os.path.join(base, stem, "tcl8.6"),
                                    os.path.join(base, stem, "tk8.6")) if os.path.isdir(c)), None)
            if hit:
                os.environ[var] = hit


_frozen_tcl()

import tkinter as tk
import urllib.request
from tkinter import ttk

from . import config

BG = "#0d0f14"
FG = "#f4f5f7"
MUTED = "#8a91a0"
ACCENT = "#1ba1e2"
ERROR_FG = "#ff6b61"
STRIP_BG = "#101216"
STRIP_FG = "#e8eaee"

WIDTH, HEIGHT = 640, 400  # размер панорамы-гифки из дизайна
STRIP_H = 88
POLL_MS = 300
ANIM_MS = 100  # задержка кадров в гифке дизайна — 10 сантисекунд
MIN_SHOW_S = 2.5  # сплэш виден минимум столько, даже если всё уже готово
OFFLINE_AFTER_S = 12.0
ERROR_HOLD_S = 5.0
LOGO_MAX = 72

TERMINAL = ("ready", "skipped", "error")
DOWNLOAD_ACTIVE = ("checking", "downloading", "verifying", "applying", "finishing")

TEXTS = {
    "ru": {
        "pending": "Запуск Linda…",
        "loading": "Загрузка ваших моделей…",
        "warming": "Прогрев моделей…",
        "offline": "Ожидание локальной службы…",
        "error": "Не удалось подготовить модели",
        "server_error": "Не удалось запустить локальную службу",
        "models_pct": "Загрузка моделей… {pct:.0f}%",
        "models": "Загрузка моделей…",
        "preparing": "Подготовка моделей…",
        "dl_fail": "Не удалось скачать модели: ",
        "version": "Версия",
        "licensed": "Лицензия активна",
        "free": "БЕСПЛАТНО · ДЛЯ ЛИЧНОГО ИСПОЛЬЗОВАНИЯ",
        "tagline": "Детектор ИИ-текста",
    },
    "en": {
        "pending": "Starting Linda…",
        "loading": "Loading your models…",
        "warming": "Warming up models…",
        "offline": "Waiting for local service…",
        "error": "Could not prepare models",
        "server_error": "Could not start local service",
        "models_pct": "Loading models… {pct:.0f}%",
        "models": "Loading models…",
        "preparing": "Preparing models…",
        "dl_fail": "Could not download models: ",
        "version": "Version",
        "licensed": "License active",
        "free": "FREE · FOR PERSONAL USE",
        "tagline": "AI text detector",
    },
    "pl": {
        "pending": "Uruchamianie Lindy…",
        "loading": "Ładowanie modeli…",
        "warming": "Rozgrzewanie modeli…",
        "offline": "Oczekiwanie na usługę lokalną…",
        "error": "Nie udało się przygotować modeli",
        "server_error": "Nie udało się uruchomić usługi lokalnej",
        "models_pct": "Ładowanie modeli… {pct:.0f}%",
        "models": "Ładowanie modeli…",
        "preparing": "Przygotowywanie modeli…",
        "dl_fail": "Nie udało się pobrać modeli: ",
        "version": "Wersja",
        "licensed": "Licencja aktywna",
        "free": "ZA DARMO · DO UŻYTKU OSOBISTEGO",
        "tagline": "Detektor tekstów AI",
    },
}
TAGLINE = "Детектор ИИ-текста"  # как в web/startup.html (ru), только для текстового фолбэка


def _fetch_status(port: int, token: str, timeout: float = 2.5) -> dict:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/status", headers={"x-linda-token": token})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _splash_lang() -> str:
    """Язык сплэша: settings.json, затем installer_choice.json, иначе en."""
    try:
        from . import config as _cfg  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return "en"
    for name in ("settings.json", "installer_choice.json"):
        try:
            lang = json.loads((_cfg.data_dir() / name).read_text(encoding="utf-8")).get("language", "")
        except Exception:  # noqa: BLE001
            continue
        if isinstance(lang, str):
            ll = lang.lower()
            if ll.startswith("ru"):
                return "ru"
            if ll.startswith("pl"):
                return "pl"
            if ll.startswith("en"):
                return "en"
    return "en"


def _splash_bg(lang: str):
    """Случайная панорама: пять иллюстраций детектора и пять Linda Trace."""
    try:
        from . import config as _cfg  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return None
    folder = _cfg.resource_dir() / "assets" / "splash" / "panorama"
    backgrounds = [folder / f"{i:02}.png" for i in range(1, 11)]
    available = [p for p in backgrounds if p.is_file()]
    return random.choice(available) if available else None


def _splash_dots():
    """Летающие точки как в Windows 10 (вариант 0 из дизайна)."""
    try:
        from . import config as _cfg  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return None
    p = _cfg.resource_dir() / "assets" / "splash" / "dots" / "dots.gif"
    try:
        if p.is_file():
            return p
    except Exception:  # noqa: BLE001
        pass
    return None


def _gif_frames(path) -> int:
    """Число кадров гифки: пробуем индексы, пока tkinter не откажет."""
    n = 0
    while n < 400:
        try:
            tk.PhotoImage(file=str(path), format=f"gif -index {n}")
        except Exception:  # noqa: BLE001
            break
        n += 1
    return max(n, 1)


def _describe(state: dict, lang: str = "ru") -> tuple[str, float | None, bool]:
    """Чистая функция: (строка статуса, доля 0..1 или None для пульса, is_error)."""
    t = TEXTS.get(lang, TEXTS["en"])
    startup = state.get("startup") or {}
    phase = startup.get("phase") or "pending"
    if phase == "error":
        err = (startup.get("error") or "").strip()
        text = t["error"] + (f": {err[:120]}" if err else "")
        return text, None, True
    dl = state.get("download") or {}
    dphase = dl.get("phase") or "idle"
    if dphase in DOWNLOAD_ACTIVE:
        try:
            total = float(dl.get("total") or 0)
            done = float(dl.get("done") or 0)
        except (TypeError, ValueError):
            total, done = 0.0, 0.0
        if total > 0:
            pct = min(max(done / total, 0.0), 1.0)
            return t["models_pct"].format(pct=pct * 100), pct, False
        return t["models"], None, False
    return t.get(phase, t["loading"]), None, False


class _Splash:
    def __init__(self, port: int, token: str) -> None:
        self._port = port
        self._token = token
        self.result = "unavailable"
        self._closing = False
        self._first_fail: float | None = None
        self._lang = _splash_lang()
        self._bg_path = _splash_bg(self._lang)
        self._t0 = time.monotonic()

        root = tk.Tk()
        self.root = root
        root.title("Linda")
        root.configure(bg=BG)
        root.overrideredirect(True)  # нет рамки и нет кнопки в панели задач
        # без -topmost: окно можно перекрыть другими и оно не висит над всей системой
        try:
            root.attributes("-topmost", False)
        except Exception:  # noqa: BLE001
            pass
        try:
            root.protocol("WM_DELETE_WINDOW", lambda: None)  # закрытие только кодом
        except Exception:  # noqa: BLE001
            pass
        root.withdraw()
        self._drag_from: tuple[int, int] | None = None
        root.bind("<ButtonPress-1>", self._drag_start)
        root.bind("<B1-Motion>", self._drag_move)

        t = TEXTS.get(self._lang, TEXTS["en"])
        self._t = t
        if self._bg_path:
            self._build_panorama(root, t)
        else:
            self._build_text(root, t)

        root.geometry(f"{WIDTH}x{HEIGHT}")
        root.update_idletasks()
        x = (root.winfo_screenwidth() - WIDTH) // 2
        y = (root.winfo_screenheight() - HEIGHT) // 2
        root.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")
        root.deiconify()
        self._t0 = time.monotonic()
        root.after(POLL_MS, self._poll)

    def _drag_start(self, ev) -> None:
        try:
            self._drag_from = (ev.x_root - self.root.winfo_x(),
                               ev.y_root - self.root.winfo_y())
        except Exception:  # noqa: BLE001
            self._drag_from = None

    def _drag_move(self, ev) -> None:
        if not self._drag_from:
            return
        try:
            self.root.geometry(
                f"+{ev.x_root - self._drag_from[0]}+{ev.y_root - self._drag_from[1]}")
        except Exception:  # noqa: BLE001
            pass

    def _draggable(self, *widgets) -> None:
        for _w in widgets:
            try:
                _w.bind("<ButtonPress-1>", self._drag_start)
                _w.bind("<B1-Motion>", self._drag_move)
            except Exception:  # noqa: BLE001
                pass

    def _build_panorama(self, root, t: dict) -> None:
        """Композиция «Панорама»: чистая иллюстрация и живые надписи."""
        cv = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BG,
                       bd=0, highlightthickness=0)
        cv.place(x=0, y=0, width=WIDTH, height=HEIGHT)
        self._cv = cv
        # Only artwork and scrims are rasterized. Every UI label stays live.
        self._background = tk.PhotoImage(file=str(self._bg_path))
        cv.create_image(0, 0, image=self._background, anchor="nw")

        def _t(x, y, text, font, fill, anchor="nw"):
            sh = cv.create_text(x + 1, y + 1, anchor=anchor, text=text,
                                font=font, fill="#05070a")
            main = cv.create_text(x, y, anchor=anchor, text=text,
                                  font=font, fill=fill)
            self._shadow_of[main] = sh
            return main
        self._shadow_of = {}

        _t(16, 37, "linda", ("Segoe UI Light", -88), FG)
        _t(25, 158, t["tagline"], ("Segoe UI Light", -17), FG)
        self._lic_id = _t(25, 196, t.get("free", ""), ("Segoe UI", -10), ACCENT)
        # Версия и иконка: одна строка, общий центр, без тени.
        # Версия и иконка: одна строка, общий центр, без тени. Иконку рисуем
        # сами по фирменному знаку (в logo_28.png под плиткой подпись, для шапки не годится).
        _brand_cy = 28
        cv.create_text(572, _brand_cy, anchor="e", text=config.APP_VERSION,
                       font=("Segoe UI", -14), fill=FG)
        _tile, _ts = 578, 34
        cv.create_rectangle(_tile, _brand_cy - _ts // 2, _tile + _ts, _brand_cy + (_ts + 1) // 2,
                            fill="#1ba1e2", outline="")
        def _bar(dx, dy, w, h, c):
            cv.create_rectangle(_tile + dx * _ts / 100, _brand_cy - _ts // 2 + dy * _ts / 100,
                                _tile + (dx + w) * _ts / 100, _brand_cy - _ts // 2 + (dy + h) * _ts / 100,
                                fill=c, outline="")
        _bar(14, 24, 72, 12, "#ffffff")
        _bar(14, 44, 32, 12, "#ffffff")
        _bar(52, 44, 34, 12, "#e51400")
        _bar(14, 64, 52, 12, "#ffffff")
        self._model_id = cv.create_text(25, 302, anchor="nw", text="",
                                        font=("Segoe UI", -10), fill=MUTED)
        self._status_id = _t(16, 329, t["pending"], ("Segoe UI", -13), STRIP_FG)
        cv.itemconfigure(self._status_id, width=505)
        cv.itemconfigure(self._shadow_of[self._status_id], width=505)
        self._dots = [cv.create_oval(16, 360, 20, 364,
                                     fill=FG, outline="")
                      for i in range(5)]
        self._dots_t = 0
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:  # noqa: BLE001
            pass
        style.configure("Splash.Horizontal.TProgressbar", troughcolor="#262b33",
                        background=ACCENT, bordercolor="#262b33",
                        lightcolor=ACCENT, darkcolor=ACCENT, borderwidth=0,
                        relief="flat")
        self._bar = ttk.Progressbar(root, mode="determinate", maximum=100,
                                    style="Splash.Horizontal.TProgressbar")
        self._bar.place(x=16, y=386, width=608, height=2)
        self._bar["value"] = 0
        # кнопку пропуска убрали по просьбе владельца: сплэш всегда дожидается готовности
        self._dl_started = False
        self._dl_done = False
        self._draggable(cv)
        root.after(50, self._anim_tick)

    @staticmethod
    def _mix(first: str, second: str, amount: float) -> str:
        a = tuple(int(first[i:i + 2], 16) for i in (1, 3, 5))
        b = tuple(int(second[i:i + 2], 16) for i in (1, 3, 5))
        return "#" + "".join(
            f"{round(x + (y - x) * amount):02x}" for x, y in zip(a, b))

    def _draw_bars(self, cv) -> None:
        """Цветные строки панорамы с приглушением слева (по референсу)."""
        rows = [
            (33, [(9, 116, "r"), (132, 231, "r"),
                  (370, 169, "o"), (545, 79, "g")]),
            (71, [(9, 180, "r"), (195, 254, "r"), (456, 168, "g")]),
            (109, [(9, 149, "r"), (165, 97, "r"), (268, 181, "r"),
                   (456, 132, "g"), (595, 29, "r")]),
            (147, [(9, 84, "g"), (100, 120, "r"),
                   (226, 255, "o"), (488, 136, "r")]),
            (185, [(9, 114, "o"), (130, 133, "r"),
                   (270, 186, "g"), (463, 161, "r")]),
            (223, [(9, 245, "r"), (261, 99, "g"),
                   (367, 132, "o"), (506, 118, "r")]),
            (261, [(9, 198, "g"), (214, 189, "o"), (410, 214, "g")]),
            (299, [(9, 258, "r"), (274, 82, "r"),
                   (361, 174, "r"), (542, 82, "r")]),
            (337, [(9, 192, "r"), (208, 110, "g"), (325, 55, "g")]),
        ]
        colors = {"r": "#bf1708", "o": "#c85a00", "g": "#508916"}
        for row_index, (y, blocks) in enumerate(rows):
            for block_index, (x, width, kind) in enumerate(blocks):
                for offset in range(0, width, 3):
                    px = x + offset
                    if px < 260:
                        strength = 0.97
                    elif px < 420:
                        strength = 0.97 * (1 - (px - 260) / 160)
                    else:
                        strength = 0.0
                    color = self._mix(colors[kind], BG, strength)
                    cv.create_rectangle(px, y, min(px + 3, x + width), y + 27,
                                        fill=color, outline="")
                cursor = x + 9
                right = x + width - 9
                index = 0
                while cursor + 8 < right:
                    length = 10 + (row_index * 13 + block_index * 17 + index * 11) % 35
                    length = min(length, right - cursor)
                    if cursor < 260:
                        strength = 0.97
                    elif cursor < 420:
                        strength = 0.97 * (1 - (cursor - 260) / 160)
                    else:
                        strength = 0.0
                    cv.create_rectangle(cursor, y + 11, cursor + length, y + 15,
                                        fill=self._mix(FG, BG, strength),
                                        outline="")
                    cursor += length + 7
                    index += 1

    def _anim_tick(self) -> None:
        try:
            dots = getattr(self, "_dots", None)
            cv = getattr(self, "_cv", None)
            if dots and cv:
                elapsed = time.monotonic() - self._t0
                for k, _oid in enumerate(dots):
                    try:
                        phase = ((elapsed - k * 0.12) % 3.0) / 2.2
                        visible = phase <= 1.0
                        phase = min(1.0, phase)
                        offset = 430 * (phase * phase * (3 - 2 * phase))
                        cv.coords(_oid, 16 + offset, 360, 20 + offset, 364)
                        cv.itemconfigure(_oid, state="normal" if visible else "hidden")
                    except Exception:  # noqa: BLE001
                        pass
        except Exception:  # noqa: BLE001
            pass
        try:
            self.root.after(30, self._anim_tick)
        except Exception:  # noqa: BLE001
            pass

    def _build_text(self, root, t: dict) -> None:
        """Запасной текстовый сплэш, если гифки нет в бандле."""
        self._fg_ok = MUTED
        frame = tk.Frame(root, bg=BG, padx=28, pady=22)
        frame.pack(fill="both", expand=True)
        self._draggable(frame)

        self._img = None
        try:
            img = tk.PhotoImage(
                file=str(config.resource_dir() / "assets" / "logo_square.png"))
            k = max(img.width(), img.height()) // LOGO_MAX
            if k > 1:
                img = img.subsample(k, k)
            self._img = img  # держать ссылку, иначе картинка пропадёт
            tk.Label(frame, image=img, bg=BG).pack(pady=(2, 0))
        except Exception:  # noqa: BLE001 — без картинки тоже можно стартовать
            pass

        tk.Label(frame, text="linda", font=("Segoe UI", 38),
                 fg=FG, bg=BG).pack()
        tk.Label(frame, text=f"{t['version']} {config.APP_VERSION}", font=("Segoe UI", 10),
                 fg=MUTED, bg=BG).pack()
        tk.Label(frame, text=TAGLINE, font=("Segoe UI", 11),
                 fg=MUTED, bg=BG).pack(pady=(0, 6))

        self._status = tk.Label(frame, text=t["pending"], font=("Segoe UI", 11),
                                fg=MUTED, bg=BG, wraplength=420, justify="center")
        self._status.pack(fill="x", pady=(6, 8))
        self._dl_started = False
        self._dl_done = False

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:  # noqa: BLE001
            pass
        style.configure("Splash.Horizontal.TProgressbar", troughcolor="#22262e",
                        background=ACCENT, borderwidth=0, thickness=10)
        self._bar = ttk.Progressbar(frame, mode="determinate", maximum=100,
                                    style="Splash.Horizontal.TProgressbar")
        self._bar.pack(fill="x")
        self._bar["value"] = 0


    def _set_status(self, text: str, is_error: bool) -> None:
        try:
            cv = getattr(self, "_cv", None)
            if cv is not None and getattr(self, "_status_id", None) is not None:
                cv.itemconfigure(self._status_id, text=text,
                                 fill=ERROR_FG if is_error else STRIP_FG)
                sh = (getattr(self, "_shadow_of", {}) or {}).get(self._status_id)
                if sh is not None:
                    cv.itemconfigure(sh, text=text)
                return
        except Exception:  # noqa: BLE001
            pass
        try:
            self._status.config(text=text, fg=ERROR_FG if is_error else getattr(self, "_fg_ok", MUTED))
        except Exception:  # noqa: BLE001
            pass
    def _skip_show(self) -> None:
        # Кнопка пропуска убрана по просьбе владельца: сплэш всегда дожидается готовности.
        return

    def _skip_hide(self) -> None:
        return

    def _pulse(self) -> None:
        try:
            self._bar["value"] = (float(self._bar["value"]) + 4) % 100
        except Exception:  # noqa: BLE001
            pass

    def _finish(self, result: str) -> None:
        """Закрыть сплэш, но не раньше MIN_SHOW_S с момента показа."""
        if self._closing:
            return
        self._closing = True
        self.result = result
        try:
            wait = MIN_SHOW_S - (time.monotonic() - self._t0)
        except Exception:  # noqa: BLE001
            wait = 0
        if wait > 0:
            try:
                self.root.after(int(wait * 1000), self._destroy)
                return
            except Exception:  # noqa: BLE001
                pass
        self._destroy()

    def _maybe_start_download(self, state: dict) -> None:
        """Первый запуск без моделей: запустить рекомендованный набор автоматически."""
        if self._dl_started:
            return
        if not bool((state.get("settings") or {}).get("auto_models", True)):
            return
        dl = state.get("download") or {}
        if (dl.get("phase") or "idle") != "idle":
            self._dl_started = True
            return
        rec = (state.get("model_sets") or {}).get("recommend") or "lite"
        sets = ["pro"] if rec == "pro" else ["lite"]
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{self._port}/api/models/sets",
                data=json.dumps({"sets": sets}).encode("utf-8"),
                headers={"x-linda-token": self._token, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception:  # noqa: BLE001 — приложение само докачает, сплэш просто ждёт
            pass
        self._dl_started = True

    def _fail(self, text: str) -> None:
        """Красная ошибка на ERROR_HOLD_S секунд, затем закрыть сплэш."""
        if self._closing:
            return
        self._closing = True
        self.result = "error"
        self._set_status(text, True)
        self.root.after(int(ERROR_HOLD_S * 1000), self._destroy)

    def _destroy(self) -> None:
        try:
            for callback in self.root.tk.call("after", "info"):
                self.root.after_cancel(callback)
            self.root.destroy()
        except Exception:  # noqa: BLE001
            pass

    def _update_license_cover(self, state: dict) -> None:
        """Лицензия: зелёная строка; без ключа — синяя «бесплатно»."""
        lbl = getattr(self, "_lic_id", None)
        cv = getattr(self, "_cv", None)
        if lbl is None or cv is None:
            return
        try:
            if (state.get("license") or {}).get("licensed"):
                cv.itemconfigure(lbl, text=self._t.get("licensed", ""),
                                 fill="#8fce62")
            else:
                cv.itemconfigure(lbl, text=self._t.get("free", ""),
                                 fill=ACCENT)
            sh = (getattr(self, "_shadow_of", {}) or {}).get(lbl)
            if sh is not None:
                cv.itemconfigure(sh, text=cv.itemcget(lbl, "text"))
        except Exception:  # noqa: BLE001
            pass

    def _poll(self) -> None:
        if self._closing:
            return
        try:
            state = _fetch_status(self._port, self._token)
        except Exception:  # noqa: BLE001 — сервер ещё не отвечает
            now = time.monotonic()
            if self._first_fail is None:
                self._first_fail = now
            if now - self._first_fail >= OFFLINE_AFTER_S:
                self._fail(self._t["server_error"])
            else:
                self._set_status(self._t["offline"], False)
                self._pulse()
                self.root.after(POLL_MS, self._poll)
            return
        self._first_fail = None
        self._update_license_cover(state)
        phase = (state.get("startup") or {}).get("phase") or "pending"
        models_ready = bool(state.get("models_ready"))
        if phase in TERMINAL:
            if phase == "error":
                self._fail(_describe(state, self._lang)[0])  # красным 5 секунд, дальше окно само покажет
                return
            if models_ready or self._dl_done:
                self._finish(phase)
                return
            # Сервер готов, моделей нет (первый запуск): качаем в сплэше, а не в главном окне.
            self._maybe_start_download(state)
            dl = state.get("download") or {}
            dphase = (dl.get("phase") or "idle")
            if dphase == "error":
                self._skip_show()
                self._set_status("%s%s" % (self._t["dl_fail"], str(dl.get("error") or "")[:150]), True)
                self.root.after(POLL_MS, self._poll)
                return
            self._skip_show()
            text, frac, is_error = _describe(state, self._lang)
            if frac is None and dphase == "idle":
                text, frac = self._t["preparing"], None
            self._set_status(text, is_error)
            if frac is None:
                self._pulse()
            else:
                try:
                    self._bar["value"] = frac * 100
                except Exception:  # noqa: BLE001
                    pass
            self.root.after(POLL_MS, self._poll)
            return
        self._skip_hide()
        text, frac, is_error = _describe(state, self._lang)
        self._set_status(text, is_error)
        if frac is None:
            self._pulse()
        else:
            try:
                self._bar["value"] = frac * 100
            except Exception:  # noqa: BLE001
                pass
        self.root.after(POLL_MS, self._poll)


def show_splash(port: int, token: str) -> str:
    """Показать сплэш и держать, пока сервер/модели не готовы.

    Возвращает 'ready' / 'skipped' / 'error' / 'unavailable' (tkinter недоступен).
    Никогда не бросает исключений.
    """
    def _log(msg: str) -> None:
        try:
            from pathlib import Path as _P  # noqa: PLC0415

            home = None
            try:
                from . import config as _cfg  # noqa: PLC0415

                home = _cfg.data_dir()
            except Exception:  # noqa: BLE001
                import os as _os

                home = _P(_os.path.expandvars(r"%LOCALAPPDATA%\Linda-Pro"))
            (home / "splash_debug.log").write_text(msg + "\n", encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    try:
        splash = _Splash(port, token)
    except Exception as e:  # noqa: BLE001 — нет дисплея: пишем причину и пропускаем сплэш
        import traceback as _tb

        _log("splash init failed: %r\n%s" % (e, _tb.format_exc()))
        return "unavailable"
    try:
        splash.root.mainloop()
    except Exception:  # noqa: BLE001
        try:
            splash.root.destroy()
        except Exception:  # noqa: BLE001
            pass
        return "unavailable"
    return splash.result
