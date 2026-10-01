# Data bill of materials — Linda-Pro 1.0 (honest, tiered)

Tier A = open licence permitting commercial use; B = licence not stated / NC / share-alike; C = contains outputs of frontier language models.

## Voter 1 — stylo7e (Tier A, strict-clean)

Training texts: 54008 (AI 21211). Cleanliness filters: `scripts/stylo_strict.py` (audit: forbidden sources and generators 0).

| source:class | texts |
|---|---:|
| llmtrace_cls:human | 6400 |
| llmtrace_cls:ai | 6158 |
| raid_clean:human | 5942 |
| raid_clean:ai | 5891 |
| llmtrace_det:human | 5658 |
| en_science:human | 2709 |
| en_thinktank:human | 2693 |
| en_fiction:human | 2677 |
| owner_fanfic:ai | 2392 |
| llmtrace_det:ai | 2347 |
| gen_mirror:ai | 2298 |
| llmtrace_long:human | 1684 |
| gutenberg_en:human | 1254 |
| human_tech_python_enhancement_proposals:human | 901 |
| human_tech_regulations:human | 901 |
| human_tech_arxiv_abstracts:human | 900 |
| human_tech_usgpo:human | 900 |
| longform_mix:ai | 741 |
| longform_qwen3-8b:ai | 647 |
| perturbed_ai:ai | 430 |
| longform_batch:ai | 194 |
| human_tech_uk_hansard:human | 178 |
| gen_humanize:ai | 50 |
| en_fiction:ai | 41 |
| en_thinktank:ai | 22 |

AI text generators (only open weights with permissive licenses: gpt-oss-20b Apache-2.0, Gemma-4-12b, etc.):

| generator | texts |
|---|---:|
| Qwen/Qwen3-32B | 1515 |
| zai-org/GLM-4-32B-0414 | 1480 |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-32B | 1478 |
| qwen3-8b | 1457 |
| tiiuae/Falcon3-10B-Instruct | 1403 |
| gpt2 | 1393 |
| Qwen/Qwen2.5-72B-Instruct | 1370 |
| gemma-4-12b | 1289 |
| mistralai/Magistral-Small-2507 | 1259 |
| mistral | 1232 |
| llama-chat | 1202 |
| mistral-chat | 1198 |
| mpt | 1153 |
| gpt-oss-20b | 1103 |
| qwen3-8b/mirror | 785 |
| gpt-oss-20b/humanlike | 566 |
| gpt-oss-20b/plain | 565 |
| gemma-4-12b/plain | 327 |
| gemma-4-12b/humanlike | 314 |
| qwen3-8b/humanize | 50 |
| qwen3-8b/prompted | 41 |
| gpt-oss-20b/prompted | 22 |
| gpt-oss-20b/mirror | 9 |

## Voter 2 — Linda-Essay v3 (Tier C and B)

Base: DeBERTa-v3-large fine-tuned on RAID train (MIT), then continued training on `essay_modern_en` (about 13.5k texts labelled `frontier`: outputs of frontier language models from public datasets and own generations), RAID replay, and the v3 fine-tune set below. Exact counts for the earlier stages are not consolidated (UNKNOWN); see docs/DATA_BOM_LINDA_PRO_DRAFT.md in the source repository.

Fine-tune set v3 (`data/linda/essay_v3_extra.jsonl`):

| source | class | generator | texts |
|---|---|---|---:|
| clean_long_windows | human | human | 2032 |
| fanfic_translate_en_gemma-4-12b | ai | gemma-4-12b | 1289 |
| en_gutenberg | human | human | 700 |
| fanfic_translate_en_gpt-oss-20b | ai | gpt-oss-20b | 652 |
| fanfic_continue_en_gpt-oss-20b | ai | gpt-oss-20b | 452 |
| en_wikisource | human | human | 400 |
| long_gptoss_windows | ai | gpt-oss-20b/humanlike | 291 |
| long_gptoss_windows | ai | gpt-oss-20b/plain | 291 |
| en_essay | human | human | 149 |
| en_fiction | human | human | 140 |

The owner's own fan-fiction (AI drafts edited by the owner) was used only through machine translations and continuations produced by open-weight models (train works only; dev works held out).

## Voter 3 — Linda-Multi v2 (Tier C and B)

mDeBERTa-v3-base fine-tuned on ~667k mixed texts (LLMTrace, AINL-Eval, RAID replay, frontier-model outputs, FineWeb humans). Exact counts: UNKNOWN (see repository draft BOM).

## Calibration and evaluation data (not training)

Human texts before 2022: persuasive/student essays, Gutenberg books, arXiv abstracts, ASAP, ELLIPSE, FineWeb 2016-2021, cc_news, Yelp, PELIC, W&I, long-form books/wiki sources. 15k texts.

## Linda-Pro 1.1 additions (October 2026)
* **Linda-Essay-D and Linda-Multi-D** (Tier C): continued from Essay v3 / Multi v2 on (1) 4,689 AI texts from open-weight models (gpt-oss-120b, qwen3-30b-a3b-fp8, llama-3.1-8b-instruct) generated through a commercial inference API,
  2,344 of them rewritten in "humanizer" styles (Llama licence terms apply); (2) 817 real outputs of commercial AI humanizer tools from two public benchmarks,
  CC BY 4.0: "AI Humanizer Benchmark" (huggingface.co/datasets/ai-humanizer-benchmark/ai-humanizer-benchmark, September 2026 cycle) and the independent humanizer audit record
  (huggingface.co/datasets/AIHumanizerBenchmarks/best-ai-humanizer-independent-benchmark, June-July 2026 cycles) — the source texts of those cycles were written by frontier language models, and the humanizer tools' own terms apply;
  (3) 96 source texts of the same cycles; (4) human texts as in 1.0.
* **Stylo-D** (Tier C, NOT strict-clean): the stylo7e recipe plus the data above. Strict-clean stylometry (stylo7e, Linda-Stylo-Clean) is unchanged and separate.
* **Test only, never trained on:** HumanizerBench (CC BY 4.0, humanizerbench.com), the October 2026 cycle of the AI Humanizer Benchmark, the August 2026 cycle of the independent audit record.
* Calibration v6: the same 14,980 held-out human texts as calibration v5; thresholds recomputed for the new voters.
