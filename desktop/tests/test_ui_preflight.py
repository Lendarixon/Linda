"""CPU-only coverage for the desktop text-suitability preflight."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")


def _pure_helpers():
    start = HTML.index("function preflightWordCount(")
    end = HTML.index("\nlet tabs =", start)
    return HTML[start:end]


def _run_assess(text):
    if shutil.which("node") is None:
        pytest.skip("node is required for JS helper behavior tests")
    script = _pure_helpers() + f"\nconsole.log(JSON.stringify(preflightAssess({json.dumps(text, ensure_ascii=False)})));"
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def test_preflight_word_boundaries_are_inclusive_as_requested():
    assert _run_assess(" ".join(["word"] * 19))["belowMinimum"] is True
    assert _run_assess(" ".join(["word"] * 20))["belowMinimum"] is False
    assert _run_assess(" ".join(["word"] * 20))["belowRecommendation"] is True
    assert _run_assess(" ".join(["word"] * 299))["belowRecommendation"] is True
    assert _run_assess(" ".join(["word"] * 300))["belowRecommendation"] is False
    assert _run_assess(" ".join(["word"] * 300))["words"] == 300


def test_whitespace_only_is_zero_words_and_has_no_length_warning():
    result = _run_assess(" \t\r\n   ")
    assert result["words"] == 0
    assert result["belowMinimum"] is False
    assert result["belowRecommendation"] is False


def test_structure_heuristic_uses_only_line_counts_and_markers():
    bullets = "\n".join(["- First short line", "- Second short line", "- Third short line", "- Fourth short line"])
    short_unmarked = "\n".join(["This is a short line with only seven words" for _ in range(6)])
    long_prose = "\n".join(["This is a long continuous prose line with enough ordinary words to exceed twenty words for this structure check." for _ in range(6)])
    rule_words_in_prose = "\n".join(["If a rule must apply, it shall be described in this long complete sentence with enough words to exceed twenty total." for _ in range(6)])
    assert _run_assess(bullets)["structural"] is True
    assert _run_assess(short_unmarked)["structural"] is True
    assert _run_assess(long_prose)["structural"] is False
    assert _run_assess(rule_words_in_prose)["structural"] is False


def test_upload_attempt_invalidates_and_blocks_text_until_edit_or_successful_replacement():
    assert "test(file.name || '')) { blockAnalysisAfterUpload('unsupported'); return; }" in HTML
    start = HTML.index("function blockAnalysisAfterUpload(")
    end = HTML.index("// UPDATE COUNTERS", start)
    block = HTML[start:end]
    assert "tab.uploadBlockReason = reason;" in block
    assert "tab.result = null;" in block
    assert "tabId === activeTabId" in block
    assert "if (currentUploadBlock()) { preflightRefresh(); return; }" in HTML
    assert "tab.uploadBlockReason = '';" in HTML
    assert "textInput.dispatchEvent(new Event('input'));" in HTML
    assert "btnAnalyze.disabled = ij.phase === 'launching' || !!checkCtl || !!uploadCtl || !!currentUploadBlock();" in HTML



def test_failed_supported_upload_keeps_input_and_stays_blocked():
    start = HTML.index("async function handleFileUpload(file)")
    end = HTML.index("// ANALYSIS", start)
    handler = HTML[start:end]
    assert "blockAnalysisAfterUpload('uploadFailed', upTab);" in handler
    assert "typeof data.text !== 'string'" in handler
    assert "textInput.value = data.text;" in handler
    assert "uploadCtl = null;" in handler
    assert "blockAnalysisAfterUpload('uploadFailed');" in handler
    assert "btnAnalyze.disabled = !!currentUploadBlock(); preflightRefresh(); progHide();" in handler
    assert "xhr.onload = () => { let j = {}; try { j = JSON.parse(xhr.responseText); } catch (e) {}" in HTML
    assert "xhr.timeout = 60000;" in HTML
    assert "xhr.ontimeout" in HTML


def test_language_switch_refreshes_copy_and_persistent_upload_error():
    assert "document.addEventListener('linda-i18n', updateCounter);" in HTML
    counter = HTML[HTML.index("function updateCounter() {"):HTML.index("const ownRunning", HTML.index("function updateCounter() {"))]
    assert "preflightRefresh();" in counter
    assert "textInput.value =" not in counter
    assert all(f"  {lang}: {{" in HTML for lang in ("en", "pl", "ru"))
    assert "statusIndicator.textContent = copy[blockedReason] || copy.uploadFailed;" in HTML
    assert "x.uploadBlockReason = '';" in HTML
    assert "statusIndicator.textContent = reason ?" in HTML
    assert "preflightRefresh();" in HTML


def test_post_analysis_short_warnings_use_the_same_300_word_recommendation():
    assert "const _short = _w > 0 && _w < 300;" in HTML
    assert "data-min', 300" in HTML
    assert "if (words && words < 300) warn.push(T('sv_short'" in HTML
    for lang in ("en", "pl", "ru"):
        catalog = json.loads((ROOT / "web" / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        assert "300" in catalog["sv_short"]
        assert "300" in catalog["verdict_short_warn"]


def test_backend_reports_powerpoint_unsupported_with_slide_suitability_context():
    sys.path.insert(0, str(ROOT))
    from linda_desktop.documents import extract
    with pytest.raises(ValueError, match="PowerPoint files are not supported") as error:
        extract("slides.pptx", b"")
    assert "even when exported to PDF" in str(error.value)

