"""Human-readable feature names for the three supported product languages."""
LABELS = {}
for line in '''word_len_mean|Mean word length|Średnia długość słowa
word_len_std|Variation in word length|Zróżnicowanie długości słów
long_word_share|Words with 10+ letters|Słowa o co najmniej 10 literach
short_word_share|Words with at most 2 letters|Słowa o najwyżej 2 literach
mattr50|Vocabulary diversity (MATTR, 50-word windows)|Różnorodność słownictwa (MATTR, okna 50 słów)
mtld|Vocabulary diversity (MTLD)|Różnorodność słownictwa (MTLD)
yule_k|Vocabulary concentration (Yule K)|Koncentracja słownictwa (Yule K)
hapax100|Words occurring once per 100-word window|Słowa występujące raz w oknie 100 słów
entropy200|Vocabulary entropy (200-word windows)|Entropia słownictwa (okna 200 słów)
fw_share|Function-word share|Udział słów funkcyjnych
pron_1s|First-person singular pronouns per 1000 words|Zaimki pierwszej osoby liczby pojedynczej na 1000 słów
pron_2|Second-person references per 1000 words|Zwracanie się do drugiej osoby na 1000 słów
cap_inner_share|Capitalized words inside sentences|Słowa pisane wielką literą wewnątrz zdań
allcaps_share|All-capital words|Słowa pisane wyłącznie wielkimi literami
num_rate|Numbers per 1000 words|Liczby na 1000 słów
sent_len_mean|Mean sentence length|Średnia długość zdania
sent_len_std|Variation in sentence length|Zróżnicowanie długości zdań
sent_len_cv|Relative variation in sentence length|Względne zróżnicowanie długości zdań
sent_len_skew|Sentence-length skewness|Asymetria rozkładu długości zdań
sent_len_median|Median sentence length|Mediana długości zdań
sent_short_share|Sentences with at most 6 words|Zdania o najwyżej 6 słowach
sent_long_share|Sentences with 30+ words|Zdania o co najmniej 30 słowach
burstiness|Changes in consecutive sentence lengths|Zmiany długości kolejnych zdań
sent_len_ac1|Correlation of adjacent sentence lengths|Korelacja długości sąsiednich zdań
first_word_div|Diversity of sentence-opening words|Różnorodność pierwszych słów zdań
first_word_top|Most frequent sentence-opening word|Najczęstsze pierwsze słowo zdania
conj_start|Sentences starting with a conjunction|Zdania rozpoczynające się spójnikiem
marker_start|Sentences starting with a discourse marker|Zdania rozpoczynające się zwrotem wprowadzającym
quest_share|Questions|Zdania pytające
excl_share|Exclamations|Zdania wykrzyknikowe
commas_per_sent|Commas per sentence|Przecinki na zdanie
commas_per_sent_std|Variation in commas per sentence|Zróżnicowanie liczby przecinków w zdaniu
no_comma_share|Sentences without commas|Zdania bez przecinków
line_len_mean|Mean paragraph length in words|Średnia długość akapitu w słowach
line_len_cv|Relative variation in paragraph length|Względne zróżnicowanie długości akapitów
single_sent_lines|Single-sentence paragraphs|Akapity jednozdaniowe
bullet_share|List-item lines|Wiersze stanowiące punkty listy
heading_share|Heading lines|Wiersze nagłówków
bold_rate|Bold spans per 1000 words|Pogrubienia na 1000 słów
emoji_rate|Emoji per 1000 characters|Emoji na 1000 znaków
compress|Text compressibility (zlib)|Podatność tekstu na kompresję (zlib)
rep_trigram|Repeated three-word sequences|Powtórzenia sekwencji trzech słów
rep_bigram|Repeated two-word sequences|Powtórzenia sekwencji dwóch słów
adj_overlap|Vocabulary overlap in adjacent sentences|Wspólne słownictwo sąsiednich zdań
upper_share|Uppercase letters|Wielkie litery
digit_share|Digits|Cyfry
punct_share|Punctuation characters|Znaki interpunkcyjne
foreign_script|Letters from another alphabet|Litery z innego alfabetu
mixed_script_words|Words mixing alphabets|Słowa mieszające alfabety
zero_width|Invisible characters|Znaki niewidoczne
odd_spaces|Unusual spaces|Nietypowe spacje
dash_spaced|Spaced dashes per 1000 characters|Myślniki ze spacjami na 1000 znaków
hyphen_as_dash|Hyphens used as dashes per 1000 characters|Łączniki zamiast myślników na 1000 znaków
ellipsis_rate|Ellipses per 1000 characters|Wielokropki na 1000 znaków
paren_rate|Parentheses per 1000 words|Nawiasy na 1000 słów
quote_rate|Quotation marks per 1000 words|Cudzysłowy na 1000 słów
diacritics|Polish diacritic letters|Polskie litery diakrytyczne
yo_share|Russian ё among е/ё|Rosyjska litera ё wśród е/ё
simpson_d|Simpson's vocabulary concentration (D)|Koncentracja słownictwa Simpsona (D)
herdan_c|Logarithmic vocabulary richness (Herdan's C)|Logarytmiczne bogactwo słownictwa (C Herdana)
hapax_ratio|Hapax legomena words per token|Udział słów jednokrotnych (hapax legomena)
hapax_type_ratio|Vocabulary proportion occurring once|Odsetek słownika występujący tylko raz
dis_ratio|Dis legomena words per token|Udział słów dwukrotnych (dis legomena)
dis_type_ratio|Vocabulary proportion occurring twice|Odsetek słownika występujący dwa razy
brunet_w|Brunet's W vocabulary richness statistic|Statystyka bogactwa słownictwa Bruneta (W)
honore_r|Honoré's R vocabulary richness statistic|Statystyka bogactwa słownictwa Honorégo (R)
dash_em_ratio|Em-dash share among dashes|Udział pauz (—) wśród wszystkich myślników
dash_hyph_ratio|Hyphen share among dashes|Udział łączników (-) wśród wszystkich myślników
dash_spaced_rate|Spaced dashes per 1000 characters|Myślniki ze spacjami na 1000 znaków
quote_pair_guill_diff|Guillemet quotation asymmetry (« »)|Asymetria cudzysłowów ostrokątnych (« »)
quote_pair_curly_diff|Curly quotation asymmetry (“ ”)|Asymetria cudzysłowów typograficznych (“ ”)
quote_parity_dq|Straight double-quote parity|Parzystość prostych cudzysłowów podwójnych
quote_parity_sq|Straight single-quote parity|Parzystość prostych cudzysłowów pojedynczych
shape_title|Titlecase capitalized words share|Udział słów pisanych z wielkiej litery
shape_upper|All-caps words share|Udział słów pisanych wielkimi literami
shape_lower|Lowercase words share|Udział słów pisanych małymi literami
shape_mixed|Mixed-case words share|Udział słów o mieszanym rejestrze'''.splitlines():
    key,en,pl=line.split('|'); LABELS[key]={'en':en,'pl':pl}

