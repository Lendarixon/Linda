# Linda-Pro 1.0 — deployment guide (on-premises, English texts)

Everything runs inside your infrastructure. No network calls at inference time, no telemetry, no accounts.

## 1. Requirements

| | Minimum (works, slower) | Reference (measured) |
|---|---|---|
| CPU | 8 cores, x86-64 | any modern desktop CPU |
| RAM | 16 GB | 32 GB |
| GPU | none (see note on CPU below) | AMD Radeon RX 9070 XT, 16 GB (ROCm PyTorch) |
| GPU memory | — | peak 4.9 GB allocated, ~5.9 GB reserved (all three voters resident) |
| Disk | 4 GB | package 2.7 GB (Essay v3 1.6 GB, Multi v2 1.1 GB, stylometry < 0.1 GB) |
| Python | 3.10+ | 3.13 |

NVIDIA CUDA GPUs use the same code path (`device="cuda"`); we have measured only the AMD card above.
CPU-only mode (`--device cpu`) works but **we have not measured its speed**; expect it to be an order of magnitude slower than GPU
on the two transformer voters. Stylometry alone (CPU) takes about 5 ms per text.

## 2. Measured speed (reference machine, all three voters, resident in memory, `sensitive` mode)

| Text length | Time per text |
|---|---|
| 500 words (2 windows) | 0.07 s |
| 1,500 words (5 windows) | 0.16 s |
| 3,600 words (12 windows) | 0.37 s |
| batch of 32 × 500 words | 0.05 s per text (≈ 20 texts/s) |
| cold start (load 3 models) | ≈ 30 s once per process |

Texts are cut into ~300-word windows (max 12), so cost grows linearly to ~3,600 words and is flat beyond (longer text is sampled by the 12 windows).
Single-process, sequential; scale horizontally by running more processes/machines. Numbers are from one machine and one run — measure on your hardware.

## 3. Install (also works offline)

```
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt   # for AMD GPUs install the ROCm build of torch first
python -m pytest tests -q         # optional self-test
python -m linda_pro essay.txt --windows
```

Air-gapped install: on a connected machine run `pip download -r requirements.txt -d wheels`, copy the `wheels` folder and this package,
then `pip install --no-index --find-links wheels -r requirements.txt`. The models are files in `models/`; nothing is downloaded at runtime.
Optional readers for `.docx`/`.pdf`: `pip install python-docx pypdf`.

Verify integrity of the package against the shipped checksums (`CHECKSUMS.sha256`) before first use — see `SECURITY.md`.

## 4. Use

**Python:**
```python
from linda_pro import LindaPro
det = LindaPro(mode="sensitive")      # or "precise" for schools/universities (fewer false accusations)
r = det.detect(["text one", "text two"])[0]
r["verdict"], r["ai_share"], r["windows"]   # verdict: ai | uncertain | human; per-window scores
```

**Command line:** `python -m linda_pro file.txt [--mode precise] [--windows] [--json]`

**Local HTTP service** (for embedding into your platform or an LTI gateway; models stay in memory between requests):
```
python -m linda_pro.server --port 8080 --token <secret> [--mode precise] [--device cuda]
curl -H "Authorization: Bearer <secret>" -d "{\"texts\":[\"...\"]}" http://127.0.0.1:8080/v1/detect
```
Listens on 127.0.0.1 by default (it refuses to start on another address without `--token`). If you expose it beyond the host, put it behind your own TLS reverse proxy and network controls;
the built-in service provides only a bearer token, request-size limit (20 MB, 64 texts) and no logging of request texts.
Requests are processed one at a time.

## 5. Choosing the mode

* `sensitive` — flags a text as AI if the Essay voter **or** the ensemble is above the 0.5 % false-positive threshold.
* `precise` — flags AI only if two independent signals agree (Essay above the 1 % threshold **and** stylometry above the 5 % threshold). Recommended when a false accusation is costly. Catches noticeably fewer AI texts (see `EVIDENCE_PACK.md`).

Thresholds come from held-out human texts (`calibration/`). Domain shift (non-native English, unusual genres) changes the false-positive rate:
see the ESL/TOEFL rows in `EVIDENCE_PACK.md`. If your texts differ from the calibration domains, recalibrate on your own human texts.
A verdict is a screening signal and must not be the sole basis for a decision about a person.

## 6. Operations

* **Updating:** the package is versioned (`VERSION`); a new release replaces the folder, calibration and models together.
* **Monitoring:** `GET /health`. Watch GPU memory; run one service process per GPU.
* **Language coverage:** English only in this release. Russian/Polish are not supported in Linda-Pro 1.0.
* **Known limits:** paraphrasing/humanizer tools reduce recall; machine translation of English text is detected poorly.
