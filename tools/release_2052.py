# -*- coding: utf-8 -*-
"""Сборка выпуска 2.0.5.2 (новый фирменный стиль Metro: логотип, иконка exe/установщика/Store) - всё локально, без публикации.
Модели не менялись (1.3.4). Логика сборки - из release_2051.py; сверху: файлы бренда в assets, иконка в ресурсах exe, плитки Store.
    python tools/release_2052.py bump | build | manifest
Публикация - tools/publish_2052.py."""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import release_2051 as r  # noqa: E402

BRAND = r.DESK / "Linda_brand_metro"
r.VER, r.STORE_VER = "2.0.5.2", "2.0.5002.0"
r.BUILD = r.DESK / "Linda_build_2052"
r.URL = f"https://github.com/Lendarixon/Linda/releases/download/v{r.VER}/Linda-Setup.exe"
r.CHANGED = []
r.ENTRY = {"version": r.VER, "date": "2026-10-10",
 "title": {"ru": "Linda: новые названия и логотип", "en": "Linda: new names and logo", "pl": "Linda: nowe nazwy i logo"},
 "notes": {
  "ru": "• Linda — теперь общее имя продукта. Полный ансамбль Linda-Pro называется Linda Assay, быстрая версия Linda-Pro Lite — Linda Loupe.\n• Модели, вердикты, настройки и ключи лицензий не изменились, ключи работают как прежде.\n• Новый логотип в стиле Metro: плитка с тремя строками текста, кусок средней подсвечен — как разметка ИИ в самом приложении. Новая иконка приложения, установщика и меню «Пуск».\n• Логотип в шапке приложения подстраивается под светлую и тёмную тему.",
  "en": "• Linda is now the name of the product. The full ensemble Linda-Pro is now called Linda Assay, the fast version Linda-Pro Lite is Linda Loupe.\n• Models, verdicts, settings and licence keys are unchanged; keys work as before.\n• New Metro-style logo: a tile with three lines of text, part of the middle one highlighted, just like the AI marking in the app. New icon for the app, the installer and the Start menu.\n• The logo in the app header follows the light/dark theme.",
  "pl": "• Linda to teraz nazwa produktu. Pełny zespół Linda-Pro nazywa się teraz Linda Assay, szybka wersja Linda-Pro Lite — Linda Loupe.\n• Modele, werdykty, ustawienia i klucze licencyjne bez zmian; klucze działają jak dotąd.\n• Nowe logo w stylu Metro: kafelek z trzema wierszami tekstu, fragment środkowego podświetlony — tak jak oznaczanie AI w aplikacji. Nowa ikona aplikacji, instalatora i menu Start.\n• Logo w nagłówku aplikacji dopasowuje się do jasnego/ciemnego motywu."}}
_tree, _sh = r.tree, r.sh


def tree(dst: Path):
    _tree(dst)
    a = dst / "_internal" / "assets"
    for p in (ROOT / "assets").iterdir():
        if p.is_file():
            shutil.copy2(p, a / p.name)


def set_icon(exe: Path):
    """Иконка в ресурсах exe PyInstaller: ресурсы меняются только в PE-части, архив (оверлей) дописывается обратно байт в байт."""
    import pefile
    from PyInstaller import config
    from PyInstaller.utils.win32.icon import CopyIcons
    config.CONF.setdefault("workpath", str(r.BUILD / "pyi_work"))
    (r.BUILD / "pyi_work").mkdir(parents=True, exist_ok=True)
    data = exe.read_bytes()
    pe = pefile.PE(data=data, fast_load=True)
    end = pe.get_overlay_data_start_offset()
    pe.close()
    assert end, "no overlay - not a PyInstaller onedir exe?"
    tmp = exe.with_suffix(".pe.tmp")
    tmp.write_bytes(data[:end])
    CopyIcons(str(tmp), str(ROOT / "assets" / "linda.ico"))
    exe.write_bytes(tmp.read_bytes() + data[end:])
    tmp.unlink()
    print("icon set:", exe, len(data), "->", exe.stat().st_size)


def sh(cmd, **kw):
    if isinstance(cmd, list) and "makeappx" in str(cmd[0]).lower():
        store = Path(cmd[cmd.index("/d") + 1])
        for p in (BRAND / "store_Assets").iterdir():
            shutil.copy2(p, store / "Assets" / p.name)
    _sh(cmd, **kw)
    if isinstance(cmd, list) and any(str(c).endswith("repack_exe.py") for c in cmd):
        set_icon(Path(cmd[3]))


r.tree, r.sh = tree, sh

if __name__ == "__main__":
    {"bump": r.bump, "build": r.build, "manifest": r.manifest}[sys.argv[1]]()
