# Linda-Pro 2.0.2.21

## ru

• Новые модели 1.3 (Essay и Multi, объединённые из трёх обученных вариантов) для всех трёх языков. Английский теперь идёт тем же путём, что русский и польский, на общих моделях: при смене языка они не перезагружаются.
• Польский: на тестовом наборе обнаружение ИИ выросло с 39% до 80% при ложных 0,9% (было 0,3%); русский: с 57% до 78% при тех же 0,6% ложных; английский: свежие модели и «очеловеченные» тексты ловятся заметно чаще (HumanizerBench 70% → 81%).
• Честно: на английском чуть выросли ложные срабатывания на текстах не носителей языка (экзаменационные эссе TOEFL: 4,4% → 6,6% на 91 тексте) и на «правленых людях». В режиме «Точный» те же эссе TOEFL дают 1,1% ложных (1 из 91), но английский ИИ ловится реже (HumanizerBench 69%). Для школ и вузов используйте его.
• Пакет моделей около 4 ГБ; пик видеопамяти около 1,6 ГБ. Обновление не удаляет старые папки моделей.
Порог вердикта заморожен по dev-данным; наборы сайта в подборе не участвовали.

## en

• New 1.3 models (Essay and Multi, each merged from three trained variants) for all three languages. English now uses the same routed path as Russian and Polish, on shared models: switching language no longer reloads them.
• Polish: on the main test set detection of AI text rose from 39% to 80% at 0.9% false flags (was 0.3%); Russian: 57% to 78% at the same 0.6% false flags; English: recent-model and humanized texts are caught noticeably more often (HumanizerBench 70% to 81%).
• Honest limits: in English, false flags rose slightly on non-native writing (TOEFL exam essays: 4.4% to 6.6% on 91 texts) and on lightly edited human text. In Precise mode the same TOEFL essays give 1.1% false flags (1 of 91), at the cost of catching fewer English AI texts (HumanizerBench 69%). Use it for schools and universities.
• The model package is about 4 GB; peak GPU memory is about 1.6 GB. The update does not delete old model folders.
The verdict threshold was frozen on development data; the website test sets were not used for selection.

## pl

• Nowe modele 1.3 (Essay i Multi, każdy scalony z trzech wytrenowanych wariantów) dla wszystkich trzech języków. Angielski idzie teraz tą samą ścieżką co rosyjski i polski, na wspólnych modelach: zmiana języka nie przeładowuje ich.
• Polski: na głównym zestawie testowym wykrywanie tekstu AI wzrosło z 39% do 80% przy 0,9% fałszywych alarmów (było 0,3%); rosyjski: z 57% do 78% przy tych samych 0,6%; angielski: teksty nowych modeli i „uczłowieczone” są wykrywane wyraźnie częściej (HumanizerBench 70% do 81%).
• Uczciwie: w angielskim nieco wzrosły fałszywe alarmy na tekstach osób niebędących native speakerami (eseje TOEFL: 4,4% do 6,6% na 91 tekstach) i na lekko redagowanych tekstach ludzi. W trybie Dokładnym te same eseje TOEFL dają 1,1% fałszywych alarmów (1 z 91), ale angielski tekst AI jest wykrywany rzadziej (HumanizerBench 69%). Użyj go w szkołach i na uczelniach.
• Pakiet modeli ma około 4 GB; szczyt pamięci GPU około 1,6 GB. Aktualizacja nie usuwa starych folderów modeli.
Próg werdyktu zamrożono na danych deweloperskich; zestawy ze strony nie brały udziału w doborze.
