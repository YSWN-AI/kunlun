"""Vibe Writer 单元测试"""

import pytest

from kunlun.vibe_writer import IntentRouter, VibeContext, VibeIntent, VibeWriter

pytestmark = pytest.mark.unit

class TestIntentRouter:
    def setup_method(self):
        self.router = IntentRouter()

    def test_detect_intent_continue(self):
        intent, confidence = self.router.detect_intent("继续写")
        assert intent == VibeIntent.CONTINUE
        assert confidence > 0

    def test_detect_intent_rewrite(self):
        intent, confidence = self.router.detect_intent("重写这段")
        assert intent == VibeIntent.REWRITE
        assert confidence > 0

    def test_detect_intent_battle(self):
        intent, confidence = self.router.detect_intent("激烈的战斗")
        assert intent == VibeIntent.ACTION
        assert confidence > 0

    def test_detect_mood_tense(self):
        mood = self.router.detect_mood("紧张压抑的气氛")
        assert mood is not None

    def test_detect_mood_dark(self):
        mood = self.router.detect_mood("黑暗沉重")
        assert mood is not None

    def test_detect_intent_empty(self):
        intent, confidence = self.router.detect_intent("")
        assert isinstance(intent, VibeIntent)
        assert 0.0 <= confidence <= 1.0

    def test_unknown_intent_default(self):
        intent, _confidence = self.router.detect_intent("xyzxyzxyz")
        assert intent == VibeIntent.CONTINUE  # 默认意图


class TestVibeWriter:
    def setup_method(self):
        self.vibe = VibeWriter(book_id="test")

    def test_set_and_get_context(self):
        ctx = VibeContext(chapter_title="第一章")
        self.vibe.set_context(ctx)
        result = self.vibe.get_context()
        assert result is not None
        assert result.chapter_title == "第一章"

    def test_write_without_context(self):
        response = self.vibe.write("继续写下一段")
        assert response.response_id.startswith("vibe_")
        assert isinstance(response.intent, VibeIntent)
        assert response.word_count == 0  # 无LLM调用时word_count为0

    def test_write_returns_response(self):
        response = self.vibe.write("写一段战斗场景")
        assert response.generated_text == ""  # 无LLM调用
        assert len(response.suggestions) > 0

    def test_context_defaults(self):
        ctx = VibeContext()
        assert ctx.chapter_title == ""
        assert ctx.current_text == ""
