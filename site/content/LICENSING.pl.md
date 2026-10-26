# Licencjonowanie Linda na jednej stronie

Linda nazywała się wcześniej Linda-Pro; obejmuje detektory Linda Assay (dawniej Linda-Pro) i Linda Loupe (dawniej Linda-Pro Lite). Licencje kupione pod starą nazwą pozostają ważne.

Linda to jeden produkt, który możesz pobrać na dwa sposoby. Zasady są te same dla obu.

| | Co otrzymujesz | Skąd |
|---|---|---|
| **Aplikacja Windows** | instalator z oknem, mapą kolorów, automatycznymi aktualizacjami modeli | `Linda-Setup.exe` w [GitHub Releases](https://github.com/Lendarixon/Linda/releases/latest) |
| **Wiersz poleceń / Python** | pakiet `linda_pro` i narzędzia (`python -m linda_pro`, `evaluate.py`) | [GitHub](https://github.com/Lendarixon/Linda) |
| **Modele i kalibracja** | sieci neuronowe i progi (około 2,9 GB) | [Hugging Face](https://huggingface.co/Lindarixon/Linda-Pro); aplikacja pobierze je za Ciebie |

## 1. Bezpłatnie: osobisty użytek niekomercyjny

Aplikacja, narzędzia wiersza poleceń, kod, modele i kalibracja są **bezpłatne** do osobistego użytku niekomercyjnego na licencji **CC BY-NC 4.0**.
Obejmuje to na przykład: sprawdzanie własnych tekstów lub tekstów znajomych na własny użytek, naukę, hobby, badania niekomercyjne oraz zgłębianie działania detektora.
Pobierz je z Hugging Face lub GitHuba albo pozwól aplikacji to zrobić. Bez rejestracji, klucza i limitów.

Bezpłatna instalacja detektora obejmuje Assay/Loupe. Opcjonalne pakiety Humanizer i Linda Trace wymagają płatnego klucza Detector, także do użytku osobistego. Nie zmienia to licencji kodu źródłowego już opublikowanego na CC BY-NC 4.0.

## 2. Licencja komercyjna: co kupujesz

Kupujesz **licencję na komercyjne używanie oprogramowania**. Jedna licencja obejmuje **wszystko razem**: aplikację (interfejs), narzędzia wiersza poleceń i pakiet oraz modele i kalibrację.
Modeli nie kupuje się osobno, a interfejs nie jest licencjonowany osobno od modeli.

Użytek komercyjny to używanie Linda do pracy zarobkowej lub dla klientów, wewnątrz firmy, szkoły, uczelni lub innej organizacji (na przykład sprawdzanie składanych prac przez personel), w produkcie lub usłudze, którą sprzedajesz, albo każdy inny użytek przynoszący pieniądze lub wspierający działalność organizacji.

| Licencja | Cena | Kto | Urządzenia | Aktualizacje |
|---|---|---|---|---|
| **Personal** | 10 $, jednorazowo | jedna osoba (freelancer, konsultant, właściciel małej firmy) | do 3 | poprawki kupionej wersji; nowe funkcje mogą wymagać osobnej licencji |
| **Team** | 30 $, jednorazowo | do 10 osób | do 20 | poprawki kupionej wersji; nowe funkcje mogą wymagać osobnej licencji |
| **Organization / University** | 500 $ rocznie | jedna organizacja w jednej siedzibie | do 200 | przez cały rok licencji, w tym nowe wersje modeli |

* **Jak otrzymać.** Po płatności otrzymujesz klucz licencyjny e-mailem. Wpisz go w aplikacji (okno Licence): powiadomienie o licencji zniknie. Narzędzia wiersza poleceń nie sprawdzają kluczy; licencja obowiązuje je tak samo, a klucz jest Twoim dowodem zakupu.
* **Zasada wersji.** Klucz Personal lub Team jest wieczysty: kupiona wersja i jej poprawki działają zawsze. Nowe funkcje i nowe modele mogą być wydawane tylko w ramach osobnych licencji lub jako płatna aktualizacja. Licencja Organization obowiązuje przez opłacony rok i obejmuje wszystkie aktualizacje wydane w tym roku; po jego zakończeniu bez odnowienia użytek komercyjny Linda na jej podstawie ustaje.
* **Detektor nie jest zablokowany.** Detektor (Linda Assay i Linda Loupe) działa tak samo bez klucza; klucz to prawne pozwolenie na użytek komercyjny, nie przełącznik techniczny. Każdy płatny klucz (dowolna edycja) obejmuje również opcjonalne narzędzia Linda Trace i Humanizer, także dla użytkownika Personal; nie są to osobne zakupy, lecz narzędzia wewnątrz Detektora. Probe to osobny program/klucz; klucz Detektora nie odblokowuje Probe.
* **Nie wchodzą w te licencje:** prawa wyłączne, integracja OEM / white-label z innym produktem, hosting Linda jako usługi lub API dla stron trzecich, redystrybucja modeli, kalibracja indywidualna na Twoich tekstach. Są uzgadniane indywidualnie: napisz na lindapro.support@proton.me, podając przypadek użycia, wolumen i wdrożenie.

## 3. Szybkie pytania

* **Czy płacę za modele?** Nie — do osobistego użytku niekomercyjnego. Do użytku komercyjnego obowiązuje licencja z sekcji 2, obejmująca modele.
* **Używam w pracy tylko wiersza poleceń. Czy potrzebuję klucza?** Tak, użytek komercyjny wymaga licencji niezależnie od sposobu uruchomienia.
* **Jestem studentem albo nauczycielem, sprawdzam własne prace lub zgłębiam narzędzie.** Bezpłatnie (niekomercyjnie). Szkoła lub uczelnia sprawdzająca prace w ramach swojej działalności potrzebuje licencji Organization.
* **Jestem freelancerem sprawdzającym teksty dla klientów.** Licencja Personal.
* **Jak liczone są urządzenia? Czy mogę przenieść klucz na nowy komputer?** Kupiony klucz aktywuje się na komputerze, na którym go wpiszesz (aplikacja wysyła klucz i anonimowy id maszyny, ale nie Twoje teksty), i zajmuje miejsce w limicie urządzeń Twojej licencji. Kopiowanie aplikacji ani jej pliku licencji na inny komputer nie przenosi licencji. Aby przenieść: otwórz okno Licence i naciśnij Remove key przy połączeniu z siecią (slot zwalnia się po potwierdzeniu przez Polar), a następnie wpisz klucz na nowym komputerze. Jeśli starego komputera już nie ma, napisz do wsparcia — slot zostanie zwolniony.
* **Czy mogę włożyć ją do swojego produktu albo strony?** Tylko na podstawie osobnej umowy OEM.
* **Co aplikacja wysyła do internetu?** Tylko pobieranie modeli, sprawdzanie aktualizacji i — gdy wpiszesz klucz — klucz, identyfikatory aktywacji, losową etykietę i skrót identyfikatora urządzenia. Twoje teksty nigdy nie opuszczają Twojego komputera. Zobacz [Privacy](https://lendarixon.github.io/Linda/privacy-pl.html).
* **Co jeśli nie zgadzam się z wynikiem?** Detektor daje ocenę probabilistyczną i może się mylić; nie może być jedyną podstawą decyzji o ludziach. Zobacz [Terms](https://lendarixon.github.io/Linda/terms-pl.html).

Ta strona streści licencję. Moc prawną mają [Terms](https://lendarixon.github.io/Linda/terms-pl.html), plik `LICENSE` (CC BY-NC 4.0 i licencja komercyjna) oraz `COMMERCIAL_LICENSE.md` w repozytoriach; ta strona nie jest poradą prawną. Zobacz też [NOTICE](https://github.com/Lendarixon/Linda/blob/main/docs/NOTICE.md) i [MODEL_CARD](https://github.com/Lendarixon/Linda/blob/main/docs/MODEL_CARD.md); warunki stron trzecich pozostają w mocy.


Personal i Team są bezterminowe dla kupionej wersji i jej poprawek; nowe funkcje lub modele mogą wymagać osobnej licencji. Organization obejmuje aktualizacje opłaconego roku i odnawia się w Polar do anulowania. Bezpłatna próba komercyjna trwa 14 dni kalendarzowych od pierwszego uruchomienia, bez płatnego klucza, rejestracji i automatycznej opłaty. Termin jest warunkiem licencji; aplikacja nie odlicza czasu. Dalszy użytek komercyjny wymaga płatnej licencji. Osobisty użytek niekomercyjny jest bezpłatny bez limitu czasu.

## Płatność, podatek, odnowienie i zwroty

Płatności obsługuje Polar (Merchant of Record), w USD: Personal 10 USD jednorazowo, Team 30 USD jednorazowo, Organization 500 USD/rok. Ustawienie podatku: Location based; w polskim checkout te kwoty zawierają podatek. W innych krajach sposób prezentacji może się różnić; ostateczna kwota, podatek i okres płatności są widoczne przed zakupem. Organization to roczna subskrypcja odnawiana automatycznie do anulowania; pozwolenie trwa do końca opłaconego roku. Personal/Team nie odnawiają się automatycznie.

Dotychczasowa polityka: Personal/Team — pełny zwrot przez Polar w ciągu 14 dni, jeśli aplikacja nie działa lub nie odpowiada potrzebom. Organization — w ciągu 14 dni, gdy klucz nie był używany do pracy komercyjnej albo problemu technicznego nie można naprawić. Później można anulować odnowienie; dobrowolny zwrot za niewykorzystaną część roku nie jest oferowany. Obowiązkowe prawa konsumenta pozostają bez zmian. To podsumowanie dostawcy, bez opinii prawnika.

## Bezpłatna 14-dniowa próba komercyjna

Osoby fizyczne i organizacje mogą bezpłatnie oceniać Linda do użytku komercyjnego przez 14 dni kalendarzowych od pierwszego uruchomienia aplikacji. Rejestracja, osobno uzgodniona data startu, płatny klucz, karta i subskrypcja nie są wymagane. To pozwolenie licencyjne, bez licznika ani technicznej blokady; użytkownik sam przestrzega terminu. Ponowna instalacja, aktualizacja lub zmiana urządzenia nie rozpoczyna nowego okresu dla tej samej osoby lub organizacji. Próba obejmuje ocenę wewnętrzną, bez odsprzedaży, dystrybucji, hostingu dla osób trzecich i negatywnych decyzji o osobach. Po tym okresie dalszy użytek komercyjny wymaga odpowiedniej płatnej licencji. Osobisty użytek niekomercyjny pozostaje bezpłatny na CC BY-NC 4.0, bez limitu 14 dni. Nie ma automatycznej opłaty, odnowienia ani przejścia na płatną subskrypcję. Teksty pozostają u użytkownika; przekazanie zbiorczych uwag jest dobrowolne.


Płatny klucz Detector można kupić wyłącznie do korzystania z Humanizera i Trace, także do osobistych zadań niekomercyjnych. Linda Probe wymaga osobnej licencji i klucza.
