<p align="center"><img src="docs/brand/readme_banner.png" alt="Linda - local AI-text detector" width="100%"></p>

# Linda — local AI-text detector (English, Polish, Russian)

Free for personal non-commercial use, **paid for commercial use** - one licence covers the app, the command-line tools and the models ([LICENSING.md](LICENSING.md), [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md), contact lindapro.support@proton.me). Runs on your machine: no cloud, no API.
Weights live on Hugging Face: [Lindarixon/Linda-Pro](https://huggingface.co/Lindarixon/Linda-Pro) (ensemble, GPU recommended) and
[Lindarixon/Linda-Stylo-Clean](https://huggingface.co/Lindarixon/Linda-Stylo-Clean) (CPU only, strictly clean data lineage).

<!-- release-2300:start -->
## Latest Windows update: 2.5.0.5

[Download the Windows release](https://github.com/Lendarixon/Linda/releases/tag/v2.5.0.5) · [Release notes](https://github.com/Lendarixon/Linda/releases/tag/v2.5.0.5) · **[Try the online demo](https://ninjagovlad--linda-pro-demo-web.modal.run/)**

App **2.5.0.5** with model pack **1.5.0** (token-level markup, automatic installer-selected licensed packs):
- **DirectML stability:** adaptive VRAM budget for 4 GB and 8 GB GPUs, model eviction before token-markup loading, and Windows cp1251 error decoding instead of masked `UnicodeDecodeError`.
- **Humanizer-Full 4B on NVIDIA:** automatic detector VRAM release, on-demand PyTorch `cu128` CUDA runtime installation, and universal hybrid GPU+CPU offload via `accelerate` for 4–8.9 GB VRAM cards (including RTX 5060 8 GB).
- **Russian Humanizer quality:** token-based CPU generation budget (cap 420) to prevent mid-paragraph truncation, plus completeness, numeral-agreement, and glued-word guards.

Prefer at least 300 words of continuous prose; results do not prove authorship.
<!-- release-2300:end -->

<!-- release-2062:start -->
## Previous update: 2.0.6.2

[Download the Windows release](https://github.com/Lendarixon/Linda/releases/tag/v2.0.6.2) · [Release notes](desktop/RELEASE_NOTES_2.0.6.2.md) · **[Try the online demo](https://ninjagovlad--linda-pro-demo-web.modal.run/)**

Clear warnings before analysis, safer uploads and model-folder moves, improved cancellation and diagnostic metadata. Model pack 1.3.4, tokenizers and thresholds are unchanged. Prefer at least 300 words of continuous prose; lists, forms and slide text may be unsuitable. Results do not prove authorship and small AI inserts can be missed.

The online demo processes your text on Modal servers; do not submit confidential material. It provides 12 successful checks, with a shared-network daily limit; up to 6,000 characters, TXT/MD/DOCX. The desktop app processes text locally and has no demo quota.
<!-- release-2062:end -->

## Also from this project

[Linda Probe](https://lendarixon.github.io/Linda/probe.html?utm_source=github) is a Windows app that searches file names and the text inside documents on your own PC. Pro adds OCR for scanned PDFs and search by meaning.

## Windows app (no Python needed)
Get it from the [Microsoft Store](https://apps.microsoft.com/detail/9NP66G69BQPN), or download **Linda-Setup.exe** from the [releases page](https://github.com/Lendarixon/Linda/releases/latest), install it and start it: the app downloads the models once (about 2.9 GB), then works offline, highlights the AI-looking passages and updates its models by itself. Free for personal non-commercial use; a commercial licence key ($10 person, $30 team of 10, $500 per year organization) covers the app, the command line and the models together ([how licensing works](LICENSING.md)). Source of the app: [desktop/](desktop).

<!-- lite:start -->
## Two versions: Linda Assay and Linda Loupe
The same app, two sets of models. Install either one or both; the installer asks, and Settings let you change it later (the app also works with only one of them).
* **Linda Loupe**: a small, fast model for any computer, including old laptops without a graphics card. Slightly less accurate.
* **Linda Assay**: the full ensemble, the most accurate; best with a modern graphics card.
Not sure? Take Lite: it runs everywhere, and Linda Assay can be added later.

| | Linda Assay | Linda Loupe |
|---|---|---|
| Texts rewritten by 16 "humanizers" (HumanizerBench), found | 81.0% | 69.4% |
| Newer humanizer texts (Oct 2026), found | 84.0% | 75.8% |
| Texts of three unseen AI generators, found | 95.5% | 83.0% |
| Polish AI texts found (false alarms) | 79.4% (1.4%) | 72.2% (1.5%) |
| Russian AI texts found (false alarms) | 80.3% (0.6%) | 77.3% (1.2%) |
| False alarms, non-native exam essays (TOEFL) | 5.5% | 2.2% |
| False alarms, human texts of a mixed set (MAGE) | 2.0% | 0.4% |
| Full-check runtime (different control lengths; see note) | 2.0.6.0: 22.14 s for a 10,594-word local control on RX 9070 XT; other hardware and text lengths vary | about 3 s for a full check with highlighting on a Ryzen 7 7800X3D (about 12 s on an office Ryzen 5 PRO 2400GE, estimate) |
| Download | about 2.9 GB | about 0.3 GB |
| Graphics card | recommended | not needed |

Recommended computer:

| | Linda Loupe | Linda Assay |
|---|---|---|
| System | Windows 10 / 11, 64-bit | Windows 10 / 11, 64-bit |
| Processor | any 4-core processor from about 2017 | 4 cores or more |
| Memory (RAM) | 4 GB (8 GB is comfortable) | 8 GB (16 GB recommended) |
| Graphics card | not needed | DirectX 12 GPU with 8 GB recommended; FP32 uses more memory, 4 GB is not validated for 2.0.6.0; CPU fallback is slower |
| Free disk space | 2 GB | 6 GB (an SSD is better) |

Our own measurements on public test sets (English, Polish, Russian), not an independent audit; one calibration rule for both versions. The full Linda Assay needed 226 s for a 3,800-word text on an office Ryzen 5 PRO 2400GE; Lite is expected to take a few seconds there (not measured on that processor yet).
Lite weights have their own repository: [Lindarixon/Linda-Pro-Lite](https://huggingface.co/Lindarixon/Linda-Pro-Lite). From Python: `python download_models.py --set lite` (or `--set both`), then `python -m linda_pro file.txt --lite` (`--tier full|lite|auto` picks explicitly; `auto` uses the full set when it is installed).

The online demo also has a **Stylize** button (rewrite a whole text, the AI-looking sentences, or your selection; it does not hide authorship). Its adapters are public: [Lindarixon/Linda-Stylizer](https://huggingface.co/Lindarixon/Linda-Stylizer) (CC BY-NC-4.0, same terms as the detectors; meaning is not verified automatically).
<!-- lite:end -->

## Speed (historical previous precision route)

The table below is retained as historical evidence; it is not a current app 2.0.6.0 FP32 measurement.
The whole ensemble on one text, measured on one machine (AMD Ryzen 7 7800X3D, 6 CPU threads; GPU: AMD Radeon RX 9070 XT through DirectML in the Windows app). Older laptops are slower. Scores on CPU and GPU differ slightly (about 0.1 on a scale where the AI line is near 0); verdicts matched on our checks.

| text length | GPU (DirectML) | CPU, quick look | CPU, careful look |
|---|---:|---:|---:|
| 300 words | 0.08 s | 0.8 s | 2.1 s |
| 1,000 words | 0.25 s | 2.7 s | 5.7 s |
| 3,000 words | 0.76 s | 8.4 s | 20 s |

Earlier timings and the 1.6 GB GPU estimate describe the previous precision route; they are not validated requirements for Assay FP32 in app 2.0.6.0. 8 GB VRAM is recommended; 4 GB is unvalidated.

## Test it on YOUR texts (nothing leaves your machine)
The weights are public on Hugging Face: [Lindarixon/Linda-Pro](https://huggingface.co/Lindarixon/Linda-Pro) (no login needed).
```bash
pip install -r requirements.txt
python download_models.py                              # full set (~5.8 GB: English + Polish/Russian voices) into ./models; --set lite for Lite (~0.3 GB)
python -m linda_pro my_text.txt --windows               # verdict + per-window scores (mixed authorship); language is detected automatically
python evaluate.py --human my_human_texts/ --ai my_ai_texts/ --mode precise   # accuracy on your own labelled samples
```
`evaluate.py` takes two folders of `.txt` files (or a JSONL with `text` and `label` fields), prints AUROC, true/false positive rates for the `ai` verdict
and for `ai or uncertain`, and writes `evaluation_report.csv`. Use **at least 100 texts per class, preferably 300+ words each**; texts by non-native writers are a good stress test.
From Python: `from linda_pro import load_detector; load_detector("sensitive").detect([text])` (add `tier="lite"` or `tier="full"` to choose; a tier that is not installed raises `FileNotFoundError`).

## No GPU? Google Colab
Open `colab/Linda_Pro_demo.ipynb` in Colab (free T4 is enough), run all cells, paste or upload your texts.

## What it is
Historical full-tier weights introduced in 1.3.1 (current app 2.5.0.5; model package 1.5.0). Three voters: stylometry (CPU) and two transformers, Linda-Essay-M (DeBERTa-v3-large) and Linda-Multi-M (mDeBERTa-v3-base), each a weight-interpolated "merge" of three fine-tuned checkpoints; one decision rule per language (English, Polish, Russian). The language is detected automatically. Version 1.3.1 was retrained **without any text generated by Llama 3.x models**; earlier versions (1.1, 1.3.0) used some, see [DATA_BOM.md](docs/DATA_BOM.md).
Text is cut into ~300-word windows; verdict `ai` / `uncertain` / `human`, `ai_share` (rough share of AI-looking text) and per-window scores. Modes: `sensitive` (default) and `precise` (fewer false accusations for schools/universities).
Results, limits and data provenance: [EVIDENCE_PACK.md](docs/EVIDENCE_PACK.md), [DATA_BOM.md](docs/DATA_BOM.md), [MODEL_CARD.md](docs/MODEL_CARD.md).

Short version (`sensitive` mode, our own evaluation, not an independent audit):
* English: on HumanizerBench (not used for training) 81.0% of 1,675 humanized texts are flagged `ai` (1.1: 69.9%; 1.0: 31.4%); on the held-out October 2026 cycle of the AI Humanizer Benchmark 84.0%; on three unseen modern generators 95.5%.
* Public Chicago Booth benchmark: plain AI 99.8% (Pangram 99.9, GPTZero 98.6, Originality 94.2), after StealthGPT 88.0% (Pangram 98.1, GPTZero 44.3, Originality 29.1). We are **not** better than Pangram on humanized text.
* Russian and Polish (our own small test sets, 350 AI + 350 human texts each): the `ai` verdict catches 80.3% of Russian AI texts at 0.6% false flags and 79.4% of Polish at 1.4%; texts rewritten by another model to look human are caught 59% (Russian) and 56% (Polish) of the time. Sets are small (about +-5 points). No comparison with other detectors was measured for these languages.
* False flags on human texts: 0.2-0.4% on general, school and adult-learner English sets, but **5.5% on TOEFL essays by non-native writers** and 2.0% on the MAGE human subset (1.3.0 had 0.9%). Precise mode lowers false flags (TOEFL 1.1% in 1.3.0; not re-measured for 1.3.1).
Never use a verdict as the sole basis for decisions about people.

Deployment (hardware, offline install, local HTTP service `python -m linda_pro.server`): [DEPLOYMENT.md](docs/DEPLOYMENT.md). Data flow, integrity check, dependencies: [SECURITY.md](docs/SECURITY.md).

## Commercial licence, custom calibration on your texts, integration
lindapro.support@proton.me — describe the use case, volume and languages.

## Citation

If you use Linda Assay or Linda Loupe, please cite the technical report for version 1.5.0 (Zenodo, DOI [10.5281/zenodo.24430711](https://doi.org/10.5281/zenodo.24430711), [record](https://zenodo.org/records/24430711)). Earlier reports: version 1.3.2, [10.5281/zenodo.23261670](https://doi.org/10.5281/zenodo.23261670); version 1.3.1, [10.5281/zenodo.23242014](https://doi.org/10.5281/zenodo.23242014); version 1.1, [10.5281/zenodo.23080472](https://doi.org/10.5281/zenodo.23080472); version 1.0, [10.5281/zenodo.23072494](https://doi.org/10.5281/zenodo.23072494).

```bibtex
@techreport{manzyuk2026linda150,
  title     = {Linda 1.5.0: two local paths for AI-text detection and token-level markup in English, Polish and Russian},
  author    = {Manzyuk, Vladyslav},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.24430711}
}
```

Application 2.5.0.5: [release notes](https://github.com/Lendarixon/Linda/releases/tag/v2.5.0.5). Model pack 1.5.0.

## Current trust and evaluation documents

App 2.5.0.5 / model pack 1.5.0. [Trust statement](docs/TRUST.md), [benchmark brief](docs/BENCHMARK_BRIEF.md), [free organization pilot](docs/PILOT_EN.md). Historical benchmark percentages are not a fresh full evaluation of app 2.5.0.5.

## Free 14-day commercial evaluation

Free commercial evaluation lasts 14 calendar days from first launch, without a paid key, registration or automatic billing. This is a licence condition; the app does not enforce a timer. Continued commercial use then needs a paid licence. Personal non-commercial use stays free without a time limit. See [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md) for the full grant.

