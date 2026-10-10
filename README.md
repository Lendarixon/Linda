# Linda — local AI-text detector (English, Polish, Russian)

Free for personal non-commercial use, **paid for commercial use** - one licence covers the app, the command-line tools and the models ([LICENSING.md](LICENSING.md), [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md), contact lindapro.support@proton.me). Runs on your machine: no cloud, no API.
Weights live on Hugging Face: [Lindarixon/Linda-Pro](https://huggingface.co/Lindarixon/Linda-Pro) (ensemble, GPU recommended) and
[Lindarixon/Linda-Stylo-Clean](https://huggingface.co/Lindarixon/Linda-Stylo-Clean) (CPU only, strictly clean data lineage).

## Windows app (no Python needed)
Get it from the [Microsoft Store](https://apps.microsoft.com/detail/9NP66G69BQPN), or download **Linda-Setup.exe** from the [releases page](https://github.com/Lendarixon/Linda/releases/latest), install it and start it: the app downloads the models once (about 2.9 GB), then works offline, highlights the AI-looking passages and updates its models by itself. Free for personal non-commercial use; a commercial licence key ($10 person, $30 team of 10, $500 per year organization) covers the app, the command line and the models together ([how licensing works](LICENSING.md)). Source of the app: [desktop/](desktop).

<!-- lite:start -->
## Two versions: Linda-Pro and Linda-Pro Lite
The same app, two sets of models. Install either one or both; the installer asks, and Settings let you change it later (the app also works with only one of them).
* **Linda-Pro Lite**: a small, fast model for any computer, including old laptops without a graphics card. Slightly less accurate.
* **Linda-Pro**: the full ensemble, the most accurate; best with a modern graphics card.
Not sure? Take Lite: it runs everywhere, and Linda-Pro can be added later.

| | Linda-Pro | Linda-Pro Lite |
|---|---|---|
| Texts rewritten by 16 "humanizers" (HumanizerBench), found | 81.0% | 69.4% |
| Newer humanizer texts (Oct 2026), found | 84.0% | 75.8% |
| Texts of three unseen AI generators, found | 95.5% | 83.0% |
| Polish AI texts found (false alarms) | 79.4% (1.4%) | 72.2% (1.5%) |
| Russian AI texts found (false alarms) | 80.3% (0.6%) | 77.3% (1.2%) |
| False alarms, non-native exam essays (TOEFL) | 5.5% | 2.2% |
| False alarms, human texts of a mixed set (MAGE) | 2.0% | 0.4% |
| Full check of a 3,800-word text (with highlighting) | about 4 s with an RX 9070 XT; minutes on a processor alone | about 3 s for a full check with highlighting on a Ryzen 7 7800X3D (about 12 s on an office Ryzen 5 PRO 2400GE, estimate) |
| Download | about 2.9 GB | about 0.3 GB |
| Graphics card | recommended | not needed |

Recommended computer:

| | Linda-Pro Lite | Linda-Pro |
|---|---|---|
| System | Windows 10 / 11, 64-bit | Windows 10 / 11, 64-bit |
| Processor | any 4-core processor from about 2017 | 4 cores or more |
| Memory (RAM) | 4 GB (8 GB is comfortable) | 8 GB (16 GB recommended) |
| Graphics card | not needed | DirectX 12 card with 4 GB of video memory or more; works without it, but slowly |
| Free disk space | 2 GB | 6 GB (an SSD is better) |

Our own measurements on public test sets (English, Polish, Russian), not an independent audit; one calibration rule for both versions. The full Linda-Pro needed 226 s for a 3,800-word text on an office Ryzen 5 PRO 2400GE; Lite is expected to take a few seconds there (not measured on that processor yet).
Lite weights have their own repository: [Lindarixon/Linda-Pro-Lite](https://huggingface.co/Lindarixon/Linda-Pro-Lite). From Python: `python download_models.py --set lite`, then `python -m linda_pro file.txt --lite`.
<!-- lite:end -->

## Speed
The whole ensemble on one text, measured on one machine (AMD Ryzen 7 7800X3D, 6 CPU threads; GPU: AMD Radeon RX 9070 XT through DirectML in the Windows app). Older laptops are slower. Scores on CPU and GPU differ slightly (about 0.1 on a scale where the AI line is near 0); verdicts matched on our checks.

| text length | GPU (DirectML) | CPU, quick look | CPU, careful look |
|---|---:|---:|---:|
| 300 words | 0.08 s | 0.8 s | 2.1 s |
| 1,000 words | 0.25 s | 2.7 s | 5.7 s |
| 3,000 words | 0.76 s | 8.4 s | 20 s |

Model loading at start takes about 5-10 s; the two networks need about 1.6 GB of GPU memory.

## Test it on YOUR texts (nothing leaves your machine)
The weights are public on Hugging Face: [Lindarixon/Linda-Pro](https://huggingface.co/Lindarixon/Linda-Pro) (no login needed).
```bash
pip install -r requirements.txt
python download_models.py                              # downloads the 1.3.1 weights (~2.9 GB) from Hugging Face into ./models
python -m linda_pro my_text.txt --windows               # verdict + per-window scores (mixed authorship); language is detected automatically
python evaluate.py --human my_human_texts/ --ai my_ai_texts/ --mode precise   # accuracy on your own labelled samples
```
`evaluate.py` takes two folders of `.txt` files (or a JSONL with `text` and `label` fields), prints AUROC, true/false positive rates for the `ai` verdict
and for `ai or uncertain`, and writes `evaluation_report.csv`. Use **at least 100 texts per class, 150+ words each**; texts by non-native writers are a good stress test.
From Python: `from linda_pro import load_detector; load_detector("sensitive").detect([text])`.

## No GPU? Google Colab
Open `colab/Linda_Pro_demo.ipynb` in Colab (free T4 is enough), run all cells, paste or upload your texts.

## What it is
Version 1.3.1 (weights; Windows app 2.0.3.x). Three voters: stylometry (CPU) and two transformers, Linda-Essay-M (DeBERTa-v3-large) and Linda-Multi-M (mDeBERTa-v3-base), each a weight-interpolated "merge" of three fine-tuned checkpoints; one decision rule per language (English, Polish, Russian). The language is detected automatically. Version 1.3.1 was retrained **without any text generated by Llama 3.x models**; earlier versions (1.1, 1.3.0) used some, see [DATA_BOM.md](docs/DATA_BOM.md).
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

If you use Linda-Pro or Linda-Pro Lite, please cite the technical report for version 1.3.2 (Zenodo, DOI [10.5281/zenodo.23261670](https://doi.org/10.5281/zenodo.23261670)). Earlier reports: version 1.3.1, [10.5281/zenodo.23242014](https://doi.org/10.5281/zenodo.23242014); version 1.1, [10.5281/zenodo.23080472](https://doi.org/10.5281/zenodo.23080472); version 1.0, [10.5281/zenodo.23072494](https://doi.org/10.5281/zenodo.23072494).

```bibtex
@techreport{manzyuk2026lindapro132,
  title     = {Linda-Pro 1.3.2 and Linda-Pro Lite: two local detectors of AI-generated text in English, Polish and Russian},
  author    = {Manzyuk, Vladyslav},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.23261670}
}
```
