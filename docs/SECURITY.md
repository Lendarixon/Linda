# Linda-Pro 1.0 — security and data-handling statement

Scope: what this software does with your data and how to verify what you received. This is a technical statement by the vendor,
**not** a third-party certification. Linda-Pro has no SOC 2, ISO 27001 or VPAT report at this time.

## 1. Data flow

```
your text -> [your server: Linda-Pro process] -> verdict + scores -> back to you
```

* Inference is fully local. The code makes no network connections: no telemetry, licence check, update check or model download at runtime.
* Texts are processed in memory. The package does not write texts, scores or logs to disk. The HTTP service (`linda_pro.server`) does not log request bodies or access lines.
* No third-party API or hosted model is used; the models are the files in `models/`.
* Retention, access control and audit logging of texts and results are the responsibility of the system that embeds Linda-Pro.

You can confirm the network claim yourself: run the package on a machine with the network disabled (or under a firewall rule denying outbound traffic); results are identical.

## 2. Integrity of the package

`CHECKSUMS.sha256` lists SHA-256 hashes of every file (code, models, calibration). Verify before use:

```
# Linux/macOS
sha256sum -c CHECKSUMS.sha256
# Windows PowerShell (prints any mismatching file)
Get-Content CHECKSUMS.sha256 | ForEach-Object { $h,$f = $_ -split '\s+\*?',2; if ((Get-FileHash $f -Algorithm SHA256).Hash -ne $h.ToUpper()) { "MISMATCH $f" } }
```
Model weights use the `safetensors` format (no pickle code execution). Stylometry uses a LightGBM text model and an `.npz` array file.
The package is not code-signed.

## 3. Software bill of materials (dependencies)

Direct runtime dependencies (`requirements.txt`); versions the reference build was tested with:

| Package | Tested version |
|---|---|
| torch | 2.13.0 (ROCm build) |
| transformers | 4.57.6 |
| tokenizers | 0.22.2 |
| safetensors | 0.8.0 |
| lightgbm | 4.7.0 |
| scikit-learn | 1.9.1 |
| numpy | 2.5.3 |
| scipy | 1.18.1 |
| pyyaml | 6.0.3 |
| sentencepiece | 0.2.2 |
| tiktoken | 0.14.0 |
| protobuf | 7.36.2 |
| Python | 3.13 |

Optional: `python-docx`, `pypdf` (file readers). The bundled `_vendor/aidetector` module is our own code. Scan dependencies with your usual tools (`pip-audit`, etc.); pin versions in your deployment.

## 4. Local HTTP service

* Binds to 127.0.0.1 by default and refuses to start on any other address without `--token`. The token is compared in constant time. Request limit 20 MB / 64 texts, no request logging.
* No TLS, user management or rate limiting in the built-in service — place it behind your own reverse proxy / API gateway if it is reachable from other hosts.
* Error responses do not echo request contents.

## 5. Models and data provenance

See `DATA_BOM.md` (training data sources, licences, what was used only for calibration/evaluation) and `MODEL_CARD.md`.
Base models: Microsoft DeBERTa-v3-large and mDeBERTa-v3-base (MIT licence).

## 6. Not provided (be aware before procurement)

* Independent security audit or penetration test, SOC 2 / ISO 27001 / VPAT / accessibility statement.
* LTI 1.3 plug-in for LMS platforms. Integration is via the Python API or the local HTTP service above.
* Formal SLA and support process (defined by the licence agreement).

## 7. Vulnerability reports

Contact: lindapro.support@proton.me. Please include the version (`VERSION`) and reproduction steps.
