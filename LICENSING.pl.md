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

## 2. Licencja komercyjna: co kupujesz

Kupujesz **licencję na komercyjne używanie oprogramowania**. Jedna licencja obejmuje **wszystko razem**: aplikację (interfejs), narzędzia wiersza poleceń i pakiet oraz modele i kalibrację.
Modeli nie kupuje się osobno, a interfejs nie jest licencjonowany osobno od modeli.

Użytek komercyjny to używanie Linda do pracy zarobkowej lub dla klientów, wewnątrz firmy, szkoły, uczelni lub innej organizacji (na przykład sprawdzanie składanych prac przez personel), w produkcie lub usłudze, którą sprzedajesz, albo każdy inny użytek przynoszący pieniądze lub wspierający działalność organizacji.

| Licencja | Cena | Kto | Urządzenia | Aktualizacje |
|---|---|---|---|---|
| **Personal** | 10 $, jednorazowo | jedna osoba (freelancer, konsultant, właściciel małej firmy) | do 3 | bezpłatnie w ramach wersji 1.x |
| **Team** | 30 $, jednorazowo | do 10 osób | do 20 | bezpłatnie w ramach wersji 1.x |
| **Organization / University** | 500 $ rocznie | jedna organizacja w jednej siedzibie | do 200 | przez cały rok licencji, w tym nowe wersje modeli |

* **Jak otrzymać.** Po płatności otrzymujesz klucz licencyjny e-mailem. Wpisz go w aplikacji (okno Licence): powiadomienie o licencji zniknie. Narzędzia wiersza poleceń nie sprawdzają kluczy; licencja obowiązuje je tak samo, a klucz jest Twoim dowodem zakupu.
* **Zasada wersji.** Klucz Personal lub Team jest wieczysty dla wersji 1.x. Nowa wersja główna (2.0) może wymagać nowego klucza lub uaktualnienia. Licencja Organization obowiązuje przez opłacony rok; po jego zakończeniu bez odnowienia użytek komercyjny Linda na jej podstawie ustaje.
* **Nic nie jest zablokowane.** Aplikacja działa tak samo bez klucza; klucz to prawne pozwolenie, nie przełącznik techniczny.
* **Nie wchodzą w te licencje:** prawa wyłączne, integracja OEM / white-label z innym produktem, hosting Linda jako usługi lub API dla stron trzecich, redystrybucja modeli, kalibracja indywidualna na Twoich tekstach. Są uzgadniane indywidualnie: napisz na lindapro.support@proton.me, podając przypadek użycia, wolumen i wdrożenie.

## 3. Szybkie pytania

* **Czy płacę za modele?** Nie — do osobistego użytku niekomercyjnego. Do użytku komercyjnego obowiązuje licencja z sekcji 2, obejmująca modele.
* **Używam w pracy tylko wiersza poleceń. Czy potrzebuję klucza?** Tak, użytek komercyjny wymaga licencji niezależnie od sposobu uruchomienia.
* **Jestem studentem albo nauczycielem, sprawdzam własne prace lub zgłębiam narzędzie.** Bezpłatnie (niekomercyjnie). Szkoła lub uczelnia sprawdzająca prace w ramach swojej działalności potrzebuje licencji Organization.
* **Jestem freelancerem sprawdzającym teksty dla klientów.** Licencja Personal.
* **Jak liczone są urządzenia? Czy mogę przenieść klucz na nowy komputer?** Kupiony klucz aktywuje się na komputerze, na którym go wpiszesz (aplikacja wysyła klucz i anonimowy id maszyny, ale nie Twoje teksty), i zajmuje miejsce w limicie urządzeń Twojej licencji. Kopiowanie aplikacji ani jej pliku licencji na inny komputer nie przenosi licencji. Aby przenieść: otwórz okno Licence i naciśnij Remove key (slot się zwolni), a następnie wpisz klucz na nowym komputerze. Jeśli starego komputera już nie ma, napisz do wsparcia — slot zostanie zwolniony.
* **Czy mogę włożyć ją do swojego produktu albo strony?** Tylko na podstawie osobnej umowy OEM.
* **Co aplikacja wysyła do internetu?** Tylko pobieranie modeli, sprawdzanie aktualizacji i — gdy wpiszesz klucz — klucz plus losową etykietę urządzenia. Twoje teksty nigdy nie opuszczają Twojego komputera. Zobacz [Privacy](privacy.html).
* **Co jeśli nie zgadzam się z wynikiem?** Detektor daje ocenę probabilistyczną i może się mylić; nie może być jedyną podstawą decyzji o ludziach. Zobacz [Terms](terms.html).

Ta strona streści licencję. Moc prawną mają [Terms](terms.html), plik `LICENSE` (CC BY-NC 4.0 i licencja komercyjna) oraz `COMMERCIAL_LICENSE.md` w repozytoriach; ta strona nie jest poradą prawną.
