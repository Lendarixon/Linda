# Linda — prywatność i zaufanie

Stan: 11 października 2026. Aplikacja 2.0.6.0; pakiet modeli 1.3.4. Oświadczenie techniczne autora, bez niezależnego certyfikatu bezpieczeństwa.

## Teksty i połączenia

Aplikacja Windows analizuje tekst lokalnie. Może zapisywać teksty, wyniki i szkice w lokalnej historii; historię można wyłączyć, ustawić okres przechowywania i usunąć wpisy. Aktualny kod chroni przechowywane teksty/wyniki za pomocą Windows DPAPI. Nie oznacza to ochrony przed osobą mającą kontrolę nad zalogowanym kontem Windows ani szyfrowania wszystkich eksportów.

Aplikacja łączy się z Hugging Face w celu pobrania modeli i sprawdzenia podpisanego manifestu, z GitHub w celu pobrania instalatora oraz z Polar w celu aktywacji, usunięcia i okresowej weryfikacji klucza. Do Polar trafiają klucz, identyfikatory aktywacji, losowa etykieta i skrót identyfikatora urządzenia; teksty nie są wysyłane tą ścieżką. Serwisy widzą metadane połączeń, np. adres IP. CLI i własny serwer to osobne wdrożenia: ich eksporty i logi zależą od operatora. **Demo w chmurze wysyła tekst do serwera; do poufnych danych używaj aplikacji lokalnej.**

## Ograniczenia

Nie używaj wyniku jako jedynego dowodu autorstwa ani jedynej podstawy decyzji dyscyplinarnych, akademickich, prawnych lub kadrowych. Fałszywe alarmy i przeoczenia są możliwe. Szczególnie trudne są krótkie teksty, małe wstawki AI, teksty mieszane, redagowane przez człowieka i prace osób piszących w obcym języku. Ocena dokumentu nie jest procentem słów napisanych przez AI. Kolorowanie lokalne może różnić się od wyniku całości.

Assay używa stabilnego FP32 DirectML; Loupe działa na CPU. Dla Assay zalecane jest 8 GB VRAM; zgodność z 4 GB nie została potwierdzona. Nie deklarujemy audytu niezależnego, SOC 2, ISO 27001 ani gwarantowanego SLA. Instalator nie ma podpisu Authenticode.

## Integralność i kontakt

Oficjalne wydanie: https://github.com/Lendarixon/Linda/releases/tag/v2.0.6.0. SHA-256 instalatora: `23a3d3afdcebb59e0bb48271392ba470d75b1a2b6a66cf41016d8fa1b73510ad`; rozmiar 286 398 840 bajtów. Manifest modeli zawiera sumy SHA-256 i podpis Ed25519, sprawdzany przez aktualizator. Podpis bieżącego manifestu został zweryfikowany.

Zgłoszenia bezpieczeństwa: lindapro.support@proton.me. Podaj wersję i minimalny przykład; nie wysyłaj kluczy ani poufnych tekstów. Szczegółowe oświadczenie: [English trust statement](trust.html).

## Dokumenty oceny

[Benchmark brief](benchmark-brief.html) · [Trial PDF — English](pilot-en.pdf) · [Próba PDF — Polski](pilot-pl.pdf) · [Document pack EN/PL](Linda_pilot_documents_EN_PL.zip).
