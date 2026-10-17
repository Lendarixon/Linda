# Linda 2.0.6.2 — 17 October 2026

## EN

• Clear warnings appear before analysis when text is shorter than the recommended 300 words or resembles a list, form or slide text.
• Supported file types are explained more clearly. After a failed upload, analysis stays blocked until the text is edited or a supported file is loaded, independently for each tab.
• Safer model moves prevent overlapping folders from deleting the new copy; cleanup removes only the job's own temporary files.
• Fixed cancellation during Linda Loupe analysis and redacted profile and model paths in diagnostic metadata.
• Models 1.3.4, tokenizers and scoring thresholds are unchanged. Results do not prove authorship; short AI inserts may still be missed.

## PL

• Przed analizą aplikacja wyraźnie ostrzega, gdy tekst ma mniej niż zalecane 300 słów lub przypomina listę, formularz albo slajdy.
• Jaśniejsze informacje o obsługiwanych plikach. Po nieudanym wczytaniu analiza pozostaje zablokowana do poprawienia tekstu lub wybrania prawidłowego pliku, osobno dla każdej karty.
• Bezpieczniejsze przenoszenie modeli: ochrona przed nakładającymi się folderami i usunięciem nowej kopii; porządkowanie tylko własnych plików tymczasowych.
• Poprawiono anulowanie analizy w Linda Loupe oraz ukrywanie ścieżek profilu i modeli w metadanych diagnostycznych.
• Modele 1.3.4, tokenizatory i progi oceny pozostają bez zmian. Wynik nie jest dowodem autorstwa; krótkie wstawki AI mogą pozostać niewykryte.

## RU

• До анализа приложение заметно предупреждает, если текст короче рекомендуемых 300 слов или похож на список, анкету либо текст слайдов.
• Понятнее указаны поддерживаемые файлы. После неудачной загрузки анализ блокируется до правки текста или выбора подходящего файла, отдельно для каждой вкладки.
• Безопаснее перенос моделей: защита от пересекающихся папок и удаления новой копии; очистка только собственных временных файлов.
• Исправлена отмена анализа Linda Loupe; пути профиля и моделей скрываются в метаданных диагностики.
• Модели 1.3.4, токенизаторы и пороги оценки не менялись. Результат не доказывает авторство; короткие ИИ-вставки могут быть пропущены.

## Web demo

[Try Linda in your browser](https://ninjagovlad--linda-pro-demo-web.modal.run/). The hosted demo processes text on Modal servers; the desktop app remains local. The demo offers 12 successful checks per signed browser cookie, with 12 checks per shared network per UTC day and a shared global daily capacity. Up to 6,000 characters, TXT/MD/DOCX; unsupported files do not consume a check. DOCX tables and cancelled quota reservations are handled more reliably.

## Validation and limits

509 desktop tests and 72 hosted-demo tests passed in the pre-release audit. A diagnostic long-text suite ran both models and modes on 13 samples of 2,106–4,056 words (52 main runs plus 12 identical repeats); sentence offsets and non-whitespace coverage passed throughout. 36 actual long-text tokenizer checks passed. This suite is not an independent accuracy benchmark: sources may overlap training, one mislabelled-language row was retained separately and a verified Russian control added, and the Polish AI control is a derived concatenation. Both detectors missed all 437 AI words in one Russian sentence-mixture case. No detection-accuracy improvement is claimed.

App 2.0.6.2; Microsoft Store package 2.0.6002.0; model pack 1.3.4. Store packaging does not establish Partner Center certification.
