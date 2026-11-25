# Linda — privacy, limitations and release integrity

Updated 25 November 2026. Windows app 2.5.0.6; model pack 1.5.0. This is a technical vendor statement, not independent security certification.

## Your texts and local storage

The Windows desktop application performs detection on your computer. It does not upload checked texts for inference. It can save texts, results and drafts locally. History can be disabled and retention configured; delete unneeded checks and exports using the application and your organization's policy. Current Windows source uses DPAPI protection for stored text/results. This does not protect against someone controlling your signed-in Windows account, nor does it imply every exported report or file is encrypted. Exports and backups remain your responsibility.

The default legacy EXE profile is `%LOCALAPPDATA%/Linda-Pro`. A Store package uses its package LocalState. Models can be stored in a separately selected folder. The CLI/core library is a separate deployment mode: it does not have the desktop application's automatic history or updater, but CLI output files, wrapper services and operator logs can still retain data.

## Network connections

Desktop network activity includes Hugging Face model downloads and signed-manifest checks; GitHub installer downloads; and Polar licence activation, deactivation and periodic validation (about weekly). Polar receives the licence key, organization/activation identifiers, a random display label and a machine-derived identifier hash. The current implementation hashes a salted Windows MachineGuid; the machine name and original GUID are not sent by this path. Network providers can see connection metadata such as IP addresses. Paid licence state can be cached offline; this does not mean the desktop app never attempts a network connection after activation. Payment data is handled by Polar/its payment processors, under their policies.

The information site sets no cookies and keeps only daily visit totals, without IP addresses or visitor identifiers. GitHub Pages and linked services have their own infrastructure logs. **Modal/HF hosted demos are different:** using them sends the submitted text to the hosted service for processing. Use the installed desktop app for confidential texts; do not equate demo processing with local offline privacy.

## Appropriate use and limitations

Linda is a screening aid for English, Polish and Russian, with `ai`, `uncertain` and `human` outcomes. **Do not use its score, highlighting or report as the sole evidence of authorship or the sole basis for disciplinary, academic, employment or legal decisions about a person.** Review the original text, drafting evidence and context, and allow a response from its author. Human text may be flagged and AI text may be missed. Short texts, small AI inserts, mixed authorship, human-edited AI and non-native/formulaic prose are difficult cases. Global document confidence is not the percentage of AI-written words. Local colouring can disagree with the global score and with another detector.

Published historical benchmark numbers are developer measurements; the historical 2.0.6.0 checks of 11 October 2026 established numerical and UI consistency, not independent population accuracy. Assay uses FP32 stable DirectML on Windows; Loupe runs on CPU. Assay downloads about 5.8 GB of models (English plus Polish/Russian networks); on a GPU the app also saves an FP32 ONNX copy of each model when it is first used (up to about 10 GB on disk). Only one language's models are held in GPU memory at a time; 8 GB GPU memory is recommended, 4 GB cards get a smaller model budget since 2.5.0.4 but are not measured by us. No SOC 2, ISO 27001, independent penetration-test certification or formal SLA is claimed.

## Verify your release

Current release: [Linda 2.5.0.6](https://github.com/Lendarixon/Linda/releases/tag/v2.5.0.6) (25 November 2026). Installer `Linda-Setup.exe`: **509,299,108 bytes**, SHA-256 **`5cf7807cef544ddde806414d437ee53ce81017721230d26432aad0a5839d687d`** (GitHub asset metadata). This hash is not an Authenticode publisher signature; the installer is not code-signed, so Windows SmartScreen may warn.

Previous release noted here: [Linda 2.5.0.5](https://github.com/Lendarixon/Linda/releases/tag/v2.5.0.5). Installer `Linda-Setup.exe`: **509,296,537 bytes**, SHA-256 **`075725bf2fcf90e7de29037db4baddfe35775775ca05e5a35958b248807ce5fb`**.

Historical release (2.0.6.0, 11 October 2026 report): [Linda 2.0.6.0](https://github.com/Lendarixon/Linda/releases/tag/v2.0.6.0). Installer `Linda-Setup.exe`: **286,398,840 bytes**, SHA-256 **`23a3d3afdcebb59e0bb48271392ba470d75b1a2b6a66cf41016d8fa1b73510ad`**. Windows PowerShell: `Get-FileHash -Algorithm SHA256 .\Linda-Setup.exe`; compare the entire hash. The hash is useful when obtained from a trusted independent source; it is not an Authenticode publisher signature. The 11 October 2026 installer was not Authenticode signed; this note does not claim signature or Store verification for later releases.

The [model manifest](https://huggingface.co/Lindarixon/Linda-Pro/resolve/main/latest.json) contains file sizes and SHA-256 values; its Ed25519 signature is checked before updates. On 25 November 2026 the Ed25519 signature of the live manifest (model pack 1.5.0, channel stable) was verified with the app's own updater code. Models and the app have separate versions. The 11 October 2026 review recorded a built Microsoft Store MSIX 2.0.6000.0; that is a historical record, not a Store-package check for this release.

## Security reports

Contact **lindapro.support@proton.me** privately with the app/model versions, platform and minimal reproduction. Do not send licence keys, confidential texts or unredacted personal information. Use synthetic examples where possible. No guaranteed response time, bounty or third-party certification is promised.

## Deployment boundary

For CLI/server deployment, configure authentication, access control, retention and wrapper logs yourself. Do not apply the desktop network/history statement to a hosted service. The built-in local API is not a full enterprise access-control platform.
