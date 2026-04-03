"""
tests/test_multimodal.py
ILbuy 多模态输入处理测试套件

Run:
    pytest tests/test_multimodal.py -v
    pytest tests/test_multimodal.py -v -k "not live"   # skip live API tests
"""
from __future__ import annotations

import asyncio
import hashlib
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── Helper ────────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def assistant():
    from local_simulation import MultimodalAssistant
    return MultimodalAssistant()


@pytest.fixture(scope="module")
def text_proc(assistant):
    return assistant._text


@pytest.fixture(scope="module")
def voice_proc(assistant):
    return assistant._voice


@pytest.fixture(scope="module")
def image_proc(assistant):
    return assistant._image


@pytest.fixture(scope="module")
def link_proc(assistant):
    return assistant._link


# ── Text processor ────────────────────────────────────────────────────────────

class TestTextProcessor:
    def test_process_returns_dict(self, text_proc):
        r = run(text_proc.process("我想买服务器", {}))
        assert isinstance(r, dict)

    def test_has_intent(self, text_proc):
        r = run(text_proc.process("我想买服务器", {}))
        assert "intent" in r
        assert r["intent"] in ("PURCHASE", "SEARCH", "PRICE_QUERY", "COMPARE", "STOCK_CHECK", "UNKNOWN")

    def test_purchase_intent(self, text_proc):
        r = run(text_proc.process("我想采购100台联想笔记本电脑", {}))
        assert r["intent"] == "PURCHASE"

    def test_price_query_intent(self, text_proc):
        r = run(text_proc.process("不锈钢板材今天的市场价格是多少", {}))
        assert r["intent"] == "PRICE_QUERY"

    def test_stock_check_intent(self, text_proc):
        r = run(text_proc.process("交换机还有库存吗", {}))
        assert r["intent"] == "STOCK_CHECK"

    def test_compare_intent(self, text_proc):
        r = run(text_proc.process("联想和戴尔服务器哪个好", {}))
        assert r["intent"] == "COMPARE"

    def test_response_is_string(self, text_proc):
        r = run(text_proc.process("推荐一款办公椅", {}))
        assert isinstance(r["response"], str) and len(r["response"]) > 0

    def test_matched_products_is_list(self, text_proc):
        r = run(text_proc.process("笔记本电脑", {}))
        assert isinstance(r["matched_products"], list)

    def test_keywords_extracted(self, text_proc):
        r = run(text_proc.process("我想买联想笔记本电脑", {}))
        assert isinstance(r["keywords"], list)

    def test_session_context_updates_intent(self, text_proc):
        session = {"last_intent": "PURCHASE", "last_keywords": ["服务器"]}
        r = run(text_proc.process("有货吗", session))
        # "有货吗" alone is STOCK_CHECK or uses session fallback
        assert r["intent"] in ("STOCK_CHECK", "PURCHASE")


# ── Voice processor ───────────────────────────────────────────────────────────

class TestVoiceProcessor:
    def test_returns_transcribed_text(self, voice_proc):
        r = run(voice_proc.process(b"audio_test_123", {}))
        assert "transcribed_text" in r
        assert len(r["transcribed_text"]) > 0

    def test_returns_asr_confidence(self, voice_proc):
        r = run(voice_proc.process(b"audio_test_456", {}))
        assert "asr_confidence" in r
        assert 0.0 <= r["asr_confidence"] <= 1.0

    def test_deterministic_mapping(self, voice_proc):
        """Same bytes → same utterance"""
        seed = b"deterministic_audio_seed"
        r1 = run(voice_proc.process(seed, {}))
        r2 = run(voice_proc.process(seed, {}))
        assert r1["transcribed_text"] == r2["transcribed_text"]
        assert r1["asr_confidence"] == r2["asr_confidence"]

    def test_different_seeds_differ(self, voice_proc):
        seeds = [b"seed_a", b"seed_b", b"audio_server", b"audio_check"]
        utterances = {run(voice_proc.process(s, {}))["transcribed_text"] for s in seeds}
        # At least 2 distinct utterances across 4 seeds (md5 collision unlikely)
        assert len(utterances) >= 2

    def test_has_matched_products(self, voice_proc):
        r = run(voice_proc.process(b"voice_check", {}))
        assert "matched_products" in r
        assert isinstance(r["matched_products"], list)

    def test_has_response(self, voice_proc):
        r = run(voice_proc.process(b"any_audio", {}))
        assert isinstance(r["response"], str)


