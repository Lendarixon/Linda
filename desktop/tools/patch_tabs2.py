# -*- coding: utf-8 -*-
"""Вкладки, второй проход: ввод/загрузка в одной вкладке не отменяют проверку, идущую в другой; файл из проводника открывается в новой вкладке."""
from pathlib import Path
P = Path(__file__).resolve().parents[1] / "web" / "index.html"
t = P.read_text(encoding="utf-8")
if "ownRunning" in t:
    raise SystemExit("already patched")


def sub(old, new):
    global t
    assert old in t, old[:80]
    t = t.replace(old, new, 1)


sub("textInput.addEventListener('input', cancelCheck);", "const ownRunning = () => runningTabId === null || runningTabId === activeTabId;  // проверка из другой вкладки не отменяется вводом в этой\ntextInput.addEventListener('input', () => { if (ownRunning()) cancelCheck(); });")
sub("async function handleFileUpload(file) {\n  cancelCheck();", "async function handleFileUpload(file) {\n  if (ownRunning()) cancelCheck();")
sub("  if (checkCtl) cancelCheck();\n  const myId = ++checkSeq", "  if (checkCtl && !ownRunning()) return;  // идёт проверка в другой вкладке: она одна за раз\n  if (checkCtl) cancelCheck();\n  const myId = ++checkSeq")
sub("    cancelCheck(); textInput.value = data.text; textInput.dispatchEvent(new Event('input'));\n    filePillName.textContent = data.filename;", "    if (textInput.value.trim() || lastResult) newTab();  // файл из проводника не затирает текст, над которым уже работают: открываем новую вкладку\n    cancelCheck(); textInput.value = data.text; textInput.dispatchEvent(new Event('input'));\n    filePillName.textContent = data.filename;")
sub("  checkCtl = null;
  if (sendCancel) postCheckCancel(checkJob).catch(() => {});", "  checkCtl = null;
  runningTabId = null;  // отменённая проверка больше не принадлежит вкладке
  if (sendCancel) postCheckCancel(checkJob).catch(() => {});")
P.write_text(t, encoding="utf-8")
print("ok")
