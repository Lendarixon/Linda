# Linda — local AI-text detector (English)

Free for research, **paid for commercial use** ([COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md), contact ninjagovlad@gmail.com). Runs on your machine: no cloud, no API.
Weights live on Hugging Face: [Lindarixon/Linda-Pro](https://huggingface.co/Lindarixon/Linda-Pro) (ensemble, GPU recommended) and
[Lindarixon/Linda-Stylo-Clean](https://huggingface.co/Lindarixon/Linda-Stylo-Clean) (CPU only, strictly clean data lineage).

## Test it on YOUR texts (nothing leaves your machine)
The weights are gated on Hugging Face (free): open [Lindarixon/Linda-Pro](https://huggingface.co/Lindarixon/Linda-Pro), fill in the short access form, then log in once with `huggingface-cli login` (token from your HF account settings).
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
Three voters — stylometry (CPU), Linda-Essay v3 and Linda-Multi v2 (transformers). Text is cut into ~300-word windows; verdict `ai` / `uncertain` / `human`,
`ai_share` (rough share of AI-looking text) and per-window scores. Modes: `sensitive` (default) and `precise` (fewer false accusations for schools/universities).
Results, limits and data provenance: [EVIDENCE_PACK.md](docs/EVIDENCE_PACK.md), [DATA_BOM.md](docs/DATA_BOM.md), [MODEL_CARD.md](docs/MODEL_CARD.md).
Short version: on the public Chicago Booth benchmark plain AI 99.7% (Pangram 99.9, GPTZero 98.6, Originality 94.2), after a humanizer 85% (Pangram 98.1, GPTZero 44.3, Originality 29.1);
we are **not** better than Pangram. English only. Weak spot: exam-style essays by non-native writers (TOEFL 8.8% false `ai` in `sensitive` mode, 1.1% in `precise`).
Never use a verdict as the sole basis for decisions about people.

Deployment (hardware, measured speed, offline install, local HTTP service `python -m linda_pro.server`): [DEPLOYMENT.md](docs/DEPLOYMENT.md). Data flow, integrity check, dependencies: [SECURITY.md](docs/SECURITY.md).

## Commercial licence, custom calibration on your texts, integration
ninjagovlad@gmail.com — describe the use case, volume and languages.
