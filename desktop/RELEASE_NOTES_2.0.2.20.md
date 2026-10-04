# Linda-Pro 2.0.2.20

## ru

• PDF-отчёты теперь строятся встроенной библиотекой без Edge, Chrome или Brave. Единая вёрстка A4 включает векторные диаграммы, карту структуры, метрики, отмеченный текст и Unicode для русского, английского и польского. Молчаливое переключение на старый экспортёр устранено.
• PDF/DOCX разбираются отдельным процессом Windows LPAC с ограничениями доступа к файлам и сети. Сохраняются лимиты: 20 секунд, 512 МиБ, вход 20 МБ, результат 4 МБ, PDF до 500 страниц; для DOCX ограничены число элементов и распаковка.
• История шифруется DPAPI текущего пользователя Windows. Существующие записи мигрируют в защищённое хранилище; запись выполняется атомарно, очистка учитывает политику хранения.
• Черновики перезапуска и обновления страницы также защищены DPAPI. Новый текст не сохраняется открыто в sessionStorage; прежние черновики переносятся с сохранением текста.
• Журнал аудита защищён цепочкой HMAC, отдельной контрольной точкой и восстановлением незавершённой записи. Ручная очистка отключена; журнал хранится согласно политике организации.
• Исправлено белое окно WebView2 после сворачивания: поверхность перерисовывается без перезагрузки страницы и потери введённого текста. Сохранён тёмный фон окна.
• Добавлен явный PerMonitorV2 DPI-манифест, сохранена поддержка длинных путей Windows для временного обработчика документов.
• DirectML проверяет фактически используемый провайдер. При смене CPU/GPU освобождаются прежние сессии и обновляется статус устройства.
• Исправлены подготовка изолированного обработчика документов и обработка его ошибок: повреждённые документы не блокируют последующую работу и не показывают внутренние пути пользователю.
• Сохранены фоновое скачивание обновления, скрытая установка, повторное открытие программы и восстановление несохранённого текста. Основной канал предлагает обычный Windows-установщик, отдельно от Dev.
Веса моделей, калибровки и коммерческие условия не менялись.

## en

• PDF reports now use the bundled renderer without Edge, Chrome or Brave. One A4 layout includes vector charts, structure map, metrics, annotated text and Unicode for English, Russian and Polish. Silent switching to the old exporter has been removed.
• PDF/DOCX parsing runs in a separate Windows LPAC process with restricted file and network access. Limits remain: 20 seconds, 512 MiB, 20 MB input, 4 MB output and 500 PDF pages; DOCX entry count and expansion are bounded.
• Current-user Windows DPAPI encrypts history. Existing records migrate into protected storage; writes are atomic and deletion respects retention policy.
• Restart and page-refresh drafts also use DPAPI. New text is no longer stored in plaintext sessionStorage; legacy drafts migrate while preserving text.
• The audit ledger uses an HMAC chain, independent checkpoint and recovery of interrupted writes. Manual clearing is disabled; organization retention policy controls storage.
• Fixed the blank WebView2 window after minimizing: the surface repaints without reloading the page or losing input. The dark window background is retained.
• An explicit PerMonitorV2 DPI manifest is included, with Windows long-path support for the temporary document worker.
• DirectML checks the actual execution provider. Switching CPU/GPU releases previous sessions and refreshes device status.
• Fixed isolated document-worker preparation and error handling: damaged documents do not block subsequent work or expose internal paths to users.
• Background update download, hidden installation, automatic relaunch and unsaved-text recovery remain supported. The stable channel serves the normal Windows installer separately from Dev.
Model weights, calibrations and commercial terms are unchanged.

## pl

• Raporty PDF używają teraz wbudowanego renderera bez Edge, Chrome ani Brave. Jeden układ A4 zawiera wykresy wektorowe, mapę struktury, metryki, oznaczony tekst i Unicode dla polskiego, angielskiego i rosyjskiego. Usunięto ciche przełączanie na stary eksport.
• PDF/DOCX są odczytywane w osobnym procesie Windows LPAC z ograniczonym dostępem do plików i sieci. Limity: 20 sekund, 512 MiB, wejście 20 MB, wynik 4 MB, PDF do 500 stron; DOCX ma limity liczby elementów i rozpakowania.
• DPAPI bieżącego użytkownika Windows szyfruje historię. Istniejące rekordy są migrowane do chronionego magazynu; zapis jest atomowy, a usuwanie uwzględnia retencję.
• Szkice po restarcie i odświeżeniu strony również używają DPAPI. Nowy tekst nie jest zapisywany jawnie w sessionStorage; stare szkice są migrowane z zachowaniem tekstu.
• Dziennik audytu używa łańcucha HMAC, osobnego punktu kontrolnego i odtwarzania przerwanych zapisów. Ręczne czyszczenie jest wyłączone; obowiązuje retencja organizacji.
• Naprawiono białe okno WebView2 po minimalizacji: powierzchnia jest odrysowywana bez przeładowania strony i utraty tekstu. Zachowano ciemne tło okna.
• Dodano jawny manifest PerMonitorV2 DPI oraz obsługę długich ścieżek Windows dla tymczasowego procesu dokumentów.
• DirectML sprawdza rzeczywistego dostawcę wykonania. Zmiana CPU/GPU zwalnia poprzednie sesje i odświeża stan urządzenia.
• Poprawiono przygotowanie izolowanego procesu dokumentów i błędy: uszkodzone dokumenty nie blokują dalszej pracy ani nie ujawniają wewnętrznych ścieżek.
• Zachowano pobieranie aktualizacji w tle, ukrytą instalację, ponowne otwarcie aplikacji i odtwarzanie tekstu. Kanał stabilny udostępnia zwykły instalator Windows oddzielnie od Dev.
Wagi modeli, kalibracje i warunki komercyjne pozostają bez zmian.