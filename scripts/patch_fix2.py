#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ILBuy 多模态补丁修复 v2 — 精确替换主 result 返回块
用法: cd /c/Users/Administrator/xjping-8871698 && python scripts/patch_fix2.py
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_FILE = os.path.join(ROOT, "services", "ai-matching-service", "app.py")

with open(APP_FILE, encoding='utf-8') as f:
    src = f.read()

# 检查是否已经修复（主 result 块中有 contextAware）
if 'original_input_type = input_type' in src:
    print("  [skip] result block already patched")
else:
    # 精确匹配旧的内联 return（用 "confidence": 0.92 作为锚点）
    OLD = ('    return resp(0, "success", {\n'
           '        "productName":    product_name.strip(),\n'
           '        "category":       category,\n'
           '        "quantity":       quantity,\n'
           '        "budgetAmount":   budget,\n'
           '        "procurementType": demand_type,\n'
           '        "brandRequired":  brand_required,\n'
           '        "detectedBrand":  detected_brand,\n'
           '        "description":    text,\n'
           '        "confidence":     0.92,\n'
           '    })')

    NEW = ('    original_input_type = input_type if input_type not in ("voice", "image") else input_type\n'
           '    result = {\n'
           '        "productName":    product_name.strip(),\n'
           '        "category":       category,\n'
           '        "quantity":       quantity,\n'
           '        "budgetAmount":   budget,\n'
           '        "procurementType": demand_type,\n'
           '        "brandRequired":  brand_required,\n'
           '        "detectedBrand":  detected_brand,\n'
           '        "description":    text,\n'
           '        "confidence":     0.92,\n'
           '        "inputType":      original_input_type,\n'
           '        "contextAware":   False,\n'
           '        "note":           '
           '"\u672c\u63a5\u53e3\u4e3a\u65e0\u72b6\u6001\u8bbe\u8ba1\uff0c'
           '\u4e0d\u4fdd\u7559\u4e0a\u4e0b\u6587\uff0c'
           '\u6bcf\u6b21\u8bf7\u6c42\u72ec\u7acb\u5904\u7406\u3002",\n'
           '    }\n'
           '    if body.get("_asr_engine"):\n'
           '        result["asr"] = {\n'
           '            "engine": body["_asr_engine"],\n'
           '            "transcript": body.get("_asr_transcript", text),\n'
           '            "language": body.get("language", "zh-CN"),\n'
           '            "activeEngine": body["_asr_engine"],\n'
           '            "engines": {\n'
           '                "whisper":    "openai-whisper \u672c\u5730\u79bb\u7ebf\u6a21\u578b",\n'
           '                "google_stt": "Google Cloud STT\uff08\u9700\u8054\u7f51\uff09",\n'
           '                "stub":       "\u6a21\u62df\u8f6c\u5199\uff08\u6d4b\u8bd5\u7528\uff09",\n'
           '            },\n'
           '        }\n'
           '    if body.get("_cv_engine"):\n'
           '        result["cv"] = {\n'
           '            "engine": body["_cv_engine"],\n'
           '            "extractedText": body.get("_cv_extracted", text),\n'
           '            "activeEngine": body["_cv_engine"],\n'
           '            "engines": {\n'
           '                "easyocr":     "EasyOCR \u6df1\u5ea6\u5b66\u4e60OCR",\n'
           '                "pytesseract": "Tesseract OCR",\n'
           '                "stub":        "\u6a21\u62df\u63d0\u53d6\uff08\u6d4b\u8bd5\u7528\uff09",\n'
           '            },\n'
           '        }\n'
           '    return resp(0, "success", result)')

    if OLD in src:
        src = src.replace(OLD, NEW, 1)
        with open(APP_FILE, 'w', encoding='utf-8') as f:
            f.write(src)
        print("  [ok] result block patched: added inputType/contextAware/asr/cv")
    else:
        # fallback: regex match on the confidence line
        pat = re.compile(
            r'(    return resp\(0, "success", \{.*?"confidence":\s+0\.92,\n    \}\))',
            re.DOTALL)
        m = pat.search(src)
        if m:
            src = src[:m.start()] + NEW + src[m.end():]
            with open(APP_FILE, 'w', encoding='utf-8') as f:
                f.write(src)
            print("  [ok] result block patched via regex")
        else:
            print("  [warn] could not find result block — check app.py manually")
            print("         Look for 'confidence': 0.92 near end of parse_intent()")

print("\n重启服务后运行测试:")
print("  bash scripts/start-windows.sh")
print("  PYTHONIOENCODING=utf-8 python tests/integration_test.py")
