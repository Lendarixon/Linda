<p align="center"><img src="desktop/assets/logo_wordmark.png" alt="Linda-Pro" height="72"></p>

# Linda — local AI-text detector (English)

Free for personal non-commercial use, **paid for commercial use** - one licence covers the app, the command-line tools and the models ([LICENSING.md](LICENSING.md), [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md), contact lindapro.support@proton.me). Runs on your machine: no cloud, no API.
Weights live on Hugging Face: [Lindarixon/Linda-Pro](https://huggingface.co/Lindarixon/Linda-Pro) (ensemble, GPU recommended) and
[Lindarixon/Linda-Stylo-Clean](https://huggingface.co/Lindarixon/Linda-Stylo-Clean) (CPU only, strictly clean data lineage).

## Windows app (no Python needed)
Download **Linda-Setup.exe** from the [releases page](https://github.com/Lendarixon/Linda/releases/latest), install it and start it: the app downloads the models once (about 2.9 GB), then works offline, highlights the AI-looking passages and updates its models by itself. Free for personal non-commercial use; a commercial licence key ($10 person, $30 team of 10, $500 per year organization) covers the app, the command line and the models together ([how licensing works](LICENSING.md)). Source of the app: [desktop/](desktop).

## Speed
The whole ensemble on one text, measured on one machine (AMD Ryzen 7 7800X3D, 6 CPU threads; GPU: AMD Radeon RX 9070 XT through DirectML in the Windows app). Older laptops are slower. Scores on CPU and GPU agree to the third decimal.

| text length | GPU (DirectML) | CPU, colours per ~300-word window | CPU, colours per sentence |
|---|---:|---:|---:|
| 300 words | 0.14 s | 1.1 s | 3.8 s |
| 1,000 words | 0.34 s | 3.5 s | 8.1 s |
| 3,000 words | 0.98 s | 11.9 s | 27 s |

Model loading at start takes about 5-10 s.

## Test it on YOUR texts (nothing leaves your machine)
The weights are public on Hugging Face: [Lindarixon/Linda-Pro](https://huggingface.co/Lindarixon/Linda-Pro) (no login needed).
```bash
pip install -r requirements.txt
python download_models.py                              # downloads the weights (~2.7 GB) from Hugging Face into ./models
python -m linda_pro my_text.txt --windows               # verdict + per-window scores (mixed authorship)
python evaluate.py --human my_human_texts/ --ai my_ai_texts/ --mode precise   # accuracy on your own labelled samples
```
`evaluate.py` takes two folders of `.txt` files (or a JSONL with `text` and `label` fields), prints AUROC, true/false positive rates for the `ai` verdict
and for `ai or uncertain`, and writes `evaluation_report.csv`. Use **at least 100 texts per class, 150+ words each**; texts by non-native writers are a good stress test.

## No GPU? Google Colab
Open `colab/Linda_Pro_demo.ipynb` in Colab (free T4 is enough), run all cells, paste or upload your texts.

## What it is
Three voters — stylometry (CPU), Linda-Essay-D and Linda-Multi-D (transformers); version 1.1, retrained against AI humanizers (1.0 is in the git history, tag `v1.0`). Text is cut into ~300-word windows; verdict `ai` / `uncertain` / `human`,
`ai_share` (rough share of AI-looking text) and per-window scores. Modes: `sensitive` (default) and `precise` (fewer false accusations for schools/universities).
Results, limits and data provenance: [EVIDENCE_PACK.md](docs/EVIDENCE_PACK.md), [DATA_BOM.md](docs/DATA_BOM.md), [MODEL_CARD.md](docs/MODEL_CARD.md).
Short version: on the public Chicago Booth benchmark plain AI 99.7% (Pangram 99.9, GPTZero 98.6, Originality 94.2), after a humanizer 83% (Pangram 98.1, GPTZero 44.3, Originality 29.1); on HumanizerBench (not used for training) 70% of 1,675 humanized texts are flagged `ai` (1.0: 31%);
we are **not** better than Pangram. English is the main language; Russian and Polish work at moderate quality (the network was trained on them, but thresholds are tuned for English: on our test sets the AI verdict catches about 63% of Russian and 51% of Polish AI texts at 0-1% false flags); treat those results as indicative. No comparison with other detectors was measured for these languages. Weak spot: exam-style essays by non-native writers (TOEFL 4.4% false `ai` in `sensitive` mode, 0.0% in `precise`).
Never use a verdict as the sole basis for decisions about people.

Deployment (hardware, measured speed, offline install, local HTTP service `python -m linda_pro.server`): [DEPLOYMENT.md](docs/DEPLOYMENT.md). Data flow, integrity check, dependencies: [SECURITY.md](docs/SECURITY.md).

## Commercial licence, custom calibration on your texts, integration
lindapro.support@proton.me — describe the use case, volume and languages.

## Citation

If you use Linda-Pro 1.1, please cite the technical report (Zenodo, DOI [10.5281/zenodo.23080472](https://doi.org/10.5281/zenodo.23080472)); the report for version 1.0 is [10.5281/zenodo.23072494](https://doi.org/10.5281/zenodo.23072494):

```bibtex
@techreport{manzyuk2026lindapro11,
  title     = {Linda-Pro 1.1: retraining a local AI-text detector against AI humanizers},
  author    = {Manzyuk, Vladyslav},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.23080472}
}
```