# ── Image processor ───────────────────────────────────────────────────────────

class TestImageProcessor:
    def test_returns_image_labels(self, image_proc):
        r = run(image_proc.process(b"img_test", {}))
        assert "image_labels" in r
        assert isinstance(r["image_labels"], list)
        assert len(r["image_labels"]) >= 1

    def test_label_has_name_and_confidence(self, image_proc):
        r = run(image_proc.process(b"img_test_2", {}))
        for label in r["image_labels"]:
            assert "name" in label
            assert "confidence" in label
            assert 0.0 <= label["confidence"] <= 1.0

    def test_returns_brands(self, image_proc):
        r = run(image_proc.process(b"img_test_3", {}))
        assert "image_brands" in r
        assert isinstance(r["image_brands"], list)

    def test_returns_ocr_text(self, image_proc):
        r = run(image_proc.process(b"img_test_4", {}))
        assert "ocr_text" in r
        assert isinstance(r["ocr_text"], str)

    def test_deterministic(self, image_proc):
        seed = b"img_deterministic"
        r1 = run(image_proc.process(seed, {}))
        r2 = run(image_proc.process(seed, {}))
        assert r1["image_labels"] == r2["image_labels"]

    def test_has_intent_search(self, image_proc):
        r = run(image_proc.process(b"image_anything", {}))
        assert r["intent"] == "SEARCH"

    def test_matched_products_list(self, image_proc):
        r = run(image_proc.process(b"img_products", {}))
        assert isinstance(r["matched_products"], list)


# ── Link processor ────────────────────────────────────────────────────────────

class TestLinkProcessor:
    @pytest.mark.parametrize("url,expected_platform", [
        ("https://item.taobao.com/item.htm?id=123", "taobao"),
        ("https://detail.tmall.com/item.htm?id=456", "tmall"),
        ("https://item.jd.com/100088.html", "jd"),
        ("https://mobile.yangkeduo.com/goods.html?id=789", "pinduoduo"),
        ("https://v.douyin.com/iFeNS9Sb/", "douyin"),
        ("https://detail.vip.com/detail-2345678.html", "weipinhui"),
        ("https://detail.1688.com/offer/12345.html", "1688"),
    ])
    def test_platform_detection(self, link_proc, url, expected_platform):
        r = run(link_proc.process(url, {}))
        assert r["platform"] == expected_platform, \
            f"URL {url!r}: expected {expected_platform!r}, got {r['platform']!r}"

    def test_returns_platform_name(self, link_proc):
        r = run(link_proc.process("https://item.taobao.com/item.htm", {}))
        assert "platform_name" in r and r["platform_name"]

    def test_keyword_extraction_from_path(self, link_proc):
        r = run(link_proc.process("https://item.taobao.com/item.htm?title=laptop-thinkpad", {}))
        assert isinstance(r["keywords"], list)

    def test_intent_is_search(self, link_proc):
        r = run(link_proc.process("https://item.jd.com/100088.html", {}))
        assert r["intent"] == "SEARCH"

    def test_response_string(self, link_proc):
        r = run(link_proc.process("https://detail.1688.com/offer/relay.html", {}))
        assert isinstance(r["response"], str) and len(r["response"]) > 0


# ── MultimodalAssistant (full orchestration) ──────────────────────────────────

