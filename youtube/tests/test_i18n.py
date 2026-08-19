"""★영어가 기본이고, 모든 언어를 지원한다★ — 이 에이전트의 말.

## 왜 에이전트가 자기 번역을 지고 다니나

유튜브 도우미가 코스모스 저장소 안에 있던 동안에는 문구가 코어 카탈로그에 살았고,
코어의 그물이 *"다섯 언어에 답이 있는가"* 를 검사해 주었다. 마켓으로 나온 지금 그
눈은 코어 소스만 본다 — ★여기서 새 문구를 쓰면 아무도 검사하지 않는다★.

그래서 검사도 함께 온다. 이 파일이 지키는 것 넷:

  ① 부르는 문구는 **표에 다 있다**(없으면 그 언어 사용자는 조용히 영어를 본다)
  ② 표에만 있고 **아무도 안 부르는** 문구는 없다(치우지 않으면 계속 는다)
  ③ ★자리표시자를 잃지 않는다★ `{days}`가 빠진 번역은 **정보를 잃은 문장**이다
  ④ ★원문이 영어다★ 키가 한국어면 그 계약은 한국어 개발자만 쓸 수 있다
"""
from __future__ import annotations

import ast
import pathlib
import re

import youtube_i18n
from youtube_i18n import LANGUAGES, TRANSLATIONS

HERE = pathlib.Path(__file__).resolve().parent.parent
SOURCES = ("youtube_scout.py",)


def _spoken() -> set[str]:
    """소스에서 `i18n.t("…")`의 **원문**을 모은다.

    ★문자열을 훑지 않고 구문 나무를 본다★ 여러 줄로 이어 붙인 문구는 정규식으로는
    안 잡히고, 안 잡힌 문구는 **검사받지 않은 채** 나간다.
    """
    found: set[str] = set()
    for name in SOURCES:
        tree = ast.parse((HERE / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "t" and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                found.add(node.args[0].value)
    return found


def _placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{([a-z_]+)\}", text))


def test_the_collector_actually_finds_something():
    """★계측기부터 잰다★ 수집이 깨지면 이 파일은 조용히 아무것도 검사하지 않는다."""
    assert len(_spoken()) >= 8, f"{len(_spoken())}개만 찾았습니다 — 수집이 깨졌습니다"


def test_every_line_we_say_has_all_five_translations():
    """★없으면 그 언어 사용자는 **영어를 본다**★ 영어 사용자를 위해 한 일이
    한국어 사용자에게 후퇴가 되면 그것은 회귀다."""
    missing = [f"{lang}: {text}" for lang in LANGUAGES
               for text in sorted(_spoken()) if text not in TRANSLATIONS[lang]]
    assert not missing, "번역이 빠졌습니다:\n  " + "\n  ".join(missing[:20])


def test_nothing_sits_in_the_table_that_nobody_says():
    """치우지 않으면 표는 계속 는다 — 그리고 다음 사람은 그것이 쓰이는 줄 안다."""
    stale = sorted(set(TRANSLATIONS["ko"]) - _spoken())
    assert not stale, f"아무도 안 부르는 문구가 남아 있습니다: {stale}"


def test_every_language_carries_the_same_lines():
    """한 언어만 채우고 넷을 잊는 것이 가장 흔한 실수다."""
    keys = {lang: set(TRANSLATIONS[lang]) for lang in LANGUAGES}
    base = keys["ko"]
    for lang in LANGUAGES:
        assert keys[lang] == base, f"{lang}에만 있거나 빠진 문구: {keys[lang] ^ base}"


def test_no_translation_loses_a_placeholder():
    """★`{days}`가 빠진 번역은 **정보를 잃은 문장**이다★ 그리고 조용히 그렇게 된다."""
    broken = []
    for lang in LANGUAGES:
        for source, translated in TRANSLATIONS[lang].items():
            if _placeholders(source) != _placeholders(translated):
                broken.append(f"{lang}: {source!r} → {translated!r}")
    assert not broken, "자리표시자가 어긋났습니다:\n  " + "\n  ".join(broken)


def test_the_source_text_is_english():
    """★영어가 원문이다★ 키가 한국어면 그 계약은 한국어 개발자만 쓸 수 있다."""
    korean = [text for text in TRANSLATIONS["ko"]
              if any("가" <= ch <= "힣" for ch in text)]
    assert not korean, f"원문이 한국어입니다: {korean}"


def test_a_language_we_do_not_have_falls_back_to_english_not_to_blank():
    """★빈칸은 사용자가 고장으로 읽는다★"""
    assert youtube_i18n.t("You published today.", lang="pt") == "You published today."
    assert youtube_i18n.t("You published today.", lang="ko") == "오늘 올리셨어요."


def test_a_word_only_the_core_knows_still_comes_back_translated():
    """★두 벌로 적지 않는다★ 화면 어휘는 코어에 있고, 우리 표에 없으면 거기 묻는다."""
    got = youtube_i18n.t("Unknown", lang="ko")
    assert got and got != "Unknown", "코어에 물어보지 않습니다"
