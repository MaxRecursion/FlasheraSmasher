"""Tests for the two bug fixes:
1. Claude prompt bans emojis / special Unicode
2. Hindi tweets are filtered out by _is_hindi() + _filter_and_rank()
"""
import sys
import os
import re
import unicodedata
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Minimal env so config.py doesn't sys.exit() on missing vars
# ---------------------------------------------------------------------------
for _var in [
    "X_CONSUMER_KEY", "X_CONSUMER_SECRET",
    "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "X_BEARER_TOKEN",
    "ANTHROPIC_API_KEY", "NTFY_TOPIC",
]:
    os.environ.setdefault(_var, "stub")

# Stub out third-party packages that aren't available in the test sandbox
# but aren't needed for the logic under test here.
for _mod in ["anthropic", "tweepy", "flask"]:
    sys.modules.setdefault(_mod, MagicMock())

# Make sure the package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.claude_drafter import SYSTEM_PROMPT
from src.feed_scanner import _is_hindi, _filter_and_rank
import src.notifier  # import only — we won't call send_for_approval


# ===========================================================================
# Helper
# ===========================================================================
def _has_emoji(text: str) -> bool:
    """Return True if text contains any emoji / pictograph codepoint."""
    for ch in text:
        cat = unicodedata.category(ch)
        cp = ord(ch)
        # Emoji ranges: Emoticons, Misc Symbols, Supplemental Symbols, Transport
        if cat in ("So", "Sm") or 0x1F300 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27FF:
            return True
    return False


# ===========================================================================
# Fix 1 — Claude prompt
# ===========================================================================
def test_system_prompt_bans_emojis():
    """SYSTEM_PROMPT must not allow emojis (old rule said 'Maximum 1-2 emoji')."""
    assert "emoji" in SYSTEM_PROMPT.lower(), "Prompt should mention 'emoji'"
    assert "NO emojis" in SYSTEM_PROMPT or "no emojis" in SYSTEM_PROMPT.lower(), (
        "Prompt must explicitly ban emojis, got:\n" + SYSTEM_PROMPT
    )
    # Old permissive rule should be gone
    assert "Maximum 1-2 emoji" not in SYSTEM_PROMPT, (
        "Old permissive emoji rule still present in prompt"
    )
    print("  PASS: SYSTEM_PROMPT explicitly bans emojis")


def test_system_prompt_devanagari_only():
    """SYSTEM_PROMPT should mention Devanagari-only restriction."""
    lower = SYSTEM_PROMPT.lower()
    assert "devanagari" in lower, (
        "Prompt should mention Devanagari as the allowed script"
    )
    print("  PASS: SYSTEM_PROMPT mentions Devanagari-only restriction")


def test_system_prompt_itself_has_no_emoji():
    """The prompt text itself should not contain any emoji characters."""
    assert not _has_emoji(SYSTEM_PROMPT), (
        "SYSTEM_PROMPT contains emoji characters — shouldn't be there"
    )
    print("  PASS: SYSTEM_PROMPT contains no emoji characters")


def test_notifier_title_no_emoji():
    """notifier.py title must not start with an emoji (was: '🐦 Reply #...')."""
    import inspect
    import src.notifier as notifier_mod
    source = inspect.getsource(notifier_mod)
    # The old title started with the bird emoji \U0001F426
    assert "\U0001f426" not in source and "🐦" not in source, (
        "notifier.py still contains the 🐦 emoji that caused the latin-1 crash"
    )
    print("  PASS: notifier.py title has no emoji (latin-1 crash fixed)")


# ===========================================================================
# Fix 2 — Hindi filter
# ===========================================================================

# Genuine Hindi tweets (from session data) — all should be detected as Hindi
HINDI_SAMPLES = [
    "आज किसकी की हालत देख शोले मूवी याद आ गई\n\nजानते आप सब लोग हैं कृपया कोई नाम नहीं लगा",
    "@AnilYadavmedia1 बिहार ऐसे ही पीछे है,आज मुझे प्रमोट कीजिए @MrsaurabhBHU",
    "ईरान Vs अमेरिका टकराव के बीच दुनिया में हाहाकार, भारत में संकट क्यों नहीं?",
    "आज अपनी विधानसभा बीकापुर अन्तर्गत नगर पंचायत बीकापुर में उत्तर प्रदेश शासन "
    "द्वारा नामित सभासद गण था थे थी",
    "@bhagatram2020 उसी दिन से गायब है आज आने की कोशिश की लेकिन फिर से गायब",
    "तुम सत्ता के लिए अपना बाप रोज बादलों हम नहीं बदलने वाले",
    "@ShivamSanghi12 त्यागी जो लोग दूसरी पार्टी में रह कर मोदी जी को गालियाँ देते थे",
    "मैं आपसे सहमत हूं, यह बहुत अच्छा काम है",
    "वो काम क्यों नहीं किया जो करना था",
    "उन्होंने कहा कि यह सही नहीं है",
]

# Genuine Marathi tweets — none should be detected as Hindi
MARATHI_SAMPLES = [
    "रावेर लोकसभा अंतर्गत सावदा (रावेर) येथील नगरसेवक श्री. राजेश वानखेडे यांची आई",
    "पुण्यात आज खूप पाऊस पडतोय! रस्त्यावर पाणीच पाणी.",
    "महाराष्ट्र सरकारने नवीन योजना जाहीर केली आहे.",
    "आपण सगळे मिळून हे काम करू शकतो, काळजी नाही.",
    "मराठी भाषा आपली आहे, तिचा अभिमान बाळगा.",
    "मुंबईत आज मोठी गर्दी होती, लोक खूप आनंदात होते.",
    "आमच्या गावी उत्सव साजरा होत आहे.",
    "चांगले शिक्षण घेतले की जीवन सुंदर होते.",
]


