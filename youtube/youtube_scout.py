"""youtube — 찾고, 보고, 요약하고, ★올린다★ (Phase MA ①).

## ★이 파일 하나가 이 에이전트의 전부다★ (Sean 요구 2026-08-11)

> *"모든 에이전트는 **독립적**이고 붙이고 떼고가 쉬워야 함."*

그래서 판정도 기억도 여기 있고 **코어에는 한 줄도 넣지 않았다**. 처음에는
`cosmos/core/youtube.py`로 갈랐다가 되돌렸다 — 그러면 에이전트를 떼어도 코어에
죽은 파일이 남고, 마켓에서 받은 남의 에이전트는 애초에 그 자리를 쓸 수 없다
(설치된 3rd-party는 자기 폴더 안에서 완결된다: `agents/*/`).

기대는 것은 **계약뿐**이다(`contracts.Plugin` · `contracts.memory` · `core.provenance`
· `core.agent_settings` · `core.appauth`). 그것이 "우리 시스템과 호환된다"는 말의 뜻이다.
번역은 옆의 `youtube_i18n.py`가 지고 다닌다 — 코어 카탈로그에 두면 마켓으로 나온 뒤
**새 문구를 아무도 검사하지 않는다**(코어 그물은 코어 소스만 본다).

층은 파일 **안에서** 가른다:

    표(단일 진실원) → 정규형 → ★판정(순수 함수)★ → 기억 → 에이전트

★판정이 순수 함수라야 그물이 잡는다★(29차 교훈) — 네트워크 호출 안에 묻어 두면
낱말만 남기고 동작을 뒤집는 뮤테이션이 그대로 빠져나간다.

## clean-room

업스트림에도 유튜브 액션이 있으나 코드는 열지 않았다. 그쪽은 브라우저를 화면
자동화로 몰고 액션이 넷(재생·요약·정보·인기)이다. ★**업로드는 업스트림에 없다**★
(실측) — 새로 만드는 일이고, Sean 승인으로 **Data API**로 간다. 화면 자동화보다
훨씬 튼튼하고, 무엇보다 *"올렸다"* 가 확실해진다(자동화는 실패해도 모른다).

## ⚠️ 열쇠가 없으면 **그렇게 말한다**

읽기는 API 키 하나, 업로드는 OAuth 셋이 필요하고 그것을 만드는 것은 **사람 일**이다
(Gmail 커넥터와 같다). 조용히 실패하면 사용자는 고장으로 읽는다 — 무엇을 어디에
넣어야 하는지 **문장으로** 답한다(함정 44).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from cosmos.contracts import Plugin, ToolContext
from cosmos.contracts.memory import (Entity, MemoryItem, Relation, Trust,
                                     entity_links, now_ts)
import youtube_i18n as i18n
from cosmos.core import provenance

# 이 채널이 만든 것은 채널 단위로 걷어낼 수 있다(모든 자동 산출물의 규칙).
CHANNEL = "youtube.v1"
ITEM_KIND = "youtube"

_API = "https://www.googleapis.com/youtube/v3"
_UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
_TOKEN = "https://oauth2.googleapis.com/token"
_TIMEOUT = 20
# 업로드는 오래 걸린다 — 짧게 잡으면 다 보내 놓고 실패로 읽는다(그리고 영상은 올라간다).
_UPLOAD_TIMEOUT = 600

# ── 무엇을 할 수 있나 — ★이 표가 단일 진실원이다★(원칙 1) ──────────────────────
#
# 새 액션은 여기 한 줄이다. `needs`가 없으면 자격증명 없이 되고, `remembers`가 참이면
# 브레인에 남는다. 라우팅도 도구 선언의 설명도 이 표에서 나온다.
#
# ⚠️ ★`play`에 `needs`가 없는 것이 요점이다★ — 여는 것은 브라우저가 하므로 키가
# 필요 없다. 키가 없다고 재생까지 막으면, 열쇠를 안 넣은 사람에게 이 에이전트는
# **아무것도 못 하는 물건**으로 보인다.
#
# ## ⚠️ ★칸이 둘인 이유 — `needs`와 `needs_any`★ (2026-08-19)
#
#     needs      **전부** 있어야 한다(그리고)
#     needs_any  ★**하나라도** 있으면 된다★(또는)
#
# 읽기는 API 키로도 되고 구글 연결로도 된다. 이것을 `needs`에 나란히 적으면
# *"둘 다 있어야 한다"* 가 되어, ★버튼을 누른 사람이 키까지 넣어야★ 하고 그러면
# 원클릭이 아니다. 뜻이 다른 두 관계를 한 칸에 뭉치면 반드시 한쪽이 틀린다.
ACTIONS: dict[str, dict] = {
    "search":    {"needs": (), "needs_any": ("api_key", "google"), "remembers": False,
                  "desc": "look for videos"},
    "info":      {"needs": (), "needs_any": ("api_key", "google"), "remembers": True,
                  "desc": "what one video is"},
    "summarize": {"needs": (), "needs_any": ("api_key", "google"), "remembers": True,
                  "desc": "sum a video up"},
    "trending":  {"needs": (), "needs_any": ("api_key", "google"), "remembers": False,
                  "desc": "what is popular right now"},
    "play":      {"needs": (), "remembers": True,
                  "desc": "open it in the browser"},
    # ★필요한 것이 **하나**로 줄었다★(Phase OA) — 사용자가 구글 클라우드에서
    # 세 값을 복사해 오던 자리가 버튼 하나가 됐다.
    "upload":    {"needs": ("google",), "remembers": True,
                  "desc": "put your own video up"},
}
DEFAULT_ACTION = "search"

# ── 공개 범위 — ★fail-closed★ ────────────────────────────────────────────────
#
# 순서가 곧 안전 순서다(좁은 것이 앞). ★모르는 값은 가장 좁은 것으로 떨어진다★ —
# 오타 하나가 남의 영상을 세상에 공개하는 일이 되어서는 안 된다. 월렛과 같은 방향이다.
PRIVACY = ("private", "unlisted", "public")
SAFE_PRIVACY = PRIVACY[0]

# 한 번에 돌려주는 최대 개수. 목록이 길면 말로는 못 읽고 브레인에는 잡음이 된다.
MAX_RESULTS = 8

_ID_LEN = 11
_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
          "music.youtube.com")


# ── 정규형 ───────────────────────────────────────────────────────────────────

@dataclass
class Video:
    """영상 하나의 **정규형** — API가 어느 모양으로 주든 이것으로 옮긴다.

    모르는 것은 **비워 둔다**. 그럴듯하게 채우면 그 값이 화면에서 사실이 된다.
    """

    video_id: str
    title: str = ""
    channel: str = ""
    channel_id: str = ""
    published: str = ""
    description: str = ""
    # ★순간값은 정규형에 담되 **기억에는 안 넣는다**★ 말할 때는 쓸모가 있고
    # (지금 몇 회) 남기면 곧 거짓이 된다 — 그 구별을 `remember_video`가 한다.
    views: int = 0
    tags: tuple[str, ...] = ()

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}" if self.video_id else ""


@dataclass
class UploadPlan:
    """올리기 **전에** 확정되는 것들. 실제 전송은 이 판정을 통과한 뒤에만 일어난다."""

    ok: bool
    privacy: str = SAFE_PRIVACY
    title: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()
    path: str = ""
    reason: str = ""
    # ★요청한 것과 다르게 정했으면 그 사실을 들고 다닌다★ 조용히 좁히면 사용자는
    # 공개된 줄 알고, 조용히 넓히면 되돌릴 수 없다. 둘 다 답에 실어야 한다.
    narrowed: bool = False


# ── 판정 — ★순수 함수★(네트워크도 디스크도 안 만진다) ────────────────────────

def privacy_of(requested: str = "", default: str = "") -> str:
    """공개 범위를 정한다 — ★모르면 가장 좁게★.

    빈 값이면 사용자가 설정에 적어 둔 기본값, 그것도 모르는 값이면 `private`.
    """
    for candidate in (str(requested or "").strip().lower(),
                      str(default or "").strip().lower()):
        if candidate in PRIVACY:
            return candidate
    return SAFE_PRIVACY


def video_ref(text: str) -> str:
    """말이나 주소에서 **영상 id**를 뽑는다. 못 찾으면 빈 문자열(검색어라는 뜻).

    ★주소를 문자열로 자르지 않고 파싱한다★ — `youtube.com`이 **어디에** 있는지가
    중요하다. `https://evil.example/youtube.com/watch?v=…`를 유튜브로 읽으면
    엉뚱한 곳을 여는 길이 열린다.
    """
    raw = str(text or "").strip()
    if not raw:
        return ""
    if _is_id(raw):
        return raw
    from urllib.parse import parse_qs, urlparse

    try:
        parsed = urlparse(raw if "//" in raw else f"https://{raw}")
    except ValueError:
        return ""
    host = (parsed.hostname or "").lower()
    if host not in _HOSTS:
        return ""
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
        return candidate if _is_id(candidate) else ""
    got = parse_qs(parsed.query or "").get("v") or []
    if got and _is_id(got[0]):
        return got[0]
    # /shorts/<id> · /embed/<id> · /live/<id>
    parts = [p for p in (parsed.path or "").split("/") if p]
    if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
        return parts[1] if _is_id(parts[1]) else ""
    return ""


def _is_id(text: str) -> bool:
    """유튜브 영상 id의 모양인가(11자 · URL-safe base64 글자)."""
    if len(text) != _ID_LEN:
        return False
    return all(c.isalnum() or c in "-_" for c in text)


def missing_for(action: str, have) -> tuple[str, ...]:
    """이 액션을 하려면 **무엇이 아직 없는가**. 순서는 `needs` 선언 순서 그대로.

    ★조용한 폴백은 거짓말이다★(함정 44) — 키가 없으면 "안 된다"가 아니라
    **무엇을 넣어야 하는지** 말해야 한다. 그 문장을 만들 재료가 이 반환값이다.
    """
    spec = ACTIONS.get(str(action or ""))
    if not spec:
        return ()
    present = {str(k) for k, v in dict(have or {}).items() if str(v or "").strip()}
    missing = [need for need in spec["needs"] if need not in present]
    # ★`needs_any`는 **하나라도** 있으면 된다★ 하나도 없을 때만 통째로 없다고 한다
    # — 그래야 화면이 *"이 중 하나를 주세요"* 라고 말할 수 있다.
    choices = tuple(spec.get("needs_any") or ())
    if choices and not any(name in present for name in choices):
        missing.extend(choices)
    return tuple(missing)


def plan_upload(path: str, *, title: str = "", description: str = "",
                tags=(), privacy: str = "", default_privacy: str = "",
                exists=None) -> UploadPlan:
    """올릴 수 있는지 **먼저** 판정한다 — 전송은 이것을 통과한 뒤에만.

    ★`exists`를 인자로 받는 이유★ 파일이 있는지는 디스크에 묻는 일이라, 그대로
    두면 이 판정 전체가 임시 파일 없이는 검사할 수 없게 된다. 판정과 세상을
    가르면 그물이 **모든 갈래**를 실제로 지나갈 수 있다.
    """
    from pathlib import Path

    check = exists if callable(exists) else (lambda p: Path(p).is_file())
    clean = str(path or "").strip()
    wanted = privacy_of(privacy, default_privacy)
    asked = str(privacy or "").strip().lower()
    if not clean:
        return UploadPlan(ok=False, privacy=wanted,
                          reason="No file was given to upload.")
    if not check(clean):
        return UploadPlan(ok=False, privacy=wanted, path=clean,
                          reason=f"There is no file at {clean}.")
    name = str(title or "").strip() or Path(clean).stem
    return UploadPlan(
        ok=True, privacy=wanted, path=clean, title=name[:100],
        description=str(description or "").strip()[:5000],
        tags=tuple(str(t).strip() for t in (tags or ()) if str(t).strip())[:20],
        # 사용자가 무언가를 청했는데 표에 없는 낱말이었다면 좁혀진 것이다
        narrowed=bool(asked) and asked != wanted,
    )


def normalize(payload) -> list[Video]:
    """`search.list`든 `videos.list`든 같은 모양으로 옮긴다.

    ★모양이 다른 두 응답을 한 함수가 받는 이유★ 유튜브는 검색 결과의 id를
    `{"id": {"videoId": …}}`로, 영상 조회의 id를 `{"id": "…"}`로 준다. 부르는
    쪽에서 가르면 그 분기가 두 군데로 늘고, 언젠가 한쪽만 고쳐진다.
    """
    items = (payload or {}).get("items") if isinstance(payload, dict) else None
    out: list[Video] = []
    for row in items or []:
        if not isinstance(row, dict):
            continue
        ident = row.get("id")
        vid = ident.get("videoId", "") if isinstance(ident, dict) else str(ident or "")
        snippet = row.get("snippet") if isinstance(row.get("snippet"), dict) else {}
        stats = row.get("statistics") if isinstance(row.get("statistics"), dict) else {}
        if not vid:
            continue
        out.append(Video(
            video_id=str(vid),
            title=str(snippet.get("title") or ""),
            channel=str(snippet.get("channelTitle") or ""),
            channel_id=str(snippet.get("channelId") or ""),
            published=str(snippet.get("publishedAt") or ""),
            description=str(snippet.get("description") or ""),
            views=_as_int(stats.get("viewCount")),
            tags=tuple(str(t) for t in (snippet.get("tags") or ())[:20]),
        ))
    return out[:MAX_RESULTS]


def _as_int(value) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


# ── 기억 (원칙 0) ────────────────────────────────────────────────────────────
#
# *"검색해서 스쳐 본 것"* 과 *"내가 지목해서 본 것"* 은 다르다. 목록을 통째로 남기면
# 브레인은 **내가 보지도 않은 영상들로 채워진다**. `ACTIONS[*].remembers`가 그 경계다.
#
#   ★내가 올린 것 → `item`★  내 자산이다. **이 에이전트의 주다**(Sean 결정)
#   내 채널      → `org`+`mine`  무엇을 만드는 사람인가
#   즐겨 보는 채널 → `org`      ★반복될 때만★ 성향으로 표시된다
#
# ## ⚠️ ★영상 제목을 `topic` 노드로 세우지 않는다★ (Sean 결정 2026-08-19 · 실측)
#
# 원래 이 파일은 영상 제목을 그대로 `topic`으로 세웠고, 주석에 *"제목에 관심사가 가장
# 진하게 들어 있다"* 고 적혀 있었다. **실측이 그 전제를 뒤집었다** — 같은 모양을 이미
# 만들고 있는 `tool.web_search.v1`의 결과를 세어 보니:
#
#     topic 노드 116개 · 그중 ★64개(55%)가 페이지 제목 모양★
#     출처: tool.web_search.v1 95 · sleep.extract.v1 17 · youtube 0
#
# 실제로 쌓인 것들이다 —
#     `고민은 배송만 늦출 뿐.. 나의 첫 맥북 | MacBook Air... - YouTube`
#     `'지금 나로 충분해' 토닥이는 책, 그림이 정말 예쁩니다 - 오마이뉴스`
#     `가성비 역대급 맥북 프로 M5, 성능과 가격의 혁신 | TikTok`
#
# 이것은 관심사가 아니라 **그날 스친 페이지 제목**이다. 평균 42자라 어떤 낱말 검색에도
# 안 걸리고, 사이트 꼬리표(`| TikTok`·`- 오마이뉴스`)가 관심사로 굳는다. 이 에이전트를
# 켜면 **같은 오염을 더 붓는** 것이었다.
#
# ★대신 반복을 센다★ *"한 번은 사건, 반복은 성향이다"*(CLAUDE.md ②). 그리고 세는
# 자리를 새로 만들지 않는다 — 볼 때마다 남는 `MemoryItem`을 **되읽어서** 센다
# (`regulars()`). 새 저장 장치 0개, 판정은 순수 함수다.
#
# 조회수·좋아요는 **남기지 않는다** — 그 순간의 수치라 남기는 순간 거짓이 된다.

# 같은 채널을 이만큼 지목해 봐야 *"즐겨 본다"* 고 말한다. 한 번은 사건이다.
REGULAR_AFTER = 3

# 반복을 셀 때 되읽는 최근 기억의 수. 넉넉하되 무한은 아니다 — 반 년 전 취향을
# 지금 취향으로 치면 그것은 참견이다.
RECENT_WINDOW = 60

def remember_video(brain, user_id: str, video: Video, *, agent=None,
                   watched: bool = False, now: str = "") -> str:
    """지목해서 본 영상 하나를 남긴다 — ★**채널로**, 제목으로가 아니라★.
    만든(또는 갱신한) 채널 노드 id를 돌려준다. 채널을 모르면 빈 문자열.

    ★왜 채널인가★ 채널 이름은 짧고, 반복되고, 지속된다(*"메이커뮤직"*·*"Basic
    Apple Guy"*). 영상 제목은 그 반대다 — 길고, 한 번뿐이고, 낚시 문구와 사이트
    꼬리표가 섞여 있다. 실측으로 확인한 자리다(이 절 머리말).

    ★본 사실 자체는 기억 항목으로 남는다★ 그래야 나중에 *"그 영상 뭐였지"* 가
    낱말로 닿고, ★반복을 셀 재료★가 된다(`regulars`). 그래프 노드가 되는 것과
    기억 항목이 되는 것은 다른 일이다 — 전자는 **길이 되고**, 후자는 **문이 된다**.
    """
    if brain is None or not video or not video.video_id:
        return ""
    stamp = now or now_ts()
    # 확신 0.8 — 채널은 유튜브가 준 사실이지만, *이 사람이 즐겨 보는가* 는 추론이다.
    trust = Trust(confidence=0.8, provenance="extracted", source_channel=CHANNEL)
    made: list[str] = []
    channel_id = ""
    if video.channel:
        channel_id = brain.upsert_entity(user_id, Entity(
            name=video.channel[:120], kind="org",
            attrs={**trust.to_attrs(), "youtube_channel_id": video.channel_id,
                   "last_seen": stamp},
            valid_from=stamp))
        if channel_id:
            made.append(channel_id)
    # ★누가 찾아 온 것인가★(R4) 산출물이 출처 에이전트를 가리킨다 — 그래야
    # 이 에이전트를 뗄 때 그것이 남긴 것을 함께 걷어낼 수 있다(Sean의 "떼기 쉽게").
    if agent is not None and made:
        provenance.record(brain, user_id, agent, made, now=stamp)
    brain.remember(user_id, MemoryItem(
        text=_watch_note(video, watched), kind=ITEM_KIND, ts=stamp,
        # ★반복을 셀 재료는 **여기** 있다★ 낱말이 아니라 id로 세어야 같은 채널이
        # 이름을 조금 달리 써도 하나로 모인다.
        meta={"video_id": video.video_id, "url": video.url,
              "channel": video.channel, "channel_id": video.channel_id,
              "watched": bool(watched),
              **trust.to_attrs(), **entity_links(*made)}))
    return channel_id


def watch_counts(items) -> dict[str, dict]:
    """최근 기억에서 **채널별로 몇 번 봤나**를 센다. ★순수 함수★

    돌려주는 것은 `{채널 이름: {"count": n, "watched": m, "last": ts}}`.
    이름이 아니라 **채널 id**로 모으되, 사람에게 보일 이름을 함께 들고 다닌다 —
    같은 채널이 이름을 조금 달리 써도 하나로 세어야 반복이 반복으로 보인다.
    """
    by_id: dict[str, dict] = {}
    for item in items or []:
        meta = getattr(item, "meta", None)
        meta = meta if isinstance(meta, dict) else {}
        name = str(meta.get("channel") or "").strip()
        if not name:
            continue
        key = str(meta.get("channel_id") or "").strip() or name.lower()
        row = by_id.setdefault(key, {"channel": name, "count": 0, "watched": 0,
                                     "last": ""})
        row["count"] += 1
        if meta.get("watched"):
            row["watched"] += 1
        ts = str(getattr(item, "ts", "") or "")
        if ts > row["last"]:
            row["last"] = ts
    return {row["channel"]: row for row in by_id.values()}


def regulars(brain, user_id: str, *, threshold: int = REGULAR_AFTER,
             window: int = RECENT_WINDOW) -> list[dict]:
    """★즐겨 보는 채널★ — 되읽는 문이다(원칙 0 ③).

    ★한 번은 사건, 반복은 성향이다★(CLAUDE.md ②) 그래서 한 번 본 채널은 여기
    안 나온다. 그리고 ★세는 자리를 새로 만들지 않는다★ — 볼 때마다 남는 기억
    항목을 되읽어 센다(새 저장 장치 0개).

    브레인이 없거나 아무것도 없으면 **빈 목록**이다. 지어내지 않는다.
    """
    if brain is None:
        return []
    try:
        items = brain.recent(user_id, k=max(1, int(window)), kinds=[ITEM_KIND]) or []
    except Exception:
        return []
    rows = [row for row in watch_counts(items).values()
            if row["count"] >= max(1, int(threshold))]
    rows.sort(key=lambda r: (-r["count"], r["channel"]))
    return rows


def mark_regulars(brain, user_id: str, *, agent=None, now: str = "",
                  threshold: int = REGULAR_AFTER) -> list[str]:
    """반복이 확인된 채널에 ★성향이라고 표시한다★. 표시한 채널 이름들.

    ★왜 표시를 따로 남기나★ `regulars()`는 최근 창만 본다 — 창 밖으로 밀려나면
    그 사실이 사라진다. 반복이 한 번 확인된 것은 **나중에도 참인 사실**이므로
    그래프에 굳힌다(그리고 다른 경로도 그것을 읽을 수 있다).
    """
    stamp = now or now_ts()
    trust = Trust(confidence=0.9, provenance="extracted", source_channel=CHANNEL)
    marked: list[str] = []
    for row in regulars(brain, user_id, threshold=threshold):
        node_id = brain.upsert_entity(user_id, Entity(
            name=row["channel"][:120], kind="org",
            attrs={**trust.to_attrs(), "watches_regularly": True,
                   "seen_times": int(row["count"]), "last_seen": row["last"] or stamp},
            valid_from=stamp))
        if node_id:
            marked.append(row["channel"])
            if agent is not None:
                provenance.record(brain, user_id, agent, [node_id], now=stamp)
    return marked


def remember_upload(brain, user_id: str, video: Video, plan: UploadPlan, *,
                    agent=None, now: str = "") -> str:
    """★내가 올린 것은 내 자산이다★ — `item`으로 남는다.

    `wish`(갖고 싶은 것)도 `topic`(관심사)도 아니다. 만들어서 세상에 내놓은 것이고,
    다음 업로드가 **지난 제목·태그를 되읽어** 더 잘하기 위한 근거다(원칙 0 ③).

    `provenance="user"`인 이유: 올리기로 한 것은 **사용자의 결정**이라 자동
    파이프라인이 덮으면 안 된다(불변 규칙).
    """
    if brain is None or not video or not video.video_id:
        return ""
    stamp = now or now_ts()
    trust = Trust(confidence=1.0, provenance="user", source_channel=CHANNEL)
    item_id = brain.upsert_entity(user_id, Entity(
        name=(plan.title or video.title or video.video_id)[:120], kind="item",
        attrs={**trust.to_attrs(), "url": video.url, "video_id": video.video_id,
               "privacy": plan.privacy, "tags": list(plan.tags),
               "uploaded_at": stamp, "mine": True},
        valid_from=stamp))
    if not item_id:
        return ""
    if agent is not None:
        provenance.record(brain, user_id, agent, [item_id], now=stamp)
    brain.remember(user_id, MemoryItem(
        text=f"Uploaded '{plan.title or video.title}' to YouTube ({plan.privacy}).",
        kind=ITEM_KIND, ts=stamp,
        meta={"video_id": video.video_id, "url": video.url, "privacy": plan.privacy,
              **trust.to_attrs(), **entity_links(item_id)}))
    return item_id


def recall_uploads(brain, user_id: str, limit: int = 5) -> list[dict]:
    """★지난 업로드를 되읽는다★(원칙 0 ③) — 다음 제목·태그를 이것에 맞춘다.

    브레인이 없거나 아무것도 없으면 **빈 목록**이다. 지어내지 않는다.
    """
    if brain is None:
        return []
    try:
        rows = brain.find_entities(user_id, kind="item") or []
    except Exception:
        return []
    out = []
    for entity in rows:
        attrs = getattr(entity, "attrs", None)
        attrs = attrs if isinstance(attrs, dict) else {}
        # ★내가 올린 것만★ — `item`에는 산 물건·기기도 산다. `mine` 표시가
        # 없으면 남의 것을 내 업로드 이력이라고 말하게 된다.
        if not attrs.get("mine") or not attrs.get("video_id"):
            continue
        out.append({"title": getattr(entity, "name", ""), "url": attrs.get("url", ""),
                    "tags": list(attrs.get("tags") or ()),
                    "privacy": attrs.get("privacy", ""),
                    # ★언제 올렸나★ 없으면 화면이 *"며칠 됐다"* 를 말할 수 없다
                    "uploaded_at": attrs.get("uploaded_at", "")})
    # ★최신순이다★ (2026-08-19 · 찍어 보고 알았다) 예전에는 그래프가 준 순서를
    # 그대로 썼다. 그래서 화면 맨 위가 **27일 전 것**이었고, 그것을 마지막 업로드로
    # 읽어 *"마지막으로 올리신 지 27일 됐어요"* 라고 **거짓을 말했다** — 실제로는
    # 엿새 전에 올렸다. ★자르기 **전에** 정렬한다★ 뒤에 자르면 최근 것이 잘려 나간다.
    out.sort(key=lambda row: str(row.get("uploaded_at") or ""), reverse=True)
    return out[:max(1, int(limit))]


def recall_seen(brain, user_id: str, video_id: str, *,
                window: int = RECENT_WINDOW) -> dict:
    """이 영상을 전에 봤는가. 못 찾으면 빈 dict. ★되읽는 문★

    ★있는 것만 말한다★ — *"처음 보는 것 같다"* 는 말은 하지 않는다. 브레인이
    비어 있는 것과 안 본 것을 구별할 수 없기 때문이다.

    ⚠️ ★그래프가 아니라 **기억 항목**을 본다★ (2026-08-19) 예전에는 영상 제목으로
    세운 `topic` 노드를 뒤졌다. 그 노드를 이제 안 만든다(제목은 관심사가 아니라
    그날 스친 문장이다 — 이 절 머리말의 실측). 본 사실은 기억 항목에 남으므로
    되읽을 곳은 거기다.
    """
    if brain is None or not str(video_id or "").strip():
        return {}
    try:
        items = brain.recent(user_id, k=max(1, int(window)), kinds=[ITEM_KIND]) or []
    except Exception:
        return {}
    times, newest = 0, None
    for item in items:
        meta = getattr(item, "meta", None)
        meta = meta if isinstance(meta, dict) else {}
        if str(meta.get("video_id") or "") != str(video_id):
            continue
        times += 1
        if newest is None:
            newest = item          # `recent`는 최신순이다
    if newest is None:
        return {}
    meta = dict(getattr(newest, "meta", None) or {})
    return {"video_id": str(video_id), "times": times,
            "channel": meta.get("channel", ""),
            "last_seen": str(getattr(newest, "ts", "") or ""),
            "watched": bool(meta.get("watched"))}


def _past_hint(past: list[dict], plan: "UploadPlan") -> str:
    """★지난 업로드를 되읽어 한 줄 보탠다★ — 없으면 아무 말도 안 한다. ★순수 함수★

    이 한 줄이 `recall_uploads`를 **부르는 자리**다. 문만 있고 부르는 자리가 없으면
    그 문은 없는 것과 같다(이 저장소가 일곱 번 데인 자리).

    ⚠️ ★태그를 조용히 붙이지 않는다★ 올리는 것은 되돌릴 수 없고 태그는 그 영상의
    얼굴이다. 지난번에 무엇을 썼는지 **말해 주고** 고르는 것은 사람에게 맡긴다.
    """
    if not past:
        return ""
    seen: list[str] = []
    for row in past:
        for tag in row.get("tags") or ():
            if tag not in seen and tag not in (plan.tags or ()):
                seen.append(tag)
    if not seen:
        return ""
    return (f" Last time you tagged with {', '.join(seen[:4])} — say the word and "
            f"I will add those too.")


def privacy_text(privacy: str) -> str:
    """공개 범위를 사람이 읽는 말로. ★코드의 말을 그대로 내보내지 않는다★

    `unlisted`는 값이지 문장이 아니다 — 그대로 찍으면 사용자는 그것을 오류로 읽고,
    무엇보다 **누가 볼 수 있는지**를 모른다(그것이 이 칸의 유일한 요점이다).
    쇼핑에서 `official_store: true`가 화면에 그대로 나왔던 것과 같은 부류다.
    """
    return {"public": i18n.t("Anyone can see it"),
            "unlisted": i18n.t("Only people with the link"),
            "private": i18n.t("Only you")}.get(str(privacy or "").strip(), "")


def _since_line(days: int) -> str:
    if days <= 0:
        return i18n.t("You published today.")
    if days == 1:
        return i18n.t("It has been a day since you last published.")
    return i18n.t("It has been {days} days since you last published.", days=days)


def _times_line(count: int) -> str:
    return i18n.t("{n} times", n=int(count))


def days_since(stamp: str, *, now: str = "") -> int:
    """이 시각으로부터 며칠 지났나. 못 읽으면 -1(=모른다). ★순수 함수★

    ★모르는 것을 0으로 두지 않는다★ 0은 *"오늘"* 이라는 뜻이고, 그것은 못 읽었다는
    사실과 정반대의 말이 된다.
    """
    from datetime import datetime, timezone
    stamps = []
    for text in (stamp, now or now_ts()):
        try:
            when = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return -1
        stamps.append(when.replace(tzinfo=timezone.utc) if when.tzinfo is None
                      else when.astimezone(timezone.utc))
    return max(0, int((stamps[1] - stamps[0]).total_seconds() // 86400))


def channel_state(brain, user_id: str, *, now: str = "") -> dict:
    """★내 채널이 지금 어떤가★ — 화면과 말이 **같은 것**을 본다. 되읽는 문이다.

    돌려주는 것은 전부 **기억에서** 온다 — 그래서 ★열쇠가 없어도 이 화면은 선다★.
    유튜브에 물어봐야 아는 것(조회수·구독자)은 여기 없다. 없는 것을 그럴듯하게
    채우면 그 값이 화면에서 사실이 된다.
    """
    uploads = recall_uploads(brain, user_id, limit=12)
    tags: list[str] = []
    for row in uploads:
        for tag in row.get("tags") or ():
            if tag not in tags:
                tags.append(tag)
    last = uploads[0].get("uploaded_at", "") if uploads else ""
    return {"uploads": uploads, "tags": tags,
            "since": days_since(last, now=now) if last else -1,
            "regulars": regulars(brain, user_id)}


def _watch_note(video: Video, watched: bool) -> str:
    verb = "Watched" if watched else "Looked up"
    where = f" on {video.channel}" if video.channel else ""
    return f"{verb} '{video.title or video.video_id}'{where} on YouTube."


# ── 에이전트 ─────────────────────────────────────────────────────────────────

class YouTubePlugin(Plugin):
    name = "youtube"
    title = "YouTube"
    summary = ("Finds videos, tells you what one is about, sums it up, and puts your "
               "own videos up. Remembers the ones you actually watched and what you "
               "uploaded, so it knows your channels and your past titles.")
    category = "media"

    # ★왜 사용자가 이것을 들였나★(Phase AG) — `summary`가 *"무엇을 하는가"* 라면
    # 이 칸은 *"이 사람이 왜 이걸 갖고 있는가"* 다. 그것이 **무엇을 남길지**의
    # 기준이 된다(원칙 0 ①).
    #
    # ★순서가 있다★(Sean 결정 2026-08-19 — *"둘 다, 순서를 둔다"*) 만드는 쪽이
    # 주다. 유튜브를 하는 사람에게 값진 것은 *"영상을 찾아 주는 것"* 이 아니라
    # **자기 채널이 쌓여 가는 것**이고, 그것은 기억 없이는 성립하지 않는다.
    # 남의 영상을 보는 것은 그 일을 돕는 부다(무엇이 잘 되고 있나, 누가 잘하나).
    purpose = (
        "The user installed this because they make things for a channel of their own, "
        "and the making is spread over weeks that nothing remembers: what they "
        "published, what they called it, what they tagged it with, how long it has "
        "been. So first it keeps their own uploads, and hands the past titles and "
        "tags back the next time they publish. Second, and only in service of that, "
        "it keeps which channels they keep coming back to -- not every video they "
        "glance at, which is a list of that afternoon rather than anything about them."
    )

    # ★원하는 사람만 들인다★ — ② 구글 OAuth가 있어야 올릴 수 있다
    optional = True

    # ★먼저 말을 걸지 **않는다** — 그리고 그것이 결정이다★ (Sean 2026-08-19)
    #
    # 이 칸이 비어 있으면 *"아직 안 봤다"* 와 구별되지 않아, 다음 사람이 **이미 정한
    # 것을 다시 정하게** 된다(`brain`의 `gap`/`settled`를 가른 것과 같은 이유).
    collab = {
        "settled": "Telling someone who publishes that it has been 27 days since "
                   "their last upload is the fastest way to become nagging, and it "
                   "is a judgement about their productivity that we have no standing "
                   "to make: we cannot tell a break from a block from a holiday. "
                   "The useful moment is the one they open themselves -- when they "
                   "publish, it hands back the titles and tags they used before. "
                   "That costs them nothing and needs no guess about their state.",
    }
    # ★말로 이렇게 시킨다★ — 사용자가 이 카드에서 읽는 사용법이다
    howto = (
        "What is this video about?",
        "Upload that clip to my channel as unlisted",
    )
    version = "0.2.2"
    author = "cosmos"
    description = ("Searches YouTube, describes or summarizes a video, lists what is "
                   "trending, opens a video in the browser, and uploads a video file "
                   "to the user's own channel.")
    parameters = {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING",
                       "description": " | ".join(f"{k} — {v['desc']}"
                                                 for k, v in ACTIONS.items())},
            "query": {"type": "STRING",
                      "description": "What to look for. For info/summarize/play this "
                                     "may also be a video URL or id."},
            "region": {"type": "STRING",
                       "description": "Two-letter country code for trending (e.g. US, KR)."},
            "file": {"type": "STRING", "description": "Path of the video file to upload."},
            "title": {"type": "STRING", "description": "Title for the upload."},
            "description": {"type": "STRING", "description": "Description for the upload."},
            "tags": {"type": "STRING", "description": "Comma-separated tags for the upload."},
            "privacy": {"type": "STRING",
                        "description": "private (default) | unlisted | public. "
                                       "★Anything not in that list becomes private.★"},
        },
        "required": [],
    }
    # ★`media.publish`가 여기 있는 이유★ 나머지는 남의 것을 읽는 역량이고 이것만
    # **내 이름으로 세상에 내놓는** 역량이다. 설치 화면에서 사용자는 그 한 줄을 보고
    # 승인한다 — 역량이 없으면 그 고지도 없다.
    capabilities = ["network", "browser", "media.publish", "memory"]
    requires_desktop = False
    # ★화면 이름★ — 마켓 카드의 `title`과 다른 자리다(이쪽은 열었을 때의 제목)
    view_title = "My channel"
    # ★이 화면의 성격★(Sean 요구 2026-08-19) 쌓아 온 것을 **시간순으로** 보는
    # 화면이다. 한 눈에 들어와야 *"얼마나 해 왔나"* 가 보이므로 촘촘하다.
    character = {"glyph": "channel", "density": "dense", "surface": "solid"}

    # ★열쇠는 금고로 직행한다★ 파일에 남기면 그 순간 저장소에 커밋되고, 화면으로
    # 내려보내면 응답·기록·스크린샷에 실린다. 돌아오는 것은 마스킹뿐이다.
    settings = (
        # ★손으로 넣는 칸은 **선택**이다★ (Sean 요구 2026-08-19 — *"OAuth 연동이
        # 필요한 것이 많은데 원클릭으로 동작이 되도록 해야 합니다"*)
        #
        # 예전에는 이 칸이 **필수**였다. 그래서 구글 클라우드에서 API 키를 만들어
        # 오지 않으면 여섯 액션 중 다섯이 막혔다 — 실측으로 확인한 상태다(브레인에
        # 남은 것 0건). ★유튜브 읽기 API는 OAuth 토큰으로도 된다★ 그러니 아래
        # 버튼 하나가 읽기와 올리기를 **둘 다** 덮는다.
        #
        # ⚠️ 그래도 칸을 없애지 않는 이유: 우리 client_id로 연결하면 할당량이
        # **우리 프로젝트** 것이다. 많이 쓰는 사람은 자기 키를 넣어 자기 할당량을
        # 쓸 수 있어야 한다(밖에서 바꿀 수 있게 두되 기본은 그냥 되는 것 —
        # CLAUDE.md ④).
        {"id": "api_key", "kind": "secret", "label": "YouTube Data API key (optional)",
         "hint": "Only if you want to use your own quota. Connecting below is enough."},
        # ★버튼 하나로 끝난다★(Phase OA · Sean 2026-08-11) — 예전에는 여기가
        # `client_id`·`client_secret`·`refresh_token` 세 칸이었고, 사용자가 구글
        # 클라우드에서 OAuth 클라이언트를 **직접 만들어** 복사해 와야 했다.
        # 개발자가 아니면 그 화면에서 멈춘다. 지금은 우리가 등록하고 사람은 허용만 한다.
        #
        # ⚠️ 세 칸을 지운 것이 아니라 **한 칸으로 바꿨다** — 옛 값이 금고에 남아
        # 있으면 아래 `_have()`가 그것도 본다(이미 넣어 둔 사람이 갑자기 못 쓰게
        # 되면 안 된다).
        # ★한 번의 허용이 읽기와 올리기를 **둘 다** 덮는다★ 예전에는 `upload`만
        # 요청해서, 올릴 수는 있는데 **찾을 수는 없는** 상태가 됐다(그리고 찾으려면
        # 위 칸에 키를 손으로 넣어야 했다). 허용 화면을 두 번 띄우지 않는다.
        {"id": "google", "kind": "oauth", "label": "Connect your YouTube channel",
         "provider": "google",
         "scopes": ["https://www.googleapis.com/auth/youtube.readonly",
                    "https://www.googleapis.com/auth/youtube.upload"],
         "hint": "One click covers both searching and uploading. "
                 "Cosmos never sees your Google password."},
        {"id": "default_privacy", "kind": "choice", "label": "Default upload privacy",
         "options": list(PRIVACY), "default": SAFE_PRIVACY},
        {"id": "region", "kind": "text", "label": "Region for trending",
         "default": "US"},
    )

    brain = {
        # ★스쳐 본 것과 지목해서 본 것을 가른다★ 검색 결과를 통째로 남기면 브레인이
        # **보지도 않은 영상**으로 채워진다. `ACTIONS[*].remembers`가 그 경계다.
        #
        #   `item` — ★내가 올린 것★ 이 에이전트의 **주**다(`mine=True`)
        #   `org`  — 채널. 반복될 때만 성향으로 표시된다(`watches_regularly`)
        "stores": ("item", "org"),
        "reads": ("item", "org"),
        # ★안 남기기로 한 것을 적는다★ — 뭉개면 고쳐야 할 것이 "검토됨"으로 묻힌다.
        "settled": "Two things are deliberately never stored as graph nodes. View and "
                   "like counts are true for one instant, so keeping them would fill "
                   "the brain with numbers that are already wrong. And video titles: "
                   "measured on this machine, 55% of the topic nodes already there are "
                   "page titles carrying site tags and clickbait, and naming a node "
                   "after a title adds one more of those for every video glanced at. "
                   "A title is what someone wrote to get a click that afternoon, not "
                   "what this person is interested in. What lasts is the channel they "
                   "keep returning to and what they published themselves.",
    }

    # -- 화면 -----------------------------------------------------------------
    def view(self, ctx: ToolContext, **params) -> dict:
        """★내 채널이 주다★(Sean 결정 2026-08-19) — 그래서 화면도 내 것을 그린다.

        ## ★열쇠가 없어도 이 화면은 선다★

        여기 그리는 것은 **전부 기억에서** 온다 — 유튜브에 묻지 않는다. 그래서
        아직 연결을 안 한 사람도 화면을 열 수 있고, 거기서 **연결하라는 말을 읽는다**.
        열쇠가 없으면 화면까지 비는 설계는, 시작하는 사람에게 *"이건 고장났다"* 로
        읽힌다(실측: 이 에이전트가 브레인에 남긴 것이 0건이었다).

        ## 무엇을 안 그리나

        조회수·구독자는 **없다**. 그것은 유튜브에 물어야 아는 값이고, 남기지 않기로
        한 값이다(`brain["settled"]`). 없는 것을 그럴듯하게 채우면 그 값이 화면에서
        사실이 된다.
        """
        brain = getattr(ctx, "brain", None)
        uid = str(getattr(ctx, "user_id", "") or "local")
        state = channel_state(brain, uid)
        blocks: list[dict] = []

        # ★먼저 **지금 무엇을 할 수 있나**를 말한다★ 연결이 없으면 그것이 첫 줄이다
        if line := self._connect_line(ctx):
            blocks.append({"type": "text", "tone": "warn", "text": line})

        blocks.append({"type": "group", "icon": "▶",
                       "label": i18n.t("What you have published")})
        uploads = state["uploads"]
        if not uploads:
            blocks.append({"type": "text", "tone": "muted", "text": i18n.t(
                "Nothing yet. When you upload through me I will keep the title and "
                "the tags, and hand them back next time.")})
        else:
            if state["since"] >= 0:
                blocks.append({"type": "text", "tone": "info",
                               "text": _since_line(state["since"])})
            blocks.append({"type": "list", "items": [
                {"text": row["title"],
                 "sub": " · ".join(x for x in (
                     privacy_text(row.get("privacy", "")),
                     ", ".join(row.get("tags") or ())) if x),
                 "tone": "muted" if row.get("privacy") == "private" else "info"}
                for row in uploads]})
            if state["tags"]:
                blocks.append({"type": "chips", "items": [
                    {"label": tag} for tag in state["tags"][:10]]})

        # ★부는 곁들이다★(Sean 결정: 순서를 둔다) — 그래서 아래에 온다
        if state["regulars"]:
            blocks.append({"type": "group", "icon": "★",
                           "label": i18n.t("Channels you come back to")})
            blocks.append({"type": "list", "items": [
                {"text": row["channel"],
                 "sub": _times_line(row["count"]), "tone": "muted"}
                for row in state["regulars"][:8]]})
        return {"title": self.view_title, "blocks": blocks}

    def _connect_line(self, ctx: ToolContext) -> str:
        """★지금 무엇이 막혀 있나★ — 없으면 빈 문자열(막는 것이 없으면 말 안 한다)."""
        try:
            have = self._have(ctx)
        except Exception:
            return ""
        if not missing_for("upload", have):
            return ""
        return self._ask_for_keys("upload", missing_for("upload", have))

    # -- 라우팅 ---------------------------------------------------------------
    def run(self, ctx: ToolContext, **args) -> str:
        action = str(args.get("action") or "").strip().lower()
        query = str(args.get("query") or "").strip()
        if action not in ACTIONS:
            # ★모르는 낱말이면 짐작한다 — 다만 안전한 쪽으로★ 파일이 딸려 왔다고
            # 업로드로 읽지 않는다. 올리는 것은 **말한 대로만** 한다.
            action = DEFAULT_ACTION
        missing = missing_for(action, self._have(ctx))
        if missing:
            return self._ask_for_keys(action, missing)
        try:
            if action == "upload":
                return self._upload(ctx, args)
            if action == "trending":
                return self._trending(ctx, str(args.get("region") or ""))
            if action == "play":
                return self._play(ctx, query)
            if action in ("info", "summarize"):
                return self._one(ctx, query, summarize=(action == "summarize"))
            return self._search(ctx, query)
        except Exception as e:                      # 네트워크·서버 오류
            return f"Could not reach YouTube: {e}"

    # -- 자격증명 -------------------------------------------------------------
    # 옛 방식으로 손수 넣어 둔 칸들 — ★지우지 않고 **받아 준다**★
    # 클릭 연동이 생겼다고 이미 넣어 둔 사람이 갑자기 못 쓰게 되면, 그것은 개선이
    # 아니라 고장이다. 새 길이 기본이고 옛 길은 살아 있다.
    _LEGACY = ("client_id", "client_secret", "refresh_token")

    def _have(self, ctx: ToolContext) -> dict:
        """지금 손에 있는 열쇠들. ★원문을 로그·응답에 싣지 않는다★ — 여기서 나간
        값은 오직 `missing_for`의 '있다/없다' 판정과 HTTP 헤더로만 쓰인다."""
        from cosmos.core import agent_settings, appauth
        uid = str(getattr(ctx, "user_id", "") or "")
        out = {}
        for field in ("api_key", *self._LEGACY):
            try:
                out[field] = agent_settings.reveal(self.name, field, user_id=uid) or ""
            except Exception:
                out[field] = ""
        # ★연결됐는가★ — 버튼으로 받은 토큰이 있거나, 옛 세 칸이 **다** 차 있거나.
        # 둘 중 하나면 올릴 수 있다.
        connected = appauth.token_of(self.name, "google", user_id=uid)
        out["google"] = connected or ("legacy" if all(out[f] for f in self._LEGACY) else "")
        return out

    def _setting(self, ctx: ToolContext, field: str, default: str = "") -> str:
        from cosmos.core import agent_settings
        uid = str(getattr(ctx, "user_id", "") or "")
        try:
            return str(agent_settings.get(self.name, field, default, user_id=uid) or default)
        except Exception:
            return default

    def _ask_for_keys(self, action: str, missing) -> str:
        """★무엇이 없는지, 그리고 **누가** 무엇을 하면 되는지 말한다★

        'not configured'는 아무것도 알려 주지 않는다. 그리고 할 일이 사용자에게
        있는지 우리에게 있는지를 갈라 말하는 것이 이 문장의 요점이다(Phase OA).

        ## ★버튼이 있으면 **버튼을 먼저** 말한다★ (Sean 요구 2026-08-19)

        예전에는 읽기가 API 키만 받았으므로 이 문장이 *"구글 클라우드 콘솔에서
        키를 만들어 오세요"* 였다. 개발자가 아니면 그 문장에서 멈춘다 — 그리고
        실제로 멈춰 있었다(브레인에 남은 것 0건). 이제 읽기도 버튼으로 되므로
        **버튼이 앞이고 키는 곁들이**다.
        """
        if "google" in missing:
            from cosmos.core import appauth
            # 우리 쪽 준비가 안 됐으면 **그렇게** 말한다 — 사용자를 구글 클라우드로
            # 보내지 않는다. 준비가 됐으면 할 일은 버튼 하나다.
            blocked = appauth.why_not("google")
            if blocked:
                return blocked
            line = ("To {what} I need to be connected to your YouTube account. "
                    "Open this agent's settings and press Connect — it takes one "
                    "click and I never see your password.").format(
                        what=ACTIONS[action]["desc"])
            # ★키는 **고를 수 있는 다른 길**이지 요구가 아니다★ 자기 할당량을
            # 쓰고 싶은 사람만 넣는다 — 그 사실을 뒤에 한 줄로 붙인다.
            if "api_key" in missing:
                line += (" (Or paste your own YouTube Data API key there if you would "
                         "rather use your own quota.)")
            return line
        names = ", ".join(missing)
        return (f"I cannot {ACTIONS[action]['desc']} yet: {names} "
                f"{'is' if len(missing) == 1 else 'are'} missing. "
                f"Add {'it' if len(missing) == 1 else 'them'} in this agent's settings.")

    # -- 읽기 -----------------------------------------------------------------
    def _api(self, ctx: ToolContext, path: str, params: dict) -> dict:
        """읽기 한 번. ★열쇠가 둘 중 **아무거나** 있으면 된다★

        ★키를 먼저 쓴다★ 사용자가 자기 키를 넣어 뒀다면 그것은 *"내 할당량을
        쓰겠다"* 는 뜻이고, 그 결정이 우리 기본값을 이긴다(불변 규칙).
        키가 없으면 구글 연결의 토큰으로 부른다 — 유튜브 읽기 API는 둘 다 받는다.
        """
        import requests
        have = self._have(ctx)
        key = have.get("api_key", "")
        if key:
            resp = requests.get(f"{_API}/{path}", params={**params, "key": key},
                                timeout=_TIMEOUT)
        else:
            token = self._access_token(ctx)
            resp = requests.get(f"{_API}/{path}", params=params,
                                headers={"Authorization": f"Bearer {token}"},
                                timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def _search(self, ctx: ToolContext, query: str) -> str:
        if not query:
            return "Tell me what to look for on YouTube."
        ctx.write_log(f"[youtube] search {query}")
        found = normalize(self._api(ctx, "search", {
            "part": "snippet", "q": query, "type": "video",
            "maxResults": MAX_RESULTS}))
        if not found:
            return f"I found nothing on YouTube for '{query}'."
        return "\n".join(f"{i}. {v.title} — {v.channel} ({v.url})"
                         for i, v in enumerate(found, 1))

    def _one(self, ctx: ToolContext, query: str, *, summarize: bool) -> str:
        """지목한 영상 하나. ★여기서부터 브레인에 남는다★(사용자가 골랐다)."""
        video = self._resolve(ctx, query)
        if video is None:
            return f"I could not find that video ('{query}')."
        ctx.write_log(f"[youtube] {'summarize' if summarize else 'info'} {video.video_id}")
        brain = getattr(ctx, "brain", None)
        uid = str(getattr(ctx, "user_id", "") or "local")
        seen = recall_seen(brain, uid, video.video_id)
        # ★되읽는 문을 **부른다**★ 예전에는 이 자리가 없어서, 몇 번을 봐도 매번
        # 처음이었다(그리고 `regulars`는 만들어 놓고 아무도 안 부르는 문이었다).
        known_channels = {row["channel"] for row in regulars(brain, uid)}
        self._remember(ctx, video, watched=False)
        head = (f"{video.title} — {video.channel}\n{video.url}"
                + (f"\n{video.views:,} views" if video.views else ""))
        if seen:
            head += f"\n(You looked this one up before, on {seen.get('last_seen', '')[:10]}.)"
        elif video.channel and video.channel in known_channels:
            # ★한 번은 사건, 반복은 성향이다★ — 그 채널을 이미 여러 번 봤을 때만 말한다
            head += f"\n(You come back to {video.channel} a lot.)"
        if not summarize:
            return head + (f"\n\n{video.description[:600]}" if video.description else "")
        return head + "\n\n" + self._summary(ctx, video)

    def _summary(self, ctx: ToolContext, video) -> str:
        """★무엇을 근거로 요약했는지 밝힌다★ 유튜브는 자막을 API로 내주지 않는다.

        제목과 설명만 보고 요약하면서 *"영상을 봤다"* 는 듯 말하면 그것은 거짓말이다
        (함정 44). 근거를 한 줄로 적고 시작한다.
        """
        if not video.description.strip():
            return ("There is no description to work from, and YouTube does not hand "
                    "out captions through the API — so I cannot summarize this one "
                    "without watching it.")
        try:
            text = ctx.think(
                "Summarize this YouTube video in three short sentences. Work only from "
                "the title and description given; do not invent anything that is not "
                f"there.\n\nTitle: {video.title}\nChannel: {video.channel}\n"
                f"Description:\n{video.description[:4000]}")
        except Exception as e:
            return f"I could not summarize it: {e}"
        return ("Based on the title and description only (YouTube does not give out "
                f"captions):\n{str(text or '').strip()}")

    def _trending(self, ctx: ToolContext, region: str) -> str:
        code = (region or self._setting(ctx, "region", "US")).strip().upper()[:2] or "US"
        ctx.write_log(f"[youtube] trending {code}")
        found = normalize(self._api(ctx, "videos", {
            "part": "snippet,statistics", "chart": "mostPopular",
            "regionCode": code, "maxResults": MAX_RESULTS}))
        if not found:
            return f"YouTube returned nothing for the trending chart in {code}."
        return f"Trending in {code}:\n" + "\n".join(
            f"{i}. {v.title} — {v.channel}" for i, v in enumerate(found, 1))

    def _play(self, ctx: ToolContext, query: str) -> str:
        """연다 — ★브라우저 일은 브라우저 도구에게 맡긴다★(원칙 1).

        여는 코드를 여기에 또 적으면 기본 브라우저·권한 판정이 두 곳이 되고,
        언젠가 한쪽만 고쳐진다.
        """
        video = self._resolve(ctx, query, need_key=False)
        url = (video.url if video is not None
               else f"https://www.youtube.com/results?search_query={_q(query)}")
        if video is not None:
            self._remember(ctx, video, watched=True)
        return str(ctx.run_tool("browser_control", {"action": "go_to", "url": url}))

    def _resolve(self, ctx: ToolContext, query: str, *, need_key: bool = True):
        """말·주소·id 중 무엇이 와도 영상 하나로. 못 찾으면 None.

        ★id가 이미 있으면 검색하지 않는다★ — 검색은 열쇠가 필요하고, 주소를 준
        사람에게 *"열쇠를 넣으라"* 고 답하는 것은 틀린 답이다.
        """
        ident = video_ref(query)
        if ident and not need_key:
            return Video(video_id=ident)          # 열쇠 없이 열기만 하면 되는 경우
        if ident:
            got = normalize(self._api(ctx, "videos",
                                      {"part": "snippet,statistics", "id": ident}))
            return got[0] if got else Video(video_id=ident)
        if not query or not need_key:
            return None
        got = normalize(self._api(ctx, "search", {
            "part": "snippet", "q": query, "type": "video", "maxResults": 1}))
        return got[0] if got else None

    # -- 업로드 ---------------------------------------------------------------
    def _upload(self, ctx: ToolContext, args: dict) -> str:
        """★되돌릴 수 없는 일이므로 판정을 먼저 통과해야 한다★

        `plan_upload`가 파일 존재와 공개 범위를 확정한다. 공개 범위는 **모르면
        가장 좁게** 정해지고, 요청과 달라졌으면 그 사실을 답에 싣는다 — 조용히
        좁히면 "왜 안 보이지"가 되고, 조용히 넓히면 되돌릴 수 없다.
        """
        brain = getattr(ctx, "brain", None)
        uid = str(getattr(ctx, "user_id", "") or "local")
        # ★지난 업로드를 **되읽는다**★(원칙 0 ③) 이 문은 있었는데 **아무도 안
        # 부르고 있었다** — 문서에는 *"다음 업로드가 지난 제목·태그를 되읽어 더
        # 잘하기 위한 근거"* 라고 적혀 있었지만 실제로는 한 번도 안 읽었다
        # (★만들어 놓고 잇지 않으면 없는 것과 같다★).
        past = recall_uploads(brain, uid)
        tags = [t.strip() for t in str(args.get("tags") or "").split(",") if t.strip()]
        plan = plan_upload(
            str(args.get("file") or ""), title=str(args.get("title") or ""),
            description=str(args.get("description") or ""), tags=tags,
            privacy=str(args.get("privacy") or ""),
            default_privacy=self._setting(ctx, "default_privacy", SAFE_PRIVACY))
        if not plan.ok:
            return plan.reason
        ctx.write_log(f"[youtube] upload {plan.title} ({plan.privacy})")
        video_id = self._send(ctx, plan)
        video = Video(video_id=video_id, title=plan.title, tags=plan.tags)
        self._remember_upload(ctx, video, plan)
        note = ("" if not plan.narrowed else
                f" I did not recognise the privacy you asked for, so it went up as "
                f"{plan.privacy} — say 'public' exactly if you want it public.")
        return (f"Uploaded '{plan.title}' as {plan.privacy}: {video.url}."
                f"{note}"
                + ("" if plan.privacy != "public" else
                   " It is public now — anyone with the link can see it.")
                + _past_hint(past, plan))

    def _access_token(self, ctx: ToolContext) -> str:
        """★길이 둘이고 뒤쪽은 하위 호환이다★

        · 버튼으로 연결했으면 — 우리 앱의 client_id로 그 사람의 토큰을 갱신한다
        · 옛 방식이면 — 그 사람이 넣은 client_id/secret으로 (그대로 둔다)
        """
        import requests
        from cosmos.core import appauth
        have = self._have(ctx)
        uid = str(getattr(ctx, "user_id", "") or "")
        connected = appauth.token_of(self.name, "google", user_id=uid)
        if connected:
            spec = appauth.PROVIDERS["google"]
            form = {"client_id": spec["client_id"],
                    "client_secret": spec.get("client_secret", ""),
                    "refresh_token": connected, "grant_type": "refresh_token"}
        else:
            form = {"client_id": have.get("client_id", ""),
                    "client_secret": have.get("client_secret", ""),
                    "refresh_token": have.get("refresh_token", ""),
                    "grant_type": "refresh_token"}
        resp = requests.post(_TOKEN, data=form, timeout=_TIMEOUT)
        resp.raise_for_status()
        token = str((resp.json() or {}).get("access_token") or "")
        if not token:
            raise RuntimeError("Google did not return an access token — the refresh "
                               "token may have been revoked. Re-do the consent step.")
        return token

    def _send(self, ctx: ToolContext, plan) -> str:
        """resumable 업로드 — 메타데이터로 자리를 잡고, 그 자리에 파일을 밀어 넣는다."""
        import requests
        token = self._access_token(ctx)
        body = {"snippet": {"title": plan.title, "description": plan.description,
                            "tags": list(plan.tags)},
                "status": {"privacyStatus": plan.privacy}}
        start = requests.post(
            _UPLOAD, params={"uploadType": "resumable", "part": "snippet,status"},
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json; charset=UTF-8",
                     "X-Upload-Content-Type": "video/*"},
            data=json.dumps(body), timeout=_TIMEOUT)
        start.raise_for_status()
        where = start.headers.get("Location") or start.headers.get("location") or ""
        if not where:
            raise RuntimeError("YouTube did not give an upload URL to send the file to.")
        with open(plan.path, "rb") as handle:
            done = requests.put(where, headers={"Authorization": f"Bearer {token}",
                                                "Content-Type": "video/*"},
                                data=handle, timeout=_UPLOAD_TIMEOUT)
        done.raise_for_status()
        ident = str((done.json() or {}).get("id") or "")
        if not ident:
            raise RuntimeError("The upload finished but YouTube did not return a video id.")
        return ident

    # -- 브레인 ---------------------------------------------------------------
    def _remember(self, ctx: ToolContext, video, *, watched: bool) -> None:
        """★기억은 부산물이다★ 실패해도 도구는 자기 답을 그대로 낸다."""
        brain = getattr(ctx, "brain", None)
        if brain is None:
            return
        try:
            remember_video(brain, str(getattr(ctx, "user_id", "") or "local"),
                           video, agent=self, watched=watched)
        except Exception as e:
            ctx.write_log(f"[youtube] could not remember: {e}")

    def _remember_upload(self, ctx: ToolContext, video, plan) -> None:
        brain = getattr(ctx, "brain", None)
        if brain is None:
            return
        try:
            remember_upload(brain, str(getattr(ctx, "user_id", "") or "local"),
                            video, plan, agent=self)
        except Exception as e:
            ctx.write_log(f"[youtube] could not remember the upload: {e}")


def _q(text: str) -> str:
    from urllib.parse import quote_plus
    return quote_plus(str(text or ""))
