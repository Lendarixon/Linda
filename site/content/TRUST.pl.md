# Linda — prywatność i zaufanie

Zaktualizowano 25 listopada 2026. Aplikacja 2.5.0.6; pakiet modeli 1.5.0. Oświadczenie techniczne autora, bez niezależnego certyfikatu bezpieczeństwa. Historyczne wyniki testów z 11 października 2026 (wersja 2.0.6.0) pozostają historyczne.

## Teksty i połączenia

Aplikacja Windows analizuje tekst lokalnie. Może zapisywać teksty, wyniki i szkice w lokalnej historii; historię można wyłączyć, ustawić okres przechowywania i usunąć wpisy. Aktualny kod chroni przechowywane teksty/wyniki za pomocą Windows DPAPI. Nie oznacza to ochrony przed osobą mającą kontrolę nad zalogowanym kontem Windows ani szyfrowania wszystkich eksportów.

Aplikacja łączy się z Hugging Face w celu pobrania modeli i sprawdzenia podpisanego manifestu, z GitHub w celu pobrania instalatora oraz z Polar w celu aktywacji, usunięcia i okresowej weryfikacji klucza. Do Polar trafiają klucz, identyfikatory aktywacji, losowa etykieta i skrót identyfikatora urządzenia; teksty nie są wysyłane tą ścieżką. Serwisy widzą metadane połączeń, np. adres IP. CLI i własny serwer to osobne wdrożenia: ich eksporty i logi zależą od operatora. **Demo w chmurze wysyła tekst do serwera; do poufnych danych używaj aplikacji lokalnej.**

## Ograniczenia

Nie używaj wyniku jako jedynego dowodu autorstwa ani jedynej podstawy decyzji dyscyplinarnych, akademickich, prawnych lub kadrowych. Fałszywe alarmy i przeoczenia są możliwe. Szczególnie trudne są krótkie teksty, małe wstawki AI, teksty mieszane, redagowane przez człowieka i prace osób piszących w obcym języku. Ocena dokumentu nie jest procentem słów napisanych przez AI. Kolorowanie lokalne może różnić się od wyniku całości.

Assay używa stabilnego FP32 DirectML; Loupe działa na CPU. Assay pobiera około 5,8 GB modeli; na karcie graficznej aplikacja zapisuje też kopię GPU każdego modelu przy pierwszym użyciu (do około 10 GB na dysku). W pamięci GPU są naraz modele tylko jednego języka; zalecane jest 8 GB VRAM, karty 4 GB od wersji 2.5.0.4 dostają mniejszy budżet, ale nie zostały przez nas zmierzone. Nie deklarujemy audytu niezależnego, SOC 2, ISO 27001 ani gwarantowanego SLA. W raporcie z 11 października 2026 instalator nie miał podpisu Authenticode; to obserwacja historyczna.

## Integralność i kontakt

Oficjalne wydanie 2.5.0.6 (25 listopada 2026): https://github.com/Lendarixon/Linda/releases/tag/v2.5.0.6. Instalator `Linda-Setup.exe`: 509299108 bajtów, SHA-256 `5cf7807cef544ddde806414d437ee53ce81017721230d26432aad0a5839d687d`. (Historyczne wyniki dla 2.0.6.0 z 11 października 2026: SHA-256 `23a3d3afdcebb59e0bb48271392ba470d75b1a2b6a66cf41016d8fa1b73510ad`, rozmiar 286 398 840 bajtów — pozostają historyczne, nie są nowym testem 2.5.) Manifest modeli zawiera sumy SHA-256 i podpis Ed25519, sprawdzany przez aktualizator. 25 listopada 2026 podpis Ed25519 aktualnego manifestu (pakiet modeli 1.5.0) zweryfikowano kodem aktualizacji samej aplikacji.

Zgłoszenia bezpieczeństwa: lindapro.support@proton.me. Podaj wersję i minimalny przykład; nie wysyłaj kluczy ani poufnych tekstów. Szczegółowe oświadczenie: [English trust statement](https://lendarixon.github.io/Linda/trust.html).

## Dokumenty oceny

[Benchmark brief](https://lendarixon.github.io/Linda/benchmark-brief.html) · [Trial PDF — English](https://lendarixon.github.io/Linda/pilot-en.pdf) · [Próba PDF — Polski](https://lendarixon.github.io/Linda/pilot-pl.pdf) · [Document pack EN/PL](https://lendarixon.github.io/Linda/Linda_pilot_documents_EN_PL.zip).

