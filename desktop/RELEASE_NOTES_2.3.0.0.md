# Linda 2.3.0.0 — 24 October 2026

A clearer Windows workspace, plus two optional licensed tools. **The detectors (Assay, Loupe), model pack 1.3.4.1 and scoring thresholds are unchanged.**

## What is new
- **Windows-style workspace**: permanent navigation, separate History and Tools pages, grouped settings, guidance before a check. Pasting no longer starts analysis automatically; there is an explicit **Stop** action, visible background activity and inline errors. Light, dark and contrast themes; RU/EN/PL.
- **Startup splash "Panorama"**: ten random illustrations (detector and Trace), shown while the local service warms up; a Skip button is available.
- **Linda Trace** (licensed pack): forensic authorship — ranks a text against a corpus and lists author candidates. Output is relative distances only, not proof of authorship.
- **Humanizer** (licensed pack, two tiers: 0.6B CPU / 4B GPU, picked automatically), with a "humanize until calm" loop: the text is rewritten again (max 5 passes) until the detector's AI share falls below 50%. Meaning is not verified automatically — read the result.
- After each completed check a **Humanize** button appears in the command row.
- Live progress bars for Humanizer, the refinement loop and the Trace corpus.
- More document formats on import; cancelling any tool; offline hu_* translations; fixes for input fields, import in Humanize and a stuck inert state after the splash.
- Installer: asks for a licence key (without one only the detector is installed); a setup mutex prevents two installers running at once. Use `/VERYSILENT` for a fully silent install.

## Licence and packs
Trace and Humanizer are **not** part of the free detector: their packs are downloaded only with a licence key (any tier, including the Organization subscription). Without a key the tabs show a lock leading to licence entry. The packs and their adapters are not included in this repository or in the source tree. The detector, the command-line tools and the 14-day commercial evaluation are described in [LICENSING.md](../LICENSING.md); personal non-commercial use stays free (CC BY-NC 4.0).

## Limits
Prefer at least 300 words of continuous prose. Results do not prove authorship and small AI inserts can be missed. Warm-up to the main window takes 20–40 s on the tested machine; 2.5 s is only the minimum splash time.