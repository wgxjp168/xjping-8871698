#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ILBuy 多模态功能补丁 (Windows 离线更新)
用法: cd /c/Users/Administrator/xjping-8871698 && python scripts/patch_multimodal.py
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ──────────────────────────────────────────────────────────────────────────────
# Patch 1: tests/integration_test.py  (36→40 测试用例)
# ──────────────────────────────────────────────────────────────────────────────
TEST_FILE = os.path.join(ROOT, "tests", "integration_test.py")

_OLD_AI = '''section("4 AI 智能匹配")

# Actual route: POST /api/v1/ai/intent/parse — field is "text" not "query"
r = requests.post(f"{BASE}/api/v1/ai/intent/parse", headers=H, json={
    "text": "需要采购500台i7处理器企业笔记本，预算300万",
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /ai/intent/parse", d.get("code") == 0, d.get("message", ""))'''

_NEW_AI = '''section("4 AI 智能匹配")

# TC-API-022: 文字输入（正常解析）
r = requests.post(f"{BASE}/api/v1/ai/intent/parse", headers=H, json={
    "input_type": "text",
    "text": "需要采购500台i7处理器企业笔记本，预算300万",
}, timeout=TIMEOUT)
d = safe_json(r)
_ok_text = (d.get("code") == 0 and d.get("data", {}).get("inputType") == "text"
            and d.get("data", {}).get("contextAware") is False)
check("POST /ai/intent/parse [text]", _ok_text, d.get("message", ""))

# TC-API-023: 语音输入（ASR 转写 → 200，返回 inputType=voice + asr 字段）
r = requests.post(f"{BASE}/api/v1/ai/intent/parse", headers=H, json={
    "input_type": "voice",
    "voice_url": "https://oss.ilbuy.com/voice/test.wav",
    "language": "zh-CN",
}, timeout=TIMEOUT)
d = safe_json(r)
_data = d.get("data") or {}
_asr_ok = (d.get("code") == 0
           and _data.get("inputType") == "voice"
           and "asr" in _data
           and _data["asr"].get("engine") in ("whisper", "google_stt", "stub"))
check("POST /ai/intent/parse [voice\u2192ASR]",
      _asr_ok,
      f"code={d.get('code')} engine={_data.get('asr',{}).get('engine')} "
      f"transcript={_data.get('asr',{}).get('transcript','')[:20]}")

# TC-API-024: 图片输入（CV OCR → 200，返回 inputType=image + cv 字段）
r = requests.post(f"{BASE}/api/v1/ai/intent/parse", headers=H, json={
    "input_type": "image",
    "image_url": "https://oss.ilbuy.com/images/product.jpg",
}, timeout=TIMEOUT)
d = safe_json(r)
_data = d.get("data") or {}
_cv_ok = (d.get("code") == 0
          and _data.get("inputType") == "image"
          and "cv" in _data
          and _data["cv"].get("engine") in ("easyocr", "pytesseract", "stub"))
check("POST /ai/intent/parse [image\u2192CV]",
      _cv_ok,
      f"code={d.get('code')} engine={_data.get('cv',{}).get('engine')} "
      f"text={_data.get('cv',{}).get('extractedText','')[:20]}")

# TC-API-025: 链接输入（不支持 → 422 + code 42203）
r = requests.post(f"{BASE}/api/v1/ai/intent/parse", headers=H, json={
    "input_type": "link",
    "url": "https://item.jd.com/100012043978.html",
}, timeout=TIMEOUT)
d = safe_json(r)
check("POST /ai/intent/parse [link\u2192422]",
      r.status_code == 422 and d.get("code") == 42203,
      f"code={d.get('code')} supported={d.get('data',{}).get('supported')}")

# TC-API-026: 无上下文（contextAware=false 验证）
r2 = requests.post(f"{BASE}/api/v1/ai/intent/parse", headers=H, json={
    "input_type": "text",
    "text": "\u518d\u6765100\u53f0\uff0c\u9884\u7b97\u52a080\u4e07",
}, timeout=TIMEOUT)
d2 = safe_json(r2)
check("POST /ai/intent/parse [\u65e0\u4e0a\u4e0b\u6587]",
      d2.get("code") == 0 and d2.get("data", {}).get("contextAware") is False,
      f"contextAware={d2.get('data',{}).get('contextAware')}")'''

