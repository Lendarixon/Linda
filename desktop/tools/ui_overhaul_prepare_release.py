"""Record the UI change in the existing local release notes."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
file=root/'CHANGELOG.json'
data=json.loads(file.read_text(encoding='utf-8'))
prefix={
 'ru':'Новый интерфейс в стиле Windows: постоянное меню, отдельные страницы истории и инструментов, настройки по категориям, понятные подписи и подсказки до анализа. Вставка из буфера больше не запускает проверку автоматически. Добавлены остановка проверки, видимый индикатор фоновой задачи и ошибки рядом с действием. Светлая, тёмная и контрастная темы, RU/EN/PL. ',
 'en':'New Windows-style workspace: permanent navigation, separate history and tool pages, grouped settings, clear labels and guidance before a check. Pasting no longer starts analysis automatically. Added an explicit Stop action, visible background activity and inline errors. Light, dark and contrast themes, RU/EN/PL. ',
 'pl':'Nowy interfejs w stylu Windows: stała nawigacja, osobne strony historii i narzędzi, pogrupowane ustawienia, czytelne etykiety i wskazówki przed sprawdzeniem. Wklejanie nie uruchamia już analizy automatycznie. Dodano zatrzymywanie, widoczne działanie w tle i błędy obok czynności. Motywy jasny, ciemny i kontrastowy, RU/EN/PL. ',
}
for lang,text in prefix.items():
 if not data[0]['notes'][lang].startswith(text): data[0]['notes'][lang]=text+data[0]['notes'][lang]
file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Updated local 2.3.0.0 UI release notes')
