# Linda public demo

Live demo: https://ninjagovlad--linda-pro-demo-web.modal.run/

The free hosted demo offers Linda Loupe (compact CPU detector) and Linda Assay (full ensemble on an L4 GPU). It uses the desktop Engine 2.0.6.2 with unchanged scoring and the signed public model pack 1.3.4. Both detectors use the current automatic markup path; document verdict and local sentence labels are distinct signals.

Demo restrictions: 12 successful checks for the signed browser cookie and 12 checks per shared network per UTC day, across both detectors. A shared global limit of 300 successful or pending checks per UTC day bounds cloud capacity. Each check accepts up to 6,000 Unicode code points and requires at least 20 words; 300 words is a recommendation for more reliable results. Uploads accept TXT, MD and DOCX files up to 2,000,000 bytes. PPT, PPTX and PDF are unsupported. Invalid, malformed, unsupported, too-short and overlong input does not reserve a check. DOCX text extraction includes paragraphs and table cells. Model failures attempt to refund a pending reservation; if refund cannot be confirmed, the pending lease expires after ten minutes. If finalization returns an ambiguous error, the computed result is withheld because the durable charge may already have succeeded.

There is no access-code gate or account. A signed, secure, HttpOnly browser cookie identifies a visitor for one year. SQLite transactions on a persistent Modal volume reserve checks before inference and retain completed counts. A keyed hash of the ingress-provided client IP limits each shared network to 12 checks per UTC day, so clearing cookies on that network does not immediately reset usage. This is browser/network accounting, not authenticated per-person identity; shared networks can share a quota. Neither raw IP addresses nor submitted texts are written to the quota database. The demo processes text in Modal; provider processing and retention policies also apply. Do not submit confidential text.

These technical caps apply only to the free hosted demo. The desktop application has no demo quota or character cap. Personal noncommercial use remains free; the 14-day commercial evaluation permission starts at the first application launch and is a licence condition, without changing the application.

## Deployment

Deploy from this repository's root with `modal deploy modal_app.py`. The `linda-models-131` volume must contain every file listed in `modal/model_manifest.json`, including the current `/calibration/routing.json`. Cold starts verify their sizes and SHA-256 hashes before loading a detector. Model weights are not committed to this repository. The application must not fall back to the older embedded routing table.

Configure the named Modal secret `linda-public-demo-session` with a stable random `SESSION_SECRET` of at least 32 characters. Keep it private and preserve it across deploys so existing signed cookies remain valid. The former `linda-demo-access` secret is no longer used. The persistent `linda-public-demo-quota` volume is created automatically; one writer commits each quota transaction before returning.

`GET /health` reports the app, model pack, markup version, available detectors, supported upload formats and demo limits. `GET /api/session` obtains a signed visitor cookie and remaining count. `POST /api/detect` accepts JSON with `text`, `mode` (`sensitive` or `precise`) and `detector` (`loupe` or `assay`). It is intended for the demo page, not a supported batch API. The UI is self-contained, responsive, uses Metro styling, and supports English, Polish and Russian.

Local API and quota tests use synthetic results, without loading models or using a GPU: `python -m pytest tests/test_public_demo.py -q`.