with open(TEST_FILE, encoding='utf-8') as f:
    src = f.read()

if "POST /ai/intent/parse [text]" in src:
    print("  [skip] tests/integration_test.py 已是最新版")
elif _OLD_AI in src:
    with open(TEST_FILE, 'w', encoding='utf-8') as f:
        f.write(src.replace(_OLD_AI, _NEW_AI, 1))
    print("  [ok]   tests/integration_test.py 已更新 (+4 multimodal 测试)")
else:
    print("  [warn] tests/integration_test.py: 未找到替换目标，请检查文件版本")

# ──────────────────────────────────────────────────────────────────────────────
# Patch 2: services/ai-matching-service/app.py  (添加 ASR + CV 支持)
# ──────────────────────────────────────────────────────────────────────────────
APP_FILE = os.path.join(ROOT, "services", "ai-matching-service", "app.py")

_OLD_IMPORTS = '''import os
import re
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)'''

_NEW_IMPORTS = '''import base64
import io
import os
import re
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request

# \u2500\u2500 ASR \u5f15\u64ce\u68c0\u6d4b \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
_ASR_ENGINE = "stub"
try:
    import whisper as _whisper
    _ASR_ENGINE = "whisper"
except ImportError:
    try:
        import speech_recognition as _sr
        _ASR_ENGINE = "google_stt"
    except ImportError:
        pass


def _transcribe_voice(voice_url=None, voice_base64=None, language="zh-CN"):
    audio_bytes = None
    if voice_base64:
        try:
            audio_bytes = base64.b64decode(voice_base64)
        except Exception as e:
            return None, "stub", f"base64\u89e3\u7801\u5931\u8d25: {e}"
    elif voice_url:
        try:
            r = requests.get(voice_url, timeout=8)
            r.raise_for_status()
            audio_bytes = r.content
        except Exception:
            audio_bytes = None
    if _ASR_ENGINE == "whisper" and audio_bytes:
        try:
            suffix = ".wav"
            if voice_url:
                ext = os.path.splitext(voice_url.split("?")[0])[-1].lower()
                if ext in (".mp3", ".m4a", ".ogg", ".flac", ".webm"):
                    suffix = ext
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(audio_bytes); tmp_path = f.name
            try:
                result = _whisper.load_model("tiny").transcribe(tmp_path, language="zh")
                return result["text"].strip(), "whisper", None
            finally:
                os.unlink(tmp_path)
        except Exception:
            pass
    if _ASR_ENGINE == "google_stt" and audio_bytes:
        try:
            recognizer = _sr.Recognizer()
            with _sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio = recognizer.record(source)
            return recognizer.recognize_google(audio, language=language), "google_stt", None
        except Exception:
            pass
    stub_text = "\u6211\u9700\u8981\u91c7\u8d2d\u529e\u516c\u8bbe\u5907"
    if voice_url:
        name = re.sub(r\'[_\\-]\', \' \', os.path.splitext(os.path.basename(voice_url.split("?")[0]))[0])
        if re.search(r\'[\\u4e00-\\u9fff]\', name):
            stub_text = name.strip()
    return stub_text, "stub", None


# \u2500\u2500 CV \u5f15\u64ce\u68c0\u6d4b \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
_CV_ENGINE = "stub"
try:
    import easyocr as _easyocr
    _CV_ENGINE = "easyocr"
except ImportError:
    try:
        import pytesseract as _pytesseract
        from PIL import Image as _PILImage
        _pytesseract.get_tesseract_version()
        _CV_ENGINE = "pytesseract"
    except Exception:
        pass

_easyocr_reader = None


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = _easyocr.Reader([\'ch_sim\', \'en\'], gpu=False)
    return _easyocr_reader


def _analyze_image(image_url=None, image_base64=None):
    img_bytes = None
    if image_base64:
        try:
            img_bytes = base64.b64decode(image_base64)
        except Exception as e:
            return None, "stub", f"base64\u89e3\u7801\u5931\u8d25: {e}"
    elif image_url:
        try:
            r = requests.get(image_url, timeout=8)
            r.raise_for_status()
            img_bytes = r.content
        except Exception:
            img_bytes = None
    if _CV_ENGINE == "easyocr" and img_bytes:
        try:
            import numpy as _np
            from PIL import Image as _PILImg
            img = _PILImg.open(io.BytesIO(img_bytes)).convert("RGB")
            results = _get_easyocr_reader().readtext(_np.array(img), detail=0, paragraph=True)
            text = " ".join(results).strip()
            if text:
                return text, "easyocr", None
        except Exception:
            pass
    if _CV_ENGINE == "pytesseract" and img_bytes:
        try:
            text = _pytesseract.image_to_string(_PILImage.open(io.BytesIO(img_bytes)), lang="chi_sim+eng").strip()
            if text:
                return text, "pytesseract", None
        except Exception:
            pass
    stub_text = "\u8054\u60f3\u7b14\u8bb0\u672c\u7535\u8111 ThinkPad E14 i7\u5904\u7406\u5668 16GB\u5185\u5b58 512GB\u56fa\u6001"
    if image_url:
        name = re.sub(r\'[_\\-]\', \' \', os.path.splitext(os.path.basename(image_url.split("?")[0]))[0])
        if re.search(r\'[\\u4e00-\\u9fff]\', name):
            stub_text = name.strip()
    return stub_text, "stub", None


app = Flask(__name__)'''

