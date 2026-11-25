import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
strings={
'ru':dict(task_stop='Остановить',task_stopping='Останавливаем…',task_stopped='Обработка остановлена. Исходный текст сохранён.',task_show='Идёт обработка · Показать',task_retry_stop='Не удалось остановить. Повторить',task_busy='Дождитесь завершения или остановите текущую обработку.',task_error='Не удалось выполнить обработку. Попробуйте ещё раз.',rewrite_current='Переписать этот текст',rewrite_open='Открыть редактор текста',rewrite_fragments='Переписать фрагменты здесь'),
'en':dict(task_stop='Stop',task_stopping='Stopping…',task_stopped='Processing stopped. Your original text is preserved.',task_show='Processing · Show',task_retry_stop='Could not stop. Retry',task_busy='Wait for the current task or stop it first.',task_error='Processing failed. Please try again.',rewrite_current='Rewrite this text',rewrite_open='Open text editor',rewrite_fragments='Rewrite selected parts here'),
'pl':dict(task_stop='Zatrzymaj',task_stopping='Zatrzymywanie…',task_stopped='Przetwarzanie zatrzymane. Tekst źródłowy został zachowany.',task_show='Przetwarzanie · Pokaż',task_retry_stop='Nie udało się zatrzymać. Ponów',task_busy='Poczekaj na zakończenie zadania lub najpierw je zatrzymaj.',task_error='Przetwarzanie nie powiodło się. Spróbuj ponownie.',rewrite_current='Przeredaguj ten tekst',rewrite_open='Otwórz edytor tekstu',rewrite_fragments='Przeredaguj fragmenty tutaj')}
for lang,values in strings.items():
 p=ROOT/f'web/i18n/{lang}.json';data=json.loads(p.read_text(encoding='utf-8'));data.update(values)
 # Replace obsolete four-format-only copy in the public format descriptions.
 if lang=='ru':
  data['b_folder_note']='Проверка папки выполняется на этом компьютере. Поддерживаются документы, книги и текстовые файлы; число файлов в папке ограничено.'
 elif lang=='en':data['b_folder_note']='Folders are checked on this computer. Documents, ebooks and text files are supported; the number of files per folder is limited.'
 else:data['b_folder_note']='Foldery są sprawdzane na tym komputerze. Obsługiwane są dokumenty, e-booki i pliki tekstowe; liczba plików w folderze jest ograniczona.'
 p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
exec((ROOT/'tools/sync_web_i18n.py').read_text(encoding='utf-8'))
