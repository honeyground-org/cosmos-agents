"""유튜브 도우미가 사람에게 하는 말 — **영어가 원문이고 번역은 여기 모인다**.

## 왜 이 파일이 있나

이 에이전트가 코스모스 저장소 안에 있던 동안에는 문구가 코어 카탈로그
(`cosmos/i18n/*.json`)에 살았고, 코어의 그물이 *"다섯 언어에 답이 있는가"* 를
검사해 주었다. 마켓으로 나온 지금 그 그물의 눈은 코어 소스만 본다 — 즉 ★여기서
새 문구를 쓰면 아무도 검사하지 않고, 그 언어 사용자는 조용히 영어를 본다★.

그래서 번역을 **에이전트가 지고 다닌다**(쇼핑·항공권·Lingua가 하는 것과 같다).
검사도 함께 온다: `tests/test_i18n.py`가 이 표와 실제 호출을 대조한다.

## 구조 — 코어와 **같은 규칙**이다

    영어 원문이 키 · 언어별 표가 값 · 없으면 **영어가 그대로** 나온다

빈칸으로 두지 않는 이유: 빈 문자열은 사용자가 **고장으로 읽는다**.

⚠️ ★래퍼를 만들지 마라★ 화면 문구를 `i18n_t(...)` 같은 우리 함수로 감쌌다가
번역 수집기가 **못 보는** 일이 있었다(수집기는 `i18n.t(...)` 모양을 찾는다).
우회로를 만들면 그 우회로는 **검사도 피한다** — 부를 때는 `i18n.t(...)` 그대로다.
"""
from __future__ import annotations

LANGUAGES = ("ko", "ja", "de", "es", "fr")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ko": {
        "Anyone can see it": "누구나 볼 수 있어요",
        "Channels you come back to": "자주 보시는 채널",
        "It has been a day since you last published.": "마지막으로 올리신 지 하루 됐어요.",
        "It has been {days} days since you last published.": "마지막으로 올리신 지 {days}일 됐어요.",
        "Nothing yet. When you upload through me I will keep the title and the tags, and hand them back next time.":
            "아직 없어요. 저를 통해 올리시면 제목과 태그를 기억해 뒀다가 다음번에 꺼내 드릴게요.",
        "Only people with the link": "링크가 있는 사람만",
        "Only you": "나만 볼 수 있어요",
        "What you have published": "올리신 것",
        "You published today.": "오늘 올리셨어요.",
        "{n} times": "{n}번",
    },
    "ja": {
        "Anyone can see it": "誰でも見られます",
        "Channels you come back to": "よく見るチャンネル",
        "It has been a day since you last published.": "最後に公開してから1日経ちました。",
        "It has been {days} days since you last published.": "最後に公開してから{days}日経ちました。",
        "Nothing yet. When you upload through me I will keep the title and the tags, and hand them back next time.":
            "まだありません。私を通してアップロードすれば、タイトルとタグを覚えておいて次回お渡しします。",
        "Only people with the link": "リンクを知っている人だけ",
        "Only you": "自分だけ",
        "What you have published": "公開したもの",
        "You published today.": "今日公開されました。",
        "{n} times": "{n}回",
    },
    "de": {
        "Anyone can see it": "Für alle sichtbar",
        "Channels you come back to": "Kanäle, zu denen Sie zurückkehren",
        "It has been a day since you last published.":
            "Seit Ihrer letzten Veröffentlichung ist ein Tag vergangen.",
        "It has been {days} days since you last published.":
            "Seit Ihrer letzten Veröffentlichung sind {days} Tage vergangen.",
        "Nothing yet. When you upload through me I will keep the title and the tags, and hand them back next time.":
            "Noch nichts. Wenn Sie über mich hochladen, merke ich mir Titel und Tags und gebe sie beim nächsten Mal zurück.",
        "Only people with the link": "Nur mit dem Link",
        "Only you": "Nur Sie",
        "What you have published": "Was Sie veröffentlicht haben",
        "You published today.": "Sie haben heute veröffentlicht.",
        "{n} times": "{n} Mal",
    },
    "es": {
        "Anyone can see it": "Cualquiera puede verlo",
        "Channels you come back to": "Canales a los que vuelves",
        "It has been a day since you last published.":
            "Ha pasado un día desde tu última publicación.",
        "It has been {days} days since you last published.":
            "Han pasado {days} días desde tu última publicación.",
        "Nothing yet. When you upload through me I will keep the title and the tags, and hand them back next time.":
            "Nada todavía. Cuando subas algo a través de mí guardaré el título y las etiquetas, y te las devolveré la próxima vez.",
        "Only people with the link": "Solo quien tenga el enlace",
        "Only you": "Solo tú",
        "What you have published": "Lo que has publicado",
        "You published today.": "Has publicado hoy.",
        "{n} times": "{n} veces",
    },
    "fr": {
        "Anyone can see it": "Visible par tous",
        "Channels you come back to": "Chaînes que vous revoyez",
        "It has been a day since you last published.":
            "Cela fait un jour depuis votre dernière publication.",
        "It has been {days} days since you last published.":
            "Cela fait {days} jours depuis votre dernière publication.",
        "Nothing yet. When you upload through me I will keep the title and the tags, and hand them back next time.":
            "Rien pour l'instant. Quand vous publierez via moi, je garderai le titre et les tags et vous les rendrai la prochaine fois.",
        "Only people with the link": "Seulement avec le lien",
        "Only you": "Vous seulement",
        "What you have published": "Ce que vous avez publié",
        "You published today.": "Vous avez publié aujourd'hui.",
        "{n} times": "{n} fois",
    },
}


def t(text: str, /, lang: str | None = None, **params) -> str:
    """영어 원문을 사용자의 언어로. 모르면 **영어가 그대로** 나온다.

    ★빈칸으로 두지 않는다★ 빈 문자열은 사용자가 고장으로 읽는다.

    ★우리 표에 없으면 코어에게 물어본다★ `{n} times`처럼 화면 어휘에 이미 있는
    것은 두 벌로 적지 않는다 — 두 벌이 되면 언젠가 한쪽만 고쳐진다.
    """
    from cosmos.core import i18n as core
    code = lang or core.active()
    row = TRANSLATIONS.get(code, {})
    if text in row:
        return row[text].format(**params) if params else row[text]
    return core.t(text, lang=code, **params)