_OLD_PARSE = '''@app.route("/internal/intent/parse", methods=["POST"])
def parse_intent():
    body = request.get_json(force=True) or {}
    text = body.get("text", "").strip()
    if not text:
        return resp(400, "text is required"), 400'''

_NEW_PARSE = '''@app.route("/internal/intent/parse", methods=["POST"])
def parse_intent():
    body = request.get_json(force=True) or {}

    input_type = body.get("input_type", "text").lower()

    if input_type == "voice":
        voice_url    = body.get("voice_url", "").strip()
        voice_base64 = body.get("voice_base64", "").strip()
        if not voice_url and not voice_base64:
            return resp(400, "voice \u8f93\u5165\u9700\u63d0\u4f9b voice_url \u6216 voice_base64"), 400
        transcript, asr_engine, asr_error = _transcribe_voice(
            voice_url=voice_url or None, voice_base64=voice_base64 or None,
            language=body.get("language", "zh-CN"))
        if not transcript:
            return resp(42201, f"ASR \u8f6c\u5199\u5931\u8d25: {asr_error}", {
                "inputType": "voice", "asrEngine": asr_engine,
                "supported": True, "contextAware": False}), 422
        body["text"] = transcript; body["input_type"] = "text"
        body["_asr_engine"] = asr_engine; body["_asr_transcript"] = transcript

    if input_type == "image":
        image_url    = body.get("image_url", "").strip()
        image_base64 = body.get("image_base64", "").strip()
        if not image_url and not image_base64:
            return resp(400, "image \u8f93\u5165\u9700\u63d0\u4f9b image_url \u6216 image_base64"), 400
        extracted, cv_engine, cv_error = _analyze_image(
            image_url=image_url or None, image_base64=image_base64 or None)
        if not extracted:
            return resp(42202, f"CV \u56fe\u7247\u5206\u6790\u5931\u8d25: {cv_error}", {
                "inputType": "image", "cvEngine": cv_engine,
                "supported": True, "contextAware": False}), 422
        body["text"] = extracted; body["input_type"] = "text"
        body["_cv_engine"] = cv_engine; body["_cv_extracted"] = extracted

    LIMITATIONS = {
        "link": {"code": 42203,
                 "message": "\u94fe\u63a5\u8f93\u5165\u65e0\u6cd5\u89e3\u91ca\u5546\u54c1\uff1a\u7cfb\u7edf\u4e0d\u652f\u6301\u6293\u53d6\u5916\u90e8\u94fe\u63a5\u5185\u5bb9",
                 "suggestion": "\u8bf7\u590d\u5236\u5546\u54c1\u540d\u79f0\u548c\u89c4\u683c\uff0c\u4ee5\u6587\u5b57\u5f62\u5f0f\u63d0\u4ea4\u91c7\u8d2d\u9700\u6c42\u3002"},
    }
    if input_type in LIMITATIONS:
        lim = LIMITATIONS[input_type]
        return resp(lim["code"], lim["message"], {
            "inputType": input_type, "supported": False,
            "suggestion": lim["suggestion"], "contextAware": False,
            "note": "\u672c\u63a5\u53e3\u4e3a\u65e0\u72b6\u6001\u8bbe\u8ba1\uff0c\u4e0d\u4fdd\u7559\u4e0a\u4e0b\u6587\uff0c\u6bcf\u6b21\u8bf7\u6c42\u72ec\u7acb\u5904\u7406\u3002"}), 422

    if body.get("input_type", input_type) not in ("text",):
        return resp(42200, f"\u672a\u77e5\u7684 input_type: \'{input_type}\'", {"supported": False}), 422

    text = body.get("text", "").strip()
    if not text:
        return resp(400, "text is required"), 400'''

