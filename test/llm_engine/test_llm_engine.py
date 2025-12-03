# test/llm_engine/test_llm_engine.py
from __future__ import annotations

import traceback

from wiki2video.llm_engine.client import get_engine


def _print_header(name: str):
    print("\n" + "=" * 80)
    print(f"TEST: {name}")
    print("=" * 80)


def test_llm_engine_basic():
    engine = get_engine()

    # ---------------------------------------------------------
    # (1) 测试基础 chat()
    # ---------------------------------------------------------
    _print_header("chat() basic")
    try:
        res = engine.chat([{"role": "user", "content": "Say hello."}])
        print("chat() output:", res["content"][:200])
    except Exception:
        traceback.print_exc()
        assert False, "chat() failed"

    # ---------------------------------------------------------
    # (2) 测试 ask_text()
    # ---------------------------------------------------------
    _print_header("ask_text()")
    try:
        text = engine.ask_text("Tell me one fact about the ocean.")
        print("ask_text() output:", text[:200])
    except Exception:
        traceback.print_exc()
        assert False, "ask_text() failed"


def test_llm_engine_template():
    engine = get_engine()
    category = "test_prompt"
    key = "test_prompt"
    ref = f"{category}.{key}"

    _print_header("ask_template() with registry")
    try:
        text = engine.ask_template(
                template_ref=ref,
                variables={"topic": "Quantum Computing"},
        )
        print("ask_template(registry) output:", text[:200])
    except Exception:
        traceback.print_exc()
        assert False, "ask_template() with registry failed"


def run_all():
    print("\n\n================ RUNNING LLM ENGINE TEST SUITE ================\n")
    test_llm_engine_basic()
    test_llm_engine_template()
    print("\n🎉 All tests attempted.\n")


if __name__ == "__main__":
    run_all()
