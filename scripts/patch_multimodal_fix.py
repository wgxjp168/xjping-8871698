#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ILBuy 多模态补丁修复 (patch_multimodal.py 的后续修复)
修复两个问题:
  1. URL 下载超时过长 (8s→3s)，防止测试请求超时
  2. parse_intent 结果缺少 inputType/contextAware/asr/cv 字段

用法: cd /c/Users/Administrator/xjping-8871698 && python scripts/patch_multimodal_fix.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_FILE = os.path.join(ROOT, "services", "ai-matching-service", "app.py")

with open(APP_FILE, encoding='utf-8') as f:
    src = f.read()

changed = False

# ── Fix 1: 降低 URL fetch 超时 (8s → 3s) ─────────────────────────────────────
# 避免假 URL 导致 AI 服务响应超时超过测试的 8s 限制
if 'requests.get(voice_url, timeout=8)' in src:
    src = src.replace('requests.get(voice_url, timeout=8)',
                      'requests.get(voice_url, timeout=3)', 1)
    print("  [ok] voice_url timeout: 8s → 3s")
    changed = True
else:
    print("  [skip] voice_url timeout already fixed or not found")

if 'requests.get(image_url, timeout=8)' in src:
    src = src.replace('requests.get(image_url, timeout=8)',
                      'requests.get(image_url, timeout=3)', 1)
    print("  [ok] image_url timeout: 8s → 3s")
    changed = True
else:
    print("  [skip] image_url timeout already fixed or not found")

# ── Fix 2: 替换旧的内联 result 返回，添加多模态字段 ──────────────────────────
_OLD = '''    return resp(0, "success", {
        "productName":    product_name.strip(),
        "category":       category,
        "quantity":       quantity,
        "budgetAmount":   budget,
        "procurementType": demand_type,
        "brandRequired":  brand_required,
        "detectedBrand":  detected_brand,
        "description":    text,
        "confidence":     0.92,
    })'''

_NEW = '''    original_input_type = input_type if input_type not in ("voice", "image") else input_type
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
            "engine": body["_asr_engine"],
            "transcript": body.get("_asr_transcript", text),
            "language": body.get("language", "zh-CN"),
            "activeEngine": body["_asr_engine"],
            "engines": {
                "whisper":    "openai-whisper \u672c\u5730\u79bb\u7ebf\u6a21\u578b",
                "google_stt": "Google Cloud STT\uff08\u9700\u8054\u7f51\uff09",
                "stub":       "\u6a21\u62df\u8f6c\u5199\uff08\u6d4b\u8bd5\u7528\uff09",
            },
        }
    if body.get("_cv_engine"):
        result["cv"] = {
            "engine": body["_cv_engine"],
            "extractedText": body.get("_cv_extracted", text),
            "activeEngine": body["_cv_engine"],
            "engines": {
                "easyocr":     "EasyOCR \u6df1\u5ea6\u5b66\u4e60OCR",
                "pytesseract": "Tesseract OCR",
                "stub":        "\u6a21\u62df\u63d0\u53d6\uff08\u6d4b\u8bd5\u7528\uff09",
            },
        }
    return resp(0, "success", result)'''

if '"inputType":' in src:
    print("  [skip] result block already has inputType field")
elif _OLD in src:
    src = src.replace(_OLD, _NEW, 1)
    print("  [ok] result block: added inputType/contextAware/asr/cv fields")
    changed = True
else:
    print("  [warn] result block not matched — check app.py manually")

if changed:
    with open(APP_FILE, 'w', encoding='utf-8') as f:
        f.write(src)
    print("\n  app.py \u5df2\u4fdd\u5b58\u3002\u91cd\u542f\u670d\u52a1\u540e\u8fd0\u884c\u6d4b\u8bd5\uff1a")
else:
    print("\n  \u65e0\u9700\u4fee\u6539\u3002")

print("  bash scripts/start-windows.sh")
print("  PYTHONIOENCODING=utf-8 python tests/integration_test.py")