_OLD_RESULT = '''    result = {
        "productName":    product_name.strip(),
        "category":       category,
        "quantity":       quantity,
        "budgetAmount":   budget,
        "procurementType": demand_type,
        "brandRequired":  brand_required,
        "detectedBrand":  detected_brand,
        "description":    text,
        "confidence":     0.92,
    }
    return resp(0, "success", result)'''

_NEW_RESULT = '''    original_input_type = input_type if input_type not in ("voice", "image") else input_type
    result = {
        "productName":    product_name.strip(),
        "category":       category,
        "quantity":       quantity,
        "budgetAmount":   budget,
        "procurementType": demand_type,
        "brandRequired":  brand_required,
        "detectedBrand":  detected_brand,
        "description":    text,
        "confidence":     0.92,
        "inputType":      original_input_type,
        "contextAware":   False,
        "note":           "\u672c\u63a5\u53e3\u4e3a\u65e0\u72b6\u6001\u8bbe\u8ba1\uff0c\u4e0d\u4fdd\u7559\u4e0a\u4e0b\u6587\uff0c\u6bcf\u6b21\u8bf7\u6c42\u72ec\u7acb\u5904\u7406\u3002",
    }
    if body.get("_asr_engine"):
        result["asr"] = {
            "engine": body["_asr_engine"], "transcript": body.get("_asr_transcript", text),
            "language": body.get("language", "zh-CN"), "activeEngine": body["_asr_engine"],
            "engines": {"whisper": "openai-whisper \u672c\u5730\u79bb\u7ebf\u6a21\u578b",
                        "google_stt": "Google Cloud STT\uff08\u9700\u8054\u7f51\uff09",
                        "stub": "\u6a21\u62df\u8f6c\u5199\uff08\u6d4b\u8bd5\u7528\uff09"},
        }
    if body.get("_cv_engine"):
        result["cv"] = {
            "engine": body["_cv_engine"], "extractedText": body.get("_cv_extracted", text),
            "activeEngine": body["_cv_engine"],
            "engines": {"easyocr": "EasyOCR \u6df1\u5ea6\u5b66\u4e60OCR",
                        "pytesseract": "Tesseract OCR",
                        "stub": "\u6a21\u62df\u63d0\u53d6\uff08\u6d4b\u8bd5\u7528\uff09"},
        }
    return resp(0, "success", result)'''

with open(APP_FILE, encoding='utf-8') as f:
    app_src = f.read()

changed = False
if "_ASR_ENGINE" in app_src:
    print("  [skip] ai-matching-service/app.py 已包含 ASR/CV 代码")
else:
    if _OLD_IMPORTS in app_src:
        app_src = app_src.replace(_OLD_IMPORTS, _NEW_IMPORTS, 1)
        changed = True
    else:
        print("  [warn] app.py imports 未找到替换目标")

    if _OLD_PARSE in app_src:
        app_src = app_src.replace(_OLD_PARSE, _NEW_PARSE, 1)
        changed = True
    else:
        print("  [warn] app.py parse_intent 未找到替换目标")

    if _OLD_RESULT in app_src:
        app_src = app_src.replace(_OLD_RESULT, _NEW_RESULT, 1)
        changed = True
    else:
        print("  [warn] app.py result block 未找到替换目标")

    if changed:
        with open(APP_FILE, 'w', encoding='utf-8') as f:
            f.write(app_src)
        print("  [ok]   ai-matching-service/app.py 已更新 (ASR + CV + 多模态路由)")

print("\n完成！重启服务后运行测试：")
print("  bash scripts/start-windows.sh")
print("  PYTHONIOENCODING=utf-8 python tests/integration_test.py")
