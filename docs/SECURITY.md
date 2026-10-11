# Linda — privacy, limitations and release integrity

Updated 11 October 2026. Windows app 2.0.6.0; model pack 1.3.4. This is a technical vendor statement, not independent security certification.

## Your texts and local storage

The Windows desktop application performs detection on your computer. It does not upload checked texts for inference. It can save texts, results and drafts locally. History can be disabled and retention configured; delete unneeded checks and exports using the application and your organization's policy. Current Windows source uses DPAPI protection for stored text/results. This does not protect against someone controlling your signed-in Windows account, nor does it imply every exported report or file is encrypted. Exports and backups remain your responsibility.

The default legacy EXE profile is `%LOCALAPPDATA%/Linda-Pro`. A Store package uses its package LocalState. Models can be stored in a separately selected folder. The CLI/core library is a separate deployment mode: it does not have the desktop application's automatic history or updater, but CLI output files, wrapper services and operator logs can still retain data.

## Network connections

Desktop network activity includes Hugging Face model downloads and signed-manifest checks; GitHub installer downloads; and Polar licence activation, deactivation and periodic validation (about weekly). Polar receives the licence key, organization/activation identifiers, a random display label and a machine-derived identifier hash. The current implementation hashes a salted Windows MachineGuid; the machine name and original GUID are not sent by this path. Network providers can see connection metadata such as IP addresses. Paid licence state can be cached offline; this does not mean the desktop app never attempts a network connection after activation. Payment data is handled by Polar/its payment processors, under their policies.

The static information site has no configured analytics or tracking cookies in its current source. GitHub Pages and linked services have their own infrastructure logs. **Modal/HF hosted demos are different:** using them sends the submitted text to the hosted service for processing. Use the installed desktop app for confidential texts; do not equate demo processing with local offline privacy.

## Appropriate use and limitations

Linda is a screening aid for English, Polish and Russian, with `ai`, `uncertain` and `human` outcomes. **Do not use its score, highlighting or report as the sole evidence of authorship or the sole basis for disciplinary, academic, employment or legal decisions about a person.** Review the original text, drafting evidence and context, and allow a response from its author. Human text may be flagged and AI text may be missed. Short texts, small AI inserts, mixed authorship, human-edited AI and non-native/formulaic prose are difficult cases. Global document confidence is not the percentage of AI-written words. Local colouring can disagree with the global score and with another detector.

Published historical benchmark numbers are developer measurements; current 2.0.6.0 checks establish numerical and UI consistency, not independent population accuracy. Assay uses FP32 stable DirectML on Windows; Loupe runs on CPU. Assay's memory use increased; 8 GB GPU memory is recommended and 4 GB compatibility is unvalidated. No SOC 2, ISO 27001, independent penetration-test certification or formal SLA is claimed.

## Verify your release

Official release: [Linda 2.0.6.0](https://github.com/Lendarixon/Linda/releases/tag/v2.0.6.0). Installer `Linda-Setup.exe`: **286,398,840 bytes**, SHA-256 **`23a3d3afdcebb59e0bb48271392ba470d75b1a2b6a66cf41016d8fa1b73510ad`**. Windows PowerShell: `Get-FileHash -Algorithm SHA256 .\Linda-Setup.exe`; compare the entire hash. The hash is useful when obtained from a trusted independent source; it is not an Authenticode publisher signature. The current installer is not Authenticode signed.

The [model manifest](https://huggingface.co/Lindarixon/Linda-Pro/resolve/main/latest.json) contains file sizes and SHA-256 values; its Ed25519 signature is checked before updates. The live signature was verified for this pack. Models and the app have separate versions. A Microsoft Store MSIX 2.0.6000.0 is built, but this pack does not claim that version is Store-certified or installed-package tested.

## Security reports

Contact **lindapro.support@proton.me** privately with the app/model versions, platform and minimal reproduction. Do not send licence keys, confidential texts or unredacted personal information. Use synthetic examples where possible. No guaranteed response time, bounty or third-party certification is promised.

## Deployment boundary

For CLI/server deployment, configure authentication, access control, retention and wrapper logs yourself. Do not apply the desktop network/history statement to a hosted service. The built-in local API is not a full enterprise access-control platform.