RU_EXTENDED = {
    'simpson_d': 'Концентрация словаря Симпсона (D)',
    'herdan_c': 'Логарифмическое богатство словаря (C Хердана)',
    'hapax_ratio': 'Доля слов, встретившихся один раз (гапаксы)',
    'hapax_type_ratio': 'Доля словаря, встретившаяся один раз',
    'dis_ratio': 'Доля слов, встретившихся два раза (дис-легомена)',
    'dis_type_ratio': 'Доля словаря, встретившаяся два раза',
    'brunet_w': 'Статистика богатства словаря Брюне (W)',
    'honore_r': 'Статистика лексического разнообразия Оноре (R)',
    'dash_em_ratio': 'Доля длинных тире (—) среди всех тире',
    'dash_hyph_ratio': 'Доля дефисов (-) среди всех тире',
    'dash_spaced_rate': 'Тире с пробелами на 1000 знаков',
    'quote_pair_guill_diff': 'Асимметрия кавычек-ёлочек (« »)',
    'quote_pair_curly_diff': 'Асимметрия фигурных кавычек (“ ”)',
    'quote_parity_dq': 'Чётность прямых двойных кавычек',
    'quote_parity_sq': 'Чётность прямых одинарных кавычек',
    'shape_title': 'Доля слов с заглавной буквы',
    'shape_upper': 'Доля слов заглавными буквами',
    'shape_lower': 'Доля строчных слов',
    'shape_mixed': 'Доля слов смешанного регистра',
}


def feature_label(name,language):
    from core import linda
    if language=='ru':
        if name in RU_EXTENDED: return RU_EXTENDED[name]
        if name.startswith('pseq_'):
            return f"Пунктуационная последовательность «{name[5:]}» на 1000 знаков"
        return linda().feature_description(name)
    if name.startswith('fw:'):
        return ('Word frequency: ' if language=='en' else 'Częstość słowa: ')+name[3:]
    if name.startswith('p_'):
        symbol=linda().PUNCT_CHARS.get(name[2:],name[2:])
        return str(symbol)+(' per 1000 characters' if language=='en' else ' na 1000 znaków')
    if name.startswith('pseq_'):
        seq = name[5:]
        return (f'Punctuation sequence "{seq}" per 1000 characters' if language=='en'
                else f'Ciąg interpunkcyjny „{seq}” na 1000 znaków')
    return LABELS.get(name,{}).get(language,name.replace('_',' '))