def test_hindi_samples_detected():
    """All known Hindi tweets should be classified as Hindi."""
    failures = []
    for text in HINDI_SAMPLES:
        if not _is_hindi(text):
            failures.append(text[:80])
    if failures:
        for f in failures:
            print(f"  MISSED Hindi tweet: {f!r}")
        raise AssertionError(f"{len(failures)}/{len(HINDI_SAMPLES)} Hindi tweets not detected")
    print(f"  PASS: All {len(HINDI_SAMPLES)} Hindi samples correctly identified")


def test_marathi_samples_not_filtered():
    """Genuine Marathi tweets must NOT be classified as Hindi."""
    failures = []
    for text in MARATHI_SAMPLES:
        if _is_hindi(text):
            failures.append(text[:80])
    if failures:
        for f in failures:
            print(f"  FALSE POSITIVE on Marathi: {f!r}")
        raise AssertionError(
            f"{len(failures)}/{len(MARATHI_SAMPLES)} Marathi tweets wrongly classified as Hindi"
        )
    print(f"  PASS: All {len(MARATHI_SAMPLES)} Marathi samples pass through correctly")


def test_empty_and_ascii_not_hindi():
    """Edge cases: empty string and plain ASCII should not be Hindi."""
    assert not _is_hindi(""), "_is_hindi('') should be False"
    assert not _is_hindi("Hello world this is a test"), "ASCII should not be Hindi"
    assert not _is_hindi("https://t.co/abcdef"), "URL should not be Hindi"
    print("  PASS: Edge cases (empty / ASCII) handled correctly")


def _make_tweet(id_, text, followers=5000, likes=100):
    return {
        "id": id_,
        "text": text,
        "author_username": "test",
        "author_name": "Test",
        "author_followers": followers,
        "likes": likes,
        "retweets": 0,
        "quotes": 0,
    }


def test_filter_and_rank_removes_hindi():
    """_filter_and_rank must discard Hindi tweets; Marathi tweets must survive."""
    tweets = [
        _make_tweet("h1", HINDI_SAMPLES[0]),   # Hindi
        _make_tweet("h2", HINDI_SAMPLES[1]),   # Hindi
        _make_tweet("m1", MARATHI_SAMPLES[0]), # Marathi
        _make_tweet("m2", MARATHI_SAMPLES[1]), # Marathi
    ]
    kept, stats = _filter_and_rank(tweets, already_replied=set(), min_followers=0, min_likes=0)
    kept_ids = {t["id"] for t in kept}

    assert "h1" not in kept_ids, "Hindi tweet h1 should have been filtered"
    assert "h2" not in kept_ids, "Hindi tweet h2 should have been filtered"
    assert "m1" in kept_ids, "Marathi tweet m1 should have been kept"
    assert "m2" in kept_ids, "Marathi tweet m2 should have been kept"
    assert stats["hindi_skipped"] == 2, f"Expected 2 hindi_skipped, got {stats['hindi_skipped']}"
    print(f"  PASS: _filter_and_rank discarded {stats['hindi_skipped']} Hindi tweets, "
          f"kept {stats['kept']} Marathi tweets")


def test_filter_stats_include_hindi_skipped():
    """Stats dict must contain 'hindi_skipped' key."""
    _, stats = _filter_and_rank([], already_replied=set(), min_followers=0, min_likes=0)
    assert "hindi_skipped" in stats, f"stats missing 'hindi_skipped' key, got: {list(stats)}"
    print("  PASS: stats dict includes 'hindi_skipped' key")


def test_all_hindi_yields_no_candidates():
    """If every fetched tweet is Hindi, the result should be empty."""
    tweets = [_make_tweet(f"h{i}", text) for i, text in enumerate(HINDI_SAMPLES)]
    kept, stats = _filter_and_rank(tweets, already_replied=set(), min_followers=0, min_likes=0)
    assert kept == [], f"Expected no candidates from all-Hindi batch, got {len(kept)}"
    assert stats["hindi_skipped"] == len(HINDI_SAMPLES)
    print(f"  PASS: All-Hindi batch produces 0 candidates "
          f"({stats['hindi_skipped']} skipped)")


# ===========================================================================
# Runner
# ===========================================================================
if __name__ == "__main__":
    tests = [
        ("prompt: bans emojis",          test_system_prompt_bans_emojis),
        ("prompt: Devanagari-only rule",  test_system_prompt_devanagari_only),
        ("prompt: no emoji in text",      test_system_prompt_itself_has_no_emoji),
        ("notifier: no emoji in title",   test_notifier_title_no_emoji),
        ("hindi: samples detected",       test_hindi_samples_detected),
        ("hindi: marathi not filtered",   test_marathi_samples_not_filtered),
        ("hindi: edge cases",             test_empty_and_ascii_not_hindi),
        ("filter: removes hindi",         test_filter_and_rank_removes_hindi),
        ("filter: stats key present",     test_filter_stats_include_hindi_skipped),
        ("filter: all-hindi → 0 cands",  test_all_hindi_yields_no_candidates),
    ]

    passed = failed = 0
    for name, fn in tests:
        print(f"\n[TEST] {name}")
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