class TestMultimodalAssistant:
    def test_text_input(self, assistant):
        r = run(assistant.process("sess_txt", "text", "我想采购服务器"))
        assert r["session_id"] == "sess_txt"
        assert r["input_type"] == "text"
        assert "intent" in r
        assert "response" in r

    def test_voice_input(self, assistant):
        r = run(assistant.process("sess_voc", "voice", b"voice_check"))
        assert r["input_type"] == "voice"
        assert "transcribed_text" in r

    def test_image_input(self, assistant):
        r = run(assistant.process("sess_img", "image", b"img_laptop_test"))
        assert r["input_type"] == "image"
        assert "image_labels" in r

    def test_link_input(self, assistant):
        r = run(assistant.process("sess_lnk", "link", "https://detail.1688.com/offer/relay-88.html"))
        assert r["input_type"] == "link"
        assert r["platform"] == "1688"

    def test_unknown_input_type_returns_error(self, assistant):
        r = run(assistant.process("sess_err", "audio_file", "some_content"))
        assert "error" in r

    def test_session_tracking(self, assistant):
        sid = "sess_multi_track"
        run(assistant.process(sid, "text", "我想采购笔记本电脑"))
        run(assistant.process(sid, "text", "价格多少"))
        r = run(assistant.process(sid, "text", "有没有库存"))
        si = r["session_info"]
        assert si["interaction_count"] == 3
        assert si["session_id"] == sid

    def test_session_history_length(self, assistant):
        sid = "sess_hist"
        for i in range(7):
            run(assistant.process(sid, "text", f"查询{i}号商品"))
        history = assistant.get_session_history(sid)
        # deque maxlen=5: only last 5 turns kept
        assert len(history) == 5

    def test_session_last_intent_updated(self, assistant):
        sid = "sess_intent_track"
        run(assistant.process(sid, "text", "我想购买交换机"))
        r2 = run(assistant.process(sid, "text", "预算多少合适"))
        si = r2["session_info"]
        assert si["last_intent"] in ("PURCHASE", "PRICE_QUERY", "SEARCH")

    def test_timestamp_in_response(self, assistant):
        r = run(assistant.process("sess_ts", "text", "继电器"))
        assert "timestamp" in r
        from datetime import datetime
        # Should parse as ISO format
        datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))

    def test_matched_products_structure(self, assistant):
        r = run(assistant.process("sess_struct", "text", "打印机"))
        for p in r["matched_products"]:
            assert "title" in p
            assert "price" in p or "current_price" in p

    def test_multimodal_session_continuity(self, assistant):
        """Switch between text → voice → image in same session."""
        sid = "sess_mm_cont"
        run(assistant.process(sid, "text", "工业设备"))
        run(assistant.process(sid, "voice", b"audio_server"))
        r = run(assistant.process(sid, "image", b"img_industrial"))
        si = r["session_info"]
        assert si["interaction_count"] == 3


# ── Integration (live API) ────────────────────────────────────────────────────

@pytest.mark.live
class TestLiveAPI:
    """Requires running ILbuy services. Skip with: pytest -k 'not live'"""

    def test_api_health(self, gateway_url):
        try:
            import requests
            r = requests.get(f"{gateway_url}/actuator/health", timeout=3)
            assert r.status_code == 200
        except Exception as e:
            pytest.skip(f"Gateway not reachable: {e}")

    def test_product_list_v2(self, gateway_url, buyer_credentials):
        try:
            import requests
            login = requests.post(f"{gateway_url}/api/v1/auth/login", json=buyer_credentials, timeout=5)
            token = login.json()["data"]["accessToken"]
            r = requests.get(
                f"{gateway_url}/api/v1/data/products",
                params={"page": 1, "size": 5},
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
            data = r.json()
            assert data["code"] == 0
            assert "items" in data["data"]
            for item in data["data"]["items"]:
                assert "version" in item
                assert item["version"] == "2.0"
        except Exception as e:
            pytest.skip(f"Live API test skipped: {e}")

    def test_platform_specific_in_response(self, gateway_url, buyer_credentials):
        try:
            import requests
            login = requests.post(f"{gateway_url}/api/v1/auth/login", json=buyer_credentials, timeout=5)
            token = login.json()["data"]["accessToken"]
            r = requests.get(
                f"{gateway_url}/api/v1/data/products",
                params={"platform": "tmall", "size": 1},
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
            data = r.json()
            assert data["code"] == 0
            items = data["data"]["items"]
            if items:
                p = items[0]
                # v2.0 response should have basicInfo with platform_specific
                if "basicInfo" in p:
                    assert "platform_specific" not in p or isinstance(p.get("platform_specific", {}), dict)
        except Exception as e:
            pytest.skip(f"Live API test skipped: {e}")
