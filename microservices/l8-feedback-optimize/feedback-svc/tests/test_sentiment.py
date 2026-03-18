import pytest
from app.services.sentiment_service import analyze_sentiment, analyze_sentiment_from_rating

def test_positive_sentiment():
    score, label = analyze_sentiment("这个报告非常准确，推荐给所有人！")
    assert label == "POSITIVE"
    assert score >= 0.5

def test_negative_sentiment():
    score, label = analyze_sentiment("报告完全错误，非常糟糕！")
    assert label in ("NEGATIVE", "NEUTRAL")  # snownlp may vary

def test_empty_text():
    score, label = analyze_sentiment("")
    assert label == "NEUTRAL"
    assert score == 0.5

def test_combined_with_high_rating():
    score, label = analyze_sentiment_from_rating(5, "非常满意，推荐！")
    assert label == "POSITIVE"
    assert score > 0.7

def test_combined_with_low_rating():
    score, label = analyze_sentiment_from_rating(1, "很差，不推荐")
    assert label in ("NEGATIVE", "NEUTRAL")
    assert score < 0.5

def test_combined_no_comment():
    score, label = analyze_sentiment_from_rating(4, None)
    assert label == "POSITIVE"
    assert score == pytest.approx(0.75, abs=0.01)
