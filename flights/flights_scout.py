"""flights — 항공권을 찾고, ★어디에 가려 했는지 기억한다★ (Phase MA ⑥ · Phase AG ①-2d).

## ★어디서 값을 얻나 — 항공편 목록을 **직접 연다**★ (Sean 지적 2026-08-21)

> *"아예 항공권 검색을 제대로 하지도 못하고 … 여러 곳에 검색을 하고 항공사에도
> 검색을 하고 날짜도 바꿔 보고 가격을 비교해 본다. 이것을 에이전트가 해야 하는
> 것이다. 그런데 그 본질을 하지 못한다."*

★맞는 지적이었고, 원인은 **검색 결과로 항공권을 사려 한 것**이었다.★ 첫 판은
쇼핑이 낸 길을 그대로 따라 `web_search` 한 줄을 던졌는데, 실측해 보니(2026-08-21):

    물음  "Seoul to Tokyo 2026-09-15 flight ticket price"   ← 한 번, 이것이 전부였다
    답    스카이스캐너·트립닷컴·익스피디아의 **노선 안내 페이지** 링크 다섯

거기 적힌 `$44`·`$41`은 ★그 날짜의 값이 아니라 **아무 날이나 통틀어 가장 싼
광고 문구**★다. 편명도 시각도 경유도 없다. 그런데 우리는 그것을 *"9월 15일 서울→
도쿄"* 라고 모델에게 넘겨 표로 만들게 했다 — ★없는 값을 지어내는 구조★였다.

지금은 **항공편 목록 페이지를 브라우저로 연다**(`ctx.read_page` — 코어의 계약).
같은 물음에 항공편 46개가 나온다: 편마다 출발·도착 시각, 소요, 직항/경유, 항공사,
그리고 실제 값. ★한 곳을 여는 것이 여러 곳을 검색하는 것보다 넓다★ — 그 페이지가
이미 대한항공·아시아나·JAL·ANA·저가 항공사를 한자리에 모아 놓았기 때문이다.

⚠️ ★페이지가 바뀌면 부서진다★ — 그것이 이 방식의 값이다. 그래서 **모델이 옮기고**
(자리가 바뀌어도 글로 읽는다), 순위·비교 같은 **판정은 우리 코드가** 한다. 그리고
못 읽으면 ★빈손이라고 말한다★ — 지어내지 않는다.

## ★이 에이전트의 값어치는 두 번째 검색이다★ (원칙 0 · Sean 요구)

    "지난주에 보던 도쿄행, 8만원 내렸어요."

그래서 검색 의도(`wish`)와 목적지(`place`)를 브레인에 남기고, 다음 검색이 그것을
**먼저 읽는다**. 남기지 않으면 이 기능은 검색창 하나 더에 지나지 않는다.

⚠️ ★가격은 순간값인데 왜 남기나★ — 남기는 것은 *"지금 89만원"* 이 아니라
*"그때 89만원이었다"* 는 **관측**이다. 시각과 함께 남기면 나중에도 참이고, 그것이
있어야 *"내렸다"* 를 말할 수 있다. 시각 없이 가격만 남기면 그것은 곧 거짓이 된다.

## ★쇼핑에 없는 축이 하나 있다 — **날짜**★ (Phase AG · 2026-08-19)

물건은 어제 사나 내일 사나 같은 물건이지만, ★같은 노선도 **다른 날은 다른 것**★이다.
9월 10일 도쿄행과 12월 24일 도쿄행은 값이 두 배 넘게 갈린다. 그런데 이 파일은
노선 이름에 날짜를 안 넣고 있었다 — 그래서 다른 날짜로 한 번만 검색해도 지난 기억을
덮어썼고, 그다음 *"74만원 올랐어요"* 라고 **없던 인상**을 말했다.

그리고 날짜는 **끝난다**. 떠난 비행기가 싸졌다는 말은 아무 값이 없으므로, 출발일이
지난 노선은 지켜보는 목록에서 빠지고 알림도 스스로 내려간다.

## 이 파일이 도는 층

    표(단일 진실원) → 정규형 → ★판정(순수 함수)★ → 기억 → 화면 → 에이전트

★판정이 순수 함수라야 그물이 잡는다★(29차 교훈) — 네트워크에 묻으면 뮤테이션이
낱말만 남기고 빠져나간다.

## 독립 — ★에이전트 하나 = 파일 하나★ (Sean 규율)

판정도 기억도 화면도 이 파일 안에 있다. 기대는 것은 **계약뿐**이다:
`contracts.Plugin` · `contracts.memory` · `contracts.view` · `core.provenance`.
번역은 옆의 `flights_i18n.py`가 지고 다닌다 — 코어 카탈로그에 두면 마켓으로 나온
뒤 **새 문구를 아무도 검사하지 않는다**(코어 그물은 코어 소스만 본다).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import flights_i18n as i18n
from cosmos.contracts import Plugin, ToolContext
from cosmos.contracts.memory import (Entity, MemoryItem, Relation, Trust,
                                     entity_links, now_ts)
# ★신호 어휘의 주인은 **화면 계약**이다★ 우리가 이름을 지어내면 화면이 무엇을
# 그릴지 모르게 되고, 그 순간 "비교가 한눈에"가 깨진다. 새 신호가 필요하면
# 코스모스의 `contracts/view.py`에 한 줄을 더한다(그리고 번역 다섯이 함께 온다).
from cosmos.contracts.view import COMPARE_SIGNALS
from cosmos.core import provenance

CHANNEL = "flights.v1"
ITEM_KIND = "flight"

ACTIONS: dict[str, dict] = {
    "search":  {"desc": "find flights for a route"},
    "next":    {"desc": "show the next few from the list already on screen"},
    "prev":    {"desc": "go back one page"},
    "plans":   {"desc": "what trips you have been looking at"},
    "booked":  {"desc": "the user says they booked it — stop watching the fare"},
    "dropped": {"desc": "the user says they are not going after all"},
    "still_looking": {"desc": "they have not booked yet — undo either of those two"},
    "forget":  {"desc": "stop tracking a route"},
}
DEFAULT_ACTION = "search"

# ★한 화면에 넷★ 스크롤해야 견줄 수 있으면 "한눈에 결정"이 깨진다. 그렇다고 넷이
# **전부**는 아니다 — 뒤엣것은 버리지 않고 넘겨 본다(쇼핑과 같은 규율).
PAGE_SIZE = 4
MAX_KEPT = PAGE_SIZE * 3

# ★더 싼 날을 몇 개까지 보이나★ 표에는 앞뒤로 일주일이 있지만, 전부 늘어놓으면
# 사용자가 고르는 것이 아니라 표를 읽게 된다. 싼 것부터 이만큼만 보인다.
MAX_NEARBY_DAYS = 3

# ★날짜 표를 읽을 때만 상한을 올린다★ 기본 60은 *"모델이 번호로 고른다"* 를 위한
# 수인데, 표는 (가는 날 × 오는 날) 격자라 칸이 마흔아홉이고 페이지의 다른 단추까지
# 세면 그것을 넘는다 — 60에서 끊으면 ★뒤쪽 날짜가 통째로 사라진다★.
GRID_TARGETS = 400

# ★누른 뒤 표가 그려질 때까지 기다린다★ (2026-08-21 실측으로 정했다)
#
# 처음에는 기본 대기(1.2초)로 읽었고 ★한 칸도 못 읽었다★. 그런데 실패로 보이지
# 않았다 — 읽힌 것 하나가 `"Cheapest from Fetching results ₩272,903"` 이었고,
# 그것은 **표가 아직 채워지는 중**이라는 뜻이었다. 빈손은 그대로 *"더 싼 날이
# 없다"* 로 화면에 나갔다.
#
# ⚠️ ★이런 종류는 사람 눈에 안 걸린다★ — 화면이 멀쩡하고 말도 맞다. 그래서
# 계측이 **읽은 칸 수를 센다**(`_other_days`의 기록 한 줄).
GRID_SETTLE_SEC = 9.0

# 지난 검색이 이보다 오래됐으면 "지난번"이라고 부르지 않는다 — 반 년 전 한 번 본
# 것을 들이밀면 도움이 아니라 참견이다(쇼핑과 같은 규율).
STALE_AFTER_DAYS = 90

# 한 노선에 대해 남기는 관측의 수. ★값의 **모양**을 보려면 점이 여럿 있어야 한다★
# 그렇다고 무한이면 한 노선의 attrs가 한없이 커진다.
MAX_HISTORY = 24

# 화면이 "값이 움직였다"고 그릴 문턱. 100원 차이를 그리면 그것은 소음이다.
PRICE_CHANGE_MIN_RATIO = 0.02


# ── ★알림의 문턱★ — 화면보다 훨씬 높다 ──────────────────────────────────────
#
# 화면은 지나가다 보는 것이고 알림은 **하던 일을 멈추게** 하는 것이다. 잔소리가
# 되는 순간 이 통로 전체가 값을 잃는다(알림이 값을 잃는 그 길이다).
ALERT_MIN_RATIO = 0.07        # 7% 넘게 내렸을 때만 말을 건다

# …그리고 실제 금액도 이만큼은 내려야 한다.
#
# ★통화마다 다르다★ (2026-08-19) 쇼핑은 이 자리에 `3_000`을 박아 두었는데, 그러면
# 달러로 파는 것은 **$3,000이 내려야** 말을 건다. CLAUDE.md가 못 박은 자리 그대로다
# — *"★기능 문자열도 언어를 탄다★ … 통화(`Candidate.currency`)"*. 항공권은 금액이
# 커서 이 실수가 더 크게 난다.
#
# ⚠️ ★모르는 통화는 **비율만으로** 판정한다★ 아무 숫자나 기본값으로 두면 그 통화
# 사용자에게는 문턱이 있는 척하면서 실제로는 엉뚱한 값이 선다.
ALERT_MIN_DELTA: dict[str, int] = {
    "KRW": 20_000, "JPY": 2_000, "USD": 15, "EUR": 15, "GBP": 12, "CNY": 100,
}

# 같은 노선을 얼마 만에 다시 알릴 수 있나. 값이 오르내리는 노선은 문턱만으로는
# 하루에 몇 번씩 울린다.
ALERT_QUIET_SEC = 3 * 24 * 3600

# 배경에서 값을 다시 보는 주기. 더 자주 보면 검색만 늘고 알릴 것은 안 는다.
RECHECK_EVERY_SEC = 12 * 3600

# 모델에게 주는 지시 — ★옮기는 일만 시킨다★
#
# ⚠️ ★읽는 것이 **검색 결과가 아니라 항공편 목록**이 되었다★(2026-08-21) 그래서
# 물어보는 칸도 달라졌다: 이제 시각과 소요가 페이지에 **실제로 있으므로** 그것을
# 묻는다. 전에는 없는 것을 물었고, 없는 것을 물으면 모델은 ★지어내서 채운다★.
_EXTRACT = (
    "You turn a flight results page into structured rows.\n"
    "The text comes from a flight search listing: each flight shows its departure "
    "and arrival time, how long it takes, whether it is nonstop, the airline, and "
    "the fare.\n"
    "Return ONLY a JSON array. Each item:\n"
    # ★코드셰어가 붙어서 온다★ (2026-08-21 · 찍어 보고 알았다) 목록 페이지는 운항사와
    # 판매사를 구분자 없이 잇대어 쓴다(`진에어대한항공`). 그대로 옮기니 화면 카드에
    # ★`Jin AirKorean Air`★ 라는 있지도 않은 항공사가 섰다. 코드로 가르려 했지만
    # 대문자 경계로 자르면 `JetBlue`가 `Jet Blue`로 쪼개진다 — **파는 쪽이 아니라
    # 태우는 쪽**을 고르는 판단이라 여기서 시킨다.
    '{"airline": str (ONE airline -- the one that actually operates the flight; if '
    'the page runs two names together for a codeshare, keep only the operating one),\n'
    ' "origin": str (airport code if shown), "destination": str '
    '(airport code if shown), "depart": str (YYYY-MM-DD or empty),\n'
    ' "leaves": str (departure clock time exactly as printed, e.g. "7:10 AM" or '
    '"19:25"), "arrives": str (arrival time, same form),\n'
    ' "stops": int, "duration_minutes": int (total travel time, 0 if not shown),\n'
    ' "price": int (digits only, 0 if the page says the price is unavailable), '
    '"currency": "KRW"|"USD"|…,\n'
    ' "fare_type": "round_trip" | "one_way" | "" (what the price covers -- leave it\n'
    '   EMPTY unless the page actually says; the user reads this as money),\n'
    ' "url": str, "note": str (one short sentence)}\n'
    "★Never invent a price, a time, a date, a duration or a flight that is not on "
    "the page. Use 0 or an empty string when unknown -- a guessed number becomes a "
    "fact on the user's screen.★\n"
    f"At most {MAX_KEPT} items."
)

# ── ★항공편 목록을 여는 주소★ ────────────────────────────────────────────────
#
# ★영어로 연다★(`hl=en`) 우리 정규형과 판정이 영어 낱말로 되어 있고, 사람이 읽을
# 글은 표시할 때 번역한다(CLAUDE.md: 주석은 한국어여도 값은 영어). 페이지 언어를
# 사용자 언어로 바꾸면 모델이 옮겨야 할 낱말이 매번 달라져 ★옮기기가 언어를 탄다★.
#
# ⚠️ ★통화는 다르다 — 그것은 **값**이다★ 사용자가 아는 돈으로 보여야 하므로
# 설정에서 받는다(`currency`). 이 둘의 경계가 이 저장소의 다국어 규율 그대로다.
FLIGHTS_URL = "https://www.google.com/travel/flights"

# 날짜 표를 여는 단추의 이름(그 페이지의 접근성 이름). ★표가 어휘를 정한다★
DATE_GRID_BUTTON = "date grid"

_IATA = re.compile(r"^[A-Z]{3}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")

# 화면이 그리는 신호 중 **우리가 채우는 것**. ★표에 있는데 아무도 안 채우면 그 칸은
# 영영 "모름"이다★(함정 74) — 그래서 여기 적힌 둘은 `_EXTRACT`가 실제로 물어본다.
SHOWN_SIGNALS = ("stops", "duration", "when")

# 화면 상태가 사는 파일. ★코드가 아니라 **상태**의 자리다★
_STATE_FILE = "last_view.json"


@dataclass
class Flight:
    """항공편 하나의 **정규형**. 모르는 것은 비워 둔다."""

    airline: str = ""
    origin: str = ""
    destination: str = ""
    depart: str = ""
    # ★그 날의 **몇 시 비행기인가**★ (Sean 지적 2026-08-21 — *"가격과 일정"*)
    #
    # 검색 결과로 값을 얻던 시절에는 이 둘을 채울 수가 없었다(광고 문구에는 시각이
    # 없다). 그래서 화면에는 값만 넷 있고 ★어느 것이 아침이고 어느 것이 밤인지
    # 알 수 없었다★ — 항공권을 고르는 사람이 값 다음으로 보는 것이 이것인데도.
    # "HH:MM" 24시로 둔다(비면 모르는 것이다). 날짜는 `depart`가 진다.
    leaves: str = ""
    arrives: str = ""
    stops: int = 0
    minutes: int = 0
    # ★이 값이 **무엇을 덮는가**★ `round_trip` · `one_way` · 빈 문자열(모른다).
    # 돈에 관한 것이라 ★모르면 모른다고 둔다★ — 왕복으로 찾았다고 편도 값을
    # 왕복 값으로 읽게 하면 사용자는 두 배를 잘못 계산한다.
    fare_type: str = ""
    price: int = 0
    currency: str = ""
    url: str = ""
    note: str = ""
    seen_at: str = ""

    def key(self) -> str:
        """같은 편인가를 가르는 열쇠 — 항공사 + 노선 + 날짜."""
        return "|".join((self.airline.strip().lower(), self.origin.strip().lower(),
                         self.destination.strip().lower(), self.depart.strip()))


# ── 판정 — ★순수 함수★ ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class Trip:
    """★사용자가 말한 **조건 한 덩어리**★ (Sean 요구 2026-08-19)

    > *"원하는 항공사와 날짜를 전달하면, 그 외 조건 왕복 여부 등을 전달하면 그에
    >  맞는 항공권을 보여주면 좋음"*

    조건을 인자로 흩어 두면 **가는 자리마다 하나씩 빠진다** — 실제로 `return_on`이
    선언만 되고 아무도 안 쓰고 있었다(고르는 화면에도, 검색어에도, 기억에도 없었다).
    한 덩어리로 다니면 검색·필터·기억·배경 재점검이 **같은 것**을 본다.

    ⚠️ ★조건은 **열쇠의 일부**다★ 왕복과 편도는 값이 다른 별개의 물건이고,
    *"대한항공으로"* 는 값을 지켜볼 대상 자체를 바꾼다. 열쇠에서 빼면 어제 본
    대한항공 값과 오늘 본 아무 항공사 값을 빼서 ★있지도 않은 인하★를 말하게 된다.
    """

    origin: str = ""
    destination: str = ""
    depart: str = ""
    return_on: str = ""
    airline: str = ""
    nonstop: bool = False

    @property
    def round_trip(self) -> bool:
        return bool(self.return_on)


def trip_of(args: dict) -> Trip:
    """도구 인자를 조건 한 덩어리로. ★못 읽는 날짜는 **없는 것**이다★ ★순수 함수★"""
    args = args if isinstance(args, dict) else {}
    return Trip(origin=str(args.get("origin") or "").strip(),
                destination=str(args.get("destination") or "").strip(),
                depart=_date(args.get("depart", "")),
                return_on=_date(args.get("return_on", "")),
                airline=str(args.get("airline") or "").strip()[:60],
                nonstop=_truthy(args.get("nonstop")))


def _truthy(value) -> bool:
    """모델은 `true`를 문자열로도 준다. ★"false"를 참으로 읽으면 직항만 남는다★"""
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1", "y")
    return bool(value)


def matches_trip(flight: "Flight", trip: Trip) -> bool:
    """이 항공편이 **사용자가 말한 조건**에 맞나. ★순수 함수★

    ★항공사는 **느슨하게** 견준다★ 결과가 *"Korean Air"* · *"대한항공"* · *"KE"* 로
    제각각 오는데, 딱 맞는 것만 남기면 사용자는 *"대한항공으로"* 라고 말하고 빈
    화면을 받는다. 한쪽이 다른 쪽에 들어 있으면 같은 것으로 본다.

    ## ⚠️ ★왕복을 물었으면 **편도 값을 섞지 않는다**★ (2026-08-19 · 찍어 보고 알았다)

    첫 그림에서 *"추천"* 이 **189,000 편도**에 붙어 있었다 — 사용자는 왕복을 물었고,
    같은 화면에 **212,000 왕복**이 있었는데도. 편도를 왕복으로 치면 대략 378,000이니
    그 추천은 정반대였다. ★값이 덮는 범위가 다르면 그 둘은 견줄 수 없다★(통화가
    다르면 안 빼는 것과 같은 이유).

    ⚠️ ★비대칭이 정당하다★ 반대로 편도를 찾을 때 왕복 값이 섞이는 것은 막지 않는다 —
    날짜만 준 검색은 *"그냥 도쿄행"* 이라 왕복 값도 참고가 되고, 카드가 *"왕복"* 이라고
    말하므로 사용자가 안다. **왕복이라고 말한 쪽만** 요구가 분명하다.

    ★모르는 것은 안 버린다★ 값이 무엇을 덮는지 결과에 안 적힌 경우가 흔한데, 그것까지
    버리면 왕복 검색은 거의 언제나 빈손이 된다.
    """
    if trip.nonstop and flight.stops:
        return False
    if trip.round_trip and flight.fare_type == "one_way":
        return False
    wanted = trip.airline.strip().lower()
    if not wanted:
        return True
    got = str(flight.airline or "").strip().lower()
    return bool(got) and (wanted in got or got in wanted)


def route_name(origin: str, destination: str, depart: str = "", *,
               return_on: str = "", airline: str = "", nonstop: bool = False) -> str:
    """이 노선을 부르는 이름. ★기억을 합치는 열쇠이기도 하다★ —
    이름이 갈리면 같은 노선을 두 곳에 쌓는다.

    ## ⚠️ ★날짜가 이름에 들어가는 이유★ (2026-08-19)

    물건과 달리 **같은 노선도 다른 날은 다른 것**이다. 날짜를 빼고 이름을 지으면
    12월 표를 한 번 찾아본 것이 9월 표의 기억을 덮고, 그다음 검색이 *"74만원
    올랐어요"* 라고 **일어나지 않은 인상**을 말한다.

    ★날짜는 **사용자가 말한 것**을 쓴다★ 결과에 실린 날짜가 아니다 — 사용자가
    *"언제 가는 표"* 를 물었는지가 그 사람의 의도이고, 검색 결과는 그 의도에 대한
    답일 뿐이다(불변 규칙: 사용자 발화가 이긴다).

    날짜를 안 말했으면 이름에도 없다 — 그것은 *"언젠가 도쿄"* 라는 다른 의도다.

    ## ★조건도 이름에 들어간다★ (Sean 요구 2026-08-19)

    같은 이유가 **왕복 여부**와 **항공사**에도 그대로 걸린다. 왕복은 편도와 값이
    다른 별개의 물건이고, *"대한항공으로"* 는 지켜볼 대상 자체를 바꾼다. 열쇠에서
    빼면 어제 본 대한항공 값과 오늘 본 아무 항공사 값을 빼서 ★있지도 않은 인하★를
    말한다. 이름이 곧 *"무엇을 지켜보는가"* 다:

        Flights ICN to Tokyo on 2026-09-10
        Flights ICN to Tokyo on 2026-09-10 returning 2026-09-14
        Flights ICN to Tokyo on 2026-09-10 with Korean Air, nonstop
    """
    start, end = _place(origin), _place(destination)
    when, back = _date(depart), _date(return_on)
    if not end:
        return ""
    name = f"Flights {start} to {end}" if start else f"Flights to {end}"
    if when:
        name += f" on {when}"
    if back:
        name += f" returning {back}"
    # ★조건은 **정해진 차례로** 붙인다★ 순서가 흔들리면 같은 조건이 두 이름이 되고,
    # 그러면 같은 것을 두 곳에 쌓는다(이름은 기억을 합치는 열쇠다).
    extra = [f"with {_place(airline)}"] if str(airline or "").strip() else []
    if nonstop:
        extra.append("nonstop")
    return f"{name} {', '.join(extra)}" if extra else name


def route_name_of(trip: Trip) -> str:
    """조건 한 덩어리에서 열쇠를. ★부르는 자리마다 칸을 하나씩 빠뜨리지 않도록★"""
    return route_name(trip.origin, trip.destination, trip.depart,
                      return_on=trip.return_on, airline=trip.airline,
                      nonstop=trip.nonstop)


def _place(text: str) -> str:
    raw = str(text or "").strip()
    return raw.upper() if _IATA.match(raw.upper()) and len(raw) == 3 else raw.title()


def _date(text: str) -> str:
    """`YYYY-MM-DD`만 통과시킨다. ★못 읽는 것은 **없는 것**이다★ — 반쯤 읽어
    이름에 끼우면 같은 날이 두 이름으로 갈린다."""
    found = _DATE.match(str(text or "").strip())
    return found.group(0) if found else ""


def to_flights(raw, *, now: str = "") -> list[Flight]:
    """모델이 옮겨 온 것을 정규형으로. ★깨진 것은 조용히 버린다★ — 한 줄이
    이상하다고 검색 전체를 실패로 만들면 사용자는 아무것도 못 본다."""
    stamp = now or now_ts()
    try:
        rows = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return []
    out: list[Flight] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        destination = str(row.get("destination") or "").strip()
        if not destination:
            continue                     # 어디로 가는지 모르면 항공편이 아니다
        out.append(Flight(
            airline=str(row.get("airline") or "").strip(),
            origin=str(row.get("origin") or "").strip(),
            destination=destination,
            depart=str(row.get("depart") or "").strip(),
            leaves=_clock(row.get("leaves")),
            arrives=_clock(row.get("arrives")),
            stops=_int(row.get("stops")),
            minutes=_int(row.get("duration_minutes")),
            fare_type=_fare_type(row.get("fare_type")),
            price=_int(row.get("price")),
            currency=str(row.get("currency") or "").strip().upper(),
            url=str(row.get("url") or "").strip(),
            note=str(row.get("note") or "").strip()[:200],
            seen_at=stamp))
    return out


_CLOCK = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)?$", re.I)


def _clock(value) -> str:
    """시각을 `HH:MM`(24시)로. ★못 읽는 것은 **없는 것**이다★ ★순수 함수★

    ⚠️ 페이지가 오전/오후로 쓰는 곳이 많아(`7:10 AM`) 모델이 그대로 옮겨 온다.
    반쯤 읽어 `7:10`으로 두면 ★저녁 7시 비행기가 아침 7시로 화면에 뜬다★ —
    사람이 그것을 보고 표를 고른다. 24시로 바꾸거나, 못 바꾸면 비운다.
    """
    got = _CLOCK.match(str(value or "").strip())
    if not got:
        return ""
    hour, minute, half = int(got.group(1)), int(got.group(2)), (got.group(3) or "").upper()
    if minute > 59 or (half and not 1 <= hour <= 12) or (not half and hour > 23):
        return ""
    if half == "PM" and hour < 12:
        hour += 12
    elif half == "AM" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def flights_url(trip: Trip, *, currency: str = "") -> str:
    """그 여정의 **항공편 목록 주소**. ★순수 함수★ (브라우저 없이 확인된다)

    ## ★왜 자연어로 묻나★

    구글 항공편은 조건을 `tfs=`라는 **인코딩된 덩어리**로도 받지만, 그것을 우리가
    만들면 판이 바뀔 때마다 조용히 부서진다(무엇이 틀렸는지도 안 보인다). `q=`에
    사람 말로 적으면 그쪽이 해석해 주고, **틀리면 화면에 그렇게 보인다**.

    ⚠️ ★조건을 여기 적는 것과 **거르는 것은 다른 일**이다★ 적으면 맞는 것이 더
    많이 올라오고, 거르는 것은 그래도 섞여 온 것을 쳐낸다. 둘 다 해야 한다
    (`matches_trip`).

    ★언어는 영어로 고정한다★ 옮겨야 할 낱말이 언어마다 달라지면 옮기기 자체가
    언어를 탄다. 사용자가 읽는 글은 표시할 때 번역된다(CLAUDE.md의 그 경계).
    """
    from urllib.parse import quote_plus
    said = ["Flights", "from", _place(trip.origin) or "anywhere",
            "to", _place(trip.destination)]
    if trip.depart:
        said += ["on", trip.depart]
    if trip.return_on:
        said += ["returning", trip.return_on]
    if trip.airline:
        said += ["on", _place(trip.airline)]
    if trip.nonstop:
        said.append("nonstop")
    query = quote_plus(" ".join(x for x in said if x))
    url = f"{FLIGHTS_URL}?q={query}&hl=en"
    if currency:
        url += f"&curr={quote_plus(currency)}"
    return url


# ── ★날짜를 바꿔 본다★ (Sean 요구 2026-08-21) ────────────────────────────────
#
# > *"날짜도 바꿔 보고 가격을 비교해 본다. 이것을 에이전트가 해야 하는 것이다."*
#
# 사람이 항공권을 살 때 하는 일 그대로다 — 하루 늦추면 얼마인지 본다. 목록 페이지의
# **날짜 표**가 앞뒤 며칠 값을 이미 계산해 두고 있어서, 그것을 열어 읽는다.
#
# ⚠️ ★이것만 누르기가 필요하다★(`browser.act`) 날짜 표는 주소로 안 열린다(실측).
# 그래서 ★못 눌러도 검색 자체는 살아 있어야 한다★ — 권한이 없거나 단추 이름이
# 바뀌면 날짜 비교만 빠지고 항공편은 그대로 나온다(있는 기능이 없는 기능을 죽이지
# 않는다).

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

# 표의 칸 하나가 **자기 값과 자기 날짜를 함께** 말한다:
#     "$215, Sep 12 to Sep 16"
#     "$174, low price, Sep 15 to Sep 16"
#     "$342, Sep 15 to Sep 19, selected"     ← 지금 보고 있는 조합
# 편도 표는 뒷날짜가 없다: "$174, Sep 15"
_GRID_CELL = re.compile(
    r"([₩$€£¥])\s?([\d,]{3,})"                 # 값
    r"(?:,\s*[a-z ]+)?"                        # "low price" 같은 꼬리표(있을 수도)
    r",\s*([A-Z][a-z]{2})\s(\d{1,2})"          # 가는 날
    r"(?:\s+to\s+([A-Z][a-z]{2})\s(\d{1,2}))?" # 오는 날(왕복일 때만)
)

_CURRENCY_SIGN = {"₩": "KRW", "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}


def read_date_grid(targets, *, around: str = "") -> list[dict]:
    """날짜 표에서 **날짜 조합마다의 값**을 뽑는다. ★순수 함수★

    받는 것은 페이지의 **누를 수 있는 것들**(`read_page`의 `targets`)이다.
    돌려주는 것: `[{"date","back","price","currency"}, …]` — `back`은 편도면 빈칸.

    ## ⚠️ ★글로 읽다가 날짜와 값을 어긋나게 붙였다★ (2026-08-21에 잡은 결함)

    처음에는 페이지 **본문**에서 날짜 목록과 값 목록을 따로 뽑아 자리로 짝지었다.
    그런데 그 표는 (가는 날 × 오는 날) 격자다 — 날짜는 머리줄에 일곱, 값은 칸마다
    마흔아홉. 자리로 맞추면 ★9월 15일에 남의 날 값이 붙는다★(실제로 $173이 붙었고,
    그것은 다른 조합의 값이었다). 그렇게 만든 *"더 싼 날"* 은 거짓말이 된다.

    ★칸마다 붙은 이름을 읽으면 짝지을 일이 아예 없다.★ 값과 날짜가 한 문장 안에
    있으니 어긋날 수가 없다 — 자리로 맞추는 코드를 **없앤 것**이 고침이다.
    """
    year = (around or "")[:4]
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for target in targets or ():
        if not isinstance(target, dict):
            continue
        label = " ".join(str(target.get(k) or "")
                         for k in ("label", "aria", "name"))
        found = _GRID_CELL.search(label)
        if not found:
            continue
        sign, amount, month, day, back_month, back_day = found.groups()
        date = _grid_date(month, day, year)
        price = _int(str(amount).replace(",", ""))
        if not date or not price:
            continue
        back = _grid_date(back_month or "", back_day or "", year)
        key = (date, back)
        if key in seen:
            continue
        seen.add(key)
        out.append({"date": date, "back": back, "price": price,
                    "currency": _CURRENCY_SIGN.get(sign, "")})
    return sorted(out, key=lambda row: (row["date"], row["back"]))


def _grid_date(month: str, day: str, year: str = "") -> str:
    """`Sep`·`16` → `2026-09-16`. 해를 모르면 비운다. ★순수 함수★

    ⚠️ ★해를 짐작하지 않는다★ 12월에 1월 표를 보면 해가 넘어가는데, 그것을 여기서
    맞히려 들면 틀린 날짜가 열쇠에 들어가 **다른 여정의 기억을 덮는다**.
    부르는 쪽이 보고 있던 날짜(`around`)의 해를 준다.
    """
    if not year.isdigit() or month not in _MONTHS:
        return ""
    number = _MONTHS.index(month) + 1
    got = _int(day)
    if not 1 <= got <= 31:
        return ""
    return f"{year}-{number:02d}-{got:02d}"


def cheaper_days(grid: list[dict], *, than: int, on: str = "",
                 back: str = "") -> list[dict]:
    """지금 보는 값보다 **싼 날짜 조합**만, 싼 순서로. ★순수 함수★

    ★보고 있는 조합은 뺀다★ 그것이 목록에 그대로 있으면 *"9월 15일에 가면 더
    싸요"* 라고 자기가 보던 날을 권하게 된다.

    ## ⚠️ ★돌아오는 날을 빼놓으면 **다른 여행을 권하게 된다**★

    표는 (가는 날 × 오는 날) 격자다. 값만 보고 고르면 *"$169로 더 싸요"* 가
    실제로는 **당일치기**일 수 있다(`Sep 16 to Sep 16`이 그랬다). 사용자가 나흘
    여행을 계획하는데 그것을 권하는 것은 싼 것이 아니라 **다른 것**이다.

    그래서 돌아오는 날을 아는 여정이면 ★같은 날 돌아오는 칸만★ 본다. 모르면
    (편도이거나 아직 안 정했으면) 그 축으로 거를 근거가 없으므로 전부 본다 —
    대신 각 줄이 자기 `back`을 지고 다녀서 화면이 **며칠 여행인지 말할 수 있다**.
    """
    if than <= 0:
        return []
    rows = []
    for row in grid:
        if int(row.get("price") or 0) <= 0 or int(row["price"]) >= than:
            continue
        if back and str(row.get("back") or "") != back:
            continue
        if row.get("date") == on and str(row.get("back") or "") == back:
            continue
        rows.append(row)
    return sorted(rows, key=lambda row: (row["price"], row["date"]))


def _fare_type(value) -> str:
    """★아는 둘만 통과한다★ 모델이 지어낸 낱말이 화면에 그대로 뜨면 그것은 정보가
    아니라 오류로 읽힌다. 모르면 빈 문자열 — 그때는 화면이 아무 말도 안 한다."""
    got = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return got if got in ("round_trip", "one_way") else ""


def fare_type_text(fare_type: str) -> str:
    """값이 무엇을 덮는지 한 낱말. 모르면 빈 문자열(빈칸이 곧 *"모른다"* 다)."""
    if fare_type == "round_trip":
        return i18n.t("Round trip")
    return i18n.t("One way") if fare_type == "one_way" else ""


def _int(value) -> int:
    try:
        return max(0, int(float(str(value))))
    except (TypeError, ValueError):
        return 0


def rank(flights: list[Flight]) -> list[Flight]:
    """싼 것부터, 같으면 **덜 갈아타는** 것부터 — ★그리고 미는 하나를 맨 앞에★

    ★가격을 모르는 것은 맨 뒤로★ 0을 '공짜'로 읽으면 값을 모르는 항공편이
    추천 1순위가 된다 — 실제로 쇼핑에서 겪은 부류의 실수다.

    ## ⚠️ ★값만으로 1위를 뽑으면 안 된다★ (2026-08-19 · 찍어 보고 알았다)

    첫 그림에서 *"추천"* 이 **13시간 걸리고 두 번 갈아타는** 표에 붙어 있었다. 값순
    정렬의 1번을 그대로 민 결과다. 물건은 싼 것이 대체로 좋은 것이지만, ★표는
    싼 것이 대체로 **고된 것**★이다 — 그래서 같은 규칙을 그대로 옮기면 안 된다.

    ★그렇다고 점수로 합치지 않는다★ 값과 시간을 하나로 버무리면 근거가 사라지고,
    근거 없는 순위는 광고와 구별되지 않는다(화면 계약이 못 박은 규율 그대로).
    대신 **말할 수 있는 규칙 하나**를 쓴다: ★가장 적게 갈아타는 무리에서 가장 싼 것★.
    그러면 카드가 자기 이유를 한 문장으로 말할 수 있다.

    ⚠️ ★자르는 수가 **한 화면**이 아니다★ 넷만 남기면 *"다음 보기"* 라고 말할 것이
    애초에 없어지고, 마음에 드는 게 없을 때 사용자가 같은 검색을 다시 해야 한다.
    """
    ordered = sorted(flights,
                     key=lambda f: (f.price == 0, f.price, f.stops,
                                    f.airline))[:MAX_KEPT]
    pick = best_pick(ordered)
    if pick is None or ordered.index(pick) == 0:
        return ordered
    # ★미는 것을 **맨 앞으로 끌어온다**★ 뒤에 두면 첫 쪽에 안 보일 수 있고, 화면에
    # 없는 것을 가리키는 추천은 사용자를 그 자리에서 멈추게 한다.
    rest = [f for f in ordered if f is not pick]
    return [pick, *rest]


def best_pick(flights: list[Flight]) -> Flight | None:
    """★미는 하나 — 가장 적게 갈아타는 무리에서 가장 싼 것★ ★순수 함수★

    값을 아는 것만 본다(모르는 값을 밀면 사용자는 눌러 보고서야 안다).
    하나도 값을 모르면 None — ★없으면 없다고 한다★.
    """
    priced = [f for f in flights if f.price > 0]
    if not priced:
        return None
    fewest = min(f.stops for f in priced)
    return min((f for f in priced if f.stops == fewest), key=lambda f: f.price)


def pick_reason(flights: list[Flight], pick: Flight | None) -> str:
    """미는 이유 한 문장. ★이유 없는 순위는 광고와 구별되지 않는다★

    가장 싸기도 하면 이유를 따로 대지 않는다 — 값이 이미 보이는데 *"가장 싸다"* 를
    글로 또 쓰면 그 줄은 정보가 아니라 장식이다.
    """
    if pick is None:
        return ""
    low = cheapest(flights)
    if low is not None and low is pick:
        return ""
    return i18n.t("Cheapest of the ones with {stops}.", stops=stops_text(pick.stops))


def cheapest(flights: list[Flight]) -> Flight | None:
    """값을 아는 것 중 가장 싼 것. 하나도 모르면 None."""
    priced = [f for f in flights if f.price > 0]
    return min(priced, key=lambda f: f.price) if priced else None


def cheapest_index(items: list[dict]) -> int:
    """값을 아는 것 중 **가장 싼 것**이 전체에서 몇 번째인가(없으면 -1). ★순수 함수★

    ★한 쪽만 보고 정하면 거짓말이 된다★ 화면은 넷씩 받는데, 그 넷에서 가장 싼 것에
    *"최저가"* 를 달면 다음 쪽에 더 싼 것이 있을 때 그 글자가 거짓이 된다(쇼핑에서
    찍어 보고 알았다). 전체를 아는 쪽이 판정한다.
    """
    best, at = 0, -1
    for n, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        try:
            price = int(item.get("price") or 0)
        except (TypeError, ValueError):
            continue
        if price > 0 and (at < 0 or price < best):
            best, at = price, n
    return at


def page_of(items: list, page: int = 0, size: int = PAGE_SIZE) -> tuple[list, int, int]:
    """지금 쪽 · 몇 쪽째인가 · 모두 몇 쪽인가. ★순수 함수★

    ★끝에서 첫 쪽으로 **되감지 않는다**★ — 되감으면 사용자는 *"다음"* 을 눌렀는데
    처음 것이 나와서 새 목록으로 읽는다. 끝은 끝이라고 말해야 다음 행동을 고른다.
    """
    size = max(1, int(size))
    pages = max(1, -(-len(items) // size))          # 올림 나눗셈
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 0
    page = max(0, min(page, pages - 1))
    return items[page * size:(page + 1) * size], page, pages


def signals_worth_showing(items: list[dict]) -> list[str]:
    """이 후보들에서 **누구 하나라도 아는** 신호만. ★순수 함수★

    ★아무도 모르는 신호는 칸을 차지하지 않는다★ 화면은 모르는 값을 *"모름"* 으로
    그리는데(빈칸은 "없다"로 읽히니까 옳다), 넷이 다 *"모름"* 인 줄은 아무것도
    말하지 않으면서 자리만 먹는다. 순서는 화면 계약의 표를 따른다.
    """
    return [key for key in COMPARE_SIGNALS
            if key in SHOWN_SIGNALS
            and any((i.get("signals") or {}).get(key) not in (None, "")
                    for i in items if isinstance(i, dict))]


def money(price, currency: str = "") -> str:
    """★통화는 항공편이 정한다★ '원'을 코드에 박으면 달러로 파는 표가 원으로 읽힌다.
    통화 이름은 번역하지 않는다 — 'KRW'는 어느 언어에서도 KRW다."""
    try:
        value = int(price or 0)
    except (TypeError, ValueError):
        value = 0
    if not value:
        return i18n.t("Price unknown")
    code = str(currency or "").upper().strip()
    return f"{value:,} {code}".strip() if code else f"{value:,}"


def when_text(leaves, arrives) -> str:
    """*"07:10 → 10:00"*. 둘 다 모르면 빈 문자열. ★순수 함수★

    ★비는 것이 맞다★ 모르는 것을 *"모름"* 으로 채우면 비교 칸 여섯이 전부 진해져서
    ★갈리는 값이 안 보인다★(화면 계약이 못 박은 자리 — 같은 값은 물러난다).

    ⚠️ 도착만 아는 일은 없다시피 하지만, 있으면 그것만이라도 보인다.
    """
    start, end = str(leaves or "").strip(), str(arrives or "").strip()
    if start and end:
        return f"{start} → {end}"
    return start or end


def duration_text(minutes) -> str:
    """소요 시간을 사람이 읽는 모양으로. 모르면 빈 문자열(0을 '0분'으로 쓰면 거짓말).

    ★서식도 언어를 탄다★ 'h'·'m'을 박아 두면 다른 언어에서 그대로 남는다.
    """
    try:
        total = max(0, int(minutes or 0))
    except (TypeError, ValueError):
        return ""
    if not total:
        return ""
    hours, mins = divmod(total, 60)
    if hours and mins:
        return i18n.t("{h}h {m}m", h=hours, m=mins)
    return i18n.t("{h}h", h=hours) if hours else i18n.t("{m}m", m=mins)


def stops_text(stops) -> str:
    """갈아타는 횟수를 말로. ★0은 '0번'이 아니라 '직항'이다★"""
    try:
        count = max(0, int(stops or 0))
    except (TypeError, ValueError):
        count = 0
    if not count:
        return i18n.t("Nonstop")
    return i18n.t("{n} stop", n=count) if count == 1 else i18n.t("{n} stops", n=count)


def price_change(before: int, after: int) -> dict:
    """값이 어느 쪽으로 얼마나 움직였나. ★순수 함수★

    ★문턱을 넘지 않으면 '그대로'다★ 100원 차이를 "내렸다"고 말하면 그것은 소음이고,
    소음이 몇 번 반복되면 사용자는 진짜 인하도 안 믿는다.
    """
    before, after = int(before or 0), int(after or 0)
    if not before or not after:
        return {"direction": "unknown", "delta": 0, "ratio": 0.0}
    delta = after - before
    ratio = abs(delta) / before
    if ratio < PRICE_CHANGE_MIN_RATIO:
        return {"direction": "same", "delta": delta, "ratio": ratio}
    return {"direction": "down" if delta < 0 else "up",
            "delta": delta, "ratio": ratio}


def alert_floor(currency: str) -> int:
    """이 통화에서 알릴 만한 **최소 금액**. 모르는 통화는 0(=비율만으로 판정). ★순수★"""
    return ALERT_MIN_DELTA.get(str(currency or "").upper().strip(), 0)


def worth_interrupting(before: int, after: int, *, currency: str = "",
                       last_alert: str = "", now: str = "") -> dict:
    """이 값 변화로 **하던 일을 멈추게 해도 되는가**. ★순수 함수★

    돌려주는 것은 판정과 **그 이유**다 — 이유 없는 알림은 광고와 구별되지 않고,
    사용자가 *"왜 이걸 지금 말하지"* 라고 물을 때 답할 것이 있어야 한다.

    ★오른 것은 알리지 않는다★ *"12만원 올랐어요"* 로 표를 살 수 있는 사람은 없다.
    올랐다는 사실은 화면이 말한다(거기서는 값이 있다 — 기다릴지 정하는 재료다).
    """
    move = price_change(before, after)
    if move["direction"] != "down":
        return {"tell": False, "reason": "not_cheaper", **move}
    floor = alert_floor(currency)
    if move["ratio"] < ALERT_MIN_RATIO or abs(move["delta"]) < floor:
        return {"tell": False, "reason": "too_small", **move}
    if not _quiet_enough(last_alert, now):
        # ★같은 노선으로 이틀 연속 말을 걸면 두 번째부터는 안 듣는다★
        return {"tell": False, "reason": "told_recently", **move}
    return {"tell": True, "reason": "cheaper", **move}


def _quiet_enough(last_alert: str, now: str = "") -> bool:
    if not str(last_alert or "").strip():
        return True
    gap = _seconds_between(last_alert, now)
    return gap is None or gap >= ALERT_QUIET_SEC


def due_for_recheck(last_checked: str, *, now: str = "",
                    every_sec: float = RECHECK_EVERY_SEC) -> bool:
    """배경에서 다시 볼 때가 됐나. ★순수 함수★

    한 번도 안 봤으면 **본다**(빈 값을 "방금 봤다"로 읽으면 영영 안 본다 — 이
    저장소가 여러 번 데인 모양이다).
    """
    if not str(last_checked or "").strip():
        return True
    gap = _seconds_between(last_checked, now)
    return gap is None or gap >= max(60.0, float(every_sec))


def has_flown(depart: str, *, now: str = "") -> bool:
    """★이 비행기는 이미 떠났나★ ★순수 함수★

    떠난 표가 싸졌다는 말은 아무 값이 없다. 날짜를 모르면 **떠나지 않은 것으로**
    본다 — 모른다고 지워 버리면 날짜 없이 찾아본 의도가 통째로 사라진다.

    ⚠️ ★시각이 아니라 **날짜**로 가른다★ 출발일은 하루지 한 순간이 아니다. 시각으로
    빼면 `2026-08-19`가 자정으로 읽혀 **그날 아침에 이미 "떠났다"** 가 된다 — 오늘
    저녁 비행기를 지켜보던 사람이 그날 아침에 조용히 목록에서 빠지는 것이다.
    """
    when = _date(depart)
    if not when:
        return False
    today = _date(now) or _date(now_ts())
    return bool(today) and when < today


def still_wanted(row: dict, *, now: str = "") -> bool:
    """이 표를 **아직 사려고 하는가**. ★순수 함수★

    넷 중 하나라도 아니면 지켜보지 않는다:

      ① ★예약했다고 말한 것★ — 끊고 나서 *"더 싸졌어요"* 는 도움이 아니라 상처다
      ② ★안 가겠다고 한 것★ — 사람이 접은 것을 우리가 계속 들이밀지 않는다
      ③ ★이미 떠난 것★ — 항공권에만 있는 축이다(물건에는 이런 끝이 없다)
      ④ ★너무 오래된 것★ — 반 년 전 마음을 지금 마음으로 치면 그것은 참견이다

    ⚠️ ★"결제 화면까지 갔다"는 **예약했다가 아니다**★ 우리가 발권하지 않으므로 알
    방법이 없다. 사람이 *"끊었어"* 라고 말한 것만 끈다 — 추측으로 끄면 정말 아직
    안 끊은 사람의 알림이 사라진다.
    """
    if not isinstance(row, dict):
        return False
    if str(row.get("booked_at") or "").strip():
        return False                       # ①
    if str(row.get("dropped_at") or "").strip():
        return False                       # ②
    if has_flown(str(row.get("depart") or ""), now=now):
        return False                       # ③
    seen = str(row.get("seen_at") or "")
    return _days_between(seen, now or now_ts()) <= STALE_AFTER_DAYS   # ④


def compare_with_past(past: dict, fresh: list[Flight], *, now: str = "") -> dict:
    """지난번과 이번을 나란히 놓는다 — ★무엇을 말할지까지 정한다★

    - `first_time` — 처음 보는 노선인가
    - `delta`      — 최저가가 얼마나 움직였나(음수면 내렸다). 모르면 None
    - `stale`      — 지난 검색이 너무 오래됐다(그때는 "지난번"을 들이밀지 않는다)
    - `booked`     — 이미 끊었다고 말한 노선인가(그러면 값 이야기를 하지 않는다)

    ★판정을 화면과 말이 나눠 갖지 않는다★ 두 곳에서 판정하면 서로 다른 것을 말한다.
    """
    now_best = cheapest(fresh)
    booked = bool(str((past or {}).get("booked_at") or "").strip())
    dropped = bool(str((past or {}).get("dropped_at") or "").strip())
    base = {"booked": booked, "dropped": dropped,
            "currency": (past or {}).get("currency", "")
                        or (now_best.currency if now_best else "")}
    if not past or not past.get("price"):
        return {**base, "first_time": True, "delta": None, "stale": False,
                "was": 0, "now": now_best.price if now_best else 0}
    stale = _days_between(str(past.get("seen_at") or ""),
                          now or now_ts()) > STALE_AFTER_DAYS
    if stale or now_best is None:
        return {**base, "first_time": False, "delta": None, "stale": stale,
                "was": int(past.get("price") or 0),
                "now": now_best.price if now_best else 0}
    was = int(past.get("price") or 0)
    return {**base, "first_time": False, "delta": now_best.price - was,
            "stale": False, "was": was, "now": now_best.price}


def _seconds_between(then: str, now: str = "") -> float | None:
    """`then` 에서 `now` 까지의 초. 못 읽으면 None(=모른다).

    ⚠️ ★시간대가 섞인다★ `now_ts()`는 시간대 없는 시각을 주는데, 브레인에 남은
    값은 다른 경로에서 온 **시간대 있는** 시각일 수 있다. 그 둘을 그냥 빼면
    `TypeError`가 나고 — 그물이 그것을 잡았다 — 그러면 비교가 통째로 죽어
    **검색 전체가 실패로** 돌아간다. 없는 시간대는 UTC로 보고 맞춘다.
    """
    from datetime import datetime, timezone
    stamps = []
    for text in (then, now or now_ts()):
        try:
            when = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        stamps.append(when.replace(tzinfo=timezone.utc) if when.tzinfo is None
                      else when.astimezone(timezone.utc))
    return (stamps[1] - stamps[0]).total_seconds()


def _days_between(then: str, now: str) -> float:
    """두 시각 사이의 날수. 못 읽으면 0(=오래되지 않았다고 본다)."""
    gap = _seconds_between(then, now)
    return 0.0 if gap is None else abs(gap) / 86400.0


def headline(route: str, flights: list[Flight], diff: dict) -> str:
    """말로 할 한두 줄. ★목록을 읽어 주지 않는다★ — 사람은 넷째쯤에서 앞을 잊는다.

    ★지난번 이야기가 맨 앞이다★ 그것이 이 에이전트의 값어치이기 때문이다.
    """
    if not flights:
        return i18n.t("I found nothing for {route}.", route=route)
    best = flights[0]
    where = f"{best.airline} {money(best.price, best.currency)}".strip()
    lead = ""
    delta = diff.get("delta")
    unit = diff.get("currency") or best.currency
    if diff.get("booked"):
        # ★끊은 사람에게 값 이야기를 하지 않는다★ 도움이 아니라 상처다
        lead = i18n.t("You said you booked this one. ")
    elif delta is not None and delta < 0:
        lead = i18n.t("That route is down {amount} since you last looked. ",
                      amount=money(abs(delta), unit))
    elif delta is not None and delta > 0:
        lead = i18n.t("That route is up {amount} since you last looked. ",
                      amount=money(delta, unit))
    elif diff.get("stale"):
        lead = i18n.t("It has been a while since you looked at this one. ")
    return lead + i18n.t("Best now: {what}, {stops}.",
                         what=where, stops=stops_text(best.stops))


# ── 기억 (원칙 0) ────────────────────────────────────────────────────────────
#
# ★담는 것과 꺼내는 것이 한 쌍이다★ 아래의 문 넷이 그 짝이다:
#
#     remember_search   ↔  recall_route        지난번 이 노선을 얼마에 봤나
#     remember_outcome  ↔  still_wanted        끊었나 · 접었나
#     remember_check    ↔  due_for_recheck     배경에서 마지막으로 본 때
#     (관측 쌓기)       ↔  price_history       값이 어느 쪽으로 가고 있나
#
# 담기만 하는 문은 절반만 만든 것이고, 이 저장소가 일곱 번 데인 자리다(원칙 0 ③).

# 사람이 **말한 것**만 여기 들어온다. 우리가 발권하지 않으므로 추측은 없다.
OUTCOMES: dict[str, dict] = {
    "booked":  {"attr": "booked_at",  "desc": "The person said they booked it"},
    "dropped": {"attr": "dropped_at", "desc": "The person said they are not going"},
}


def remember_search(brain, user_id: str, origin: str, destination: str,
                    flights: list[Flight], *, depart: str = "", trip: Trip | None = None,
                    agent=None, now: str = "") -> str:
    """이번 검색을 남긴다 — **의도(`wish`)와 목적지(`place`)로**.

    ★조건도 함께 남는다★(Sean 요구 2026-08-19) 왕복인지·어느 항공사인지·직항만인지가
    안 남으면 **배경 재점검이 다른 것을 보고 온다** — 그리고 그 값으로 *"내렸다"* 를
    말하면 거짓말이 된다.

    ★가격은 **관측으로** 남긴다★ *"지금 89만원"* 이 아니라 *"이 시각에 89만원이었다"*
    이므로 나중에도 참이고, 그래야 다음번에 *"내렸다"* 를 말할 수 있다.

    ★그리고 관측은 **쌓인다**★ 마지막 값 하나만 남기면 *"내렸다/올랐다"* 는 말할 수
    있어도 **어느 쪽으로 가고 있는지**는 못 말한다. 사람이 표를 살 때 실제로 묻는
    것은 후자다(*"더 기다리면 더 내릴까"*).

    `provenance="user"` — 어디에 가려는지는 사용자의 것이라 자동 파이프라인이
    덮으면 안 된다(불변 규칙).
    """
    trip = trip or Trip(origin=origin, destination=destination, depart=_date(depart))
    route = route_name_of(trip)
    if brain is None or not route:
        return ""
    stamp = now or now_ts()
    trust = Trust(confidence=1.0, provenance="user", source_channel=CHANNEL)
    best = cheapest(flights)
    known = _wish_of(brain, user_id, route)
    attrs = {**trust.to_attrs(),
             "origin": _place(trip.origin), "destination": _place(trip.destination),
             "depart": trip.depart,
             # ★조건을 남긴다★ 배경 재점검이 **같은 것**을 보고 오게 하는 재료다
             "return_on": trip.return_on, "airline": trip.airline,
             "nonstop": bool(trip.nonstop),
             "price": best.price if best else 0,
             "currency": best.currency if best else "",
             "seen_at": stamp, "last_searched": stamp}
    if best:
        # ★관측은 읽어서 이어 붙인다★ 리스트 칸은 병합이 아니라 **교체**된다 —
        # 그냥 넘기면 매번 점 하나짜리 이력이 되고, 화면은 영영 선을 못 그린다.
        attrs["history"] = _extend_history(
            (getattr(known, "attrs", None) or {}).get("history"), stamp, best.price)
    wish_id = brain.upsert_entity(user_id, Entity(
        name=route[:120], kind="wish", attrs=attrs, valid_from=stamp))
    if not wish_id:
        return ""                    # 사용자가 지운 항목은 되살리지 않는다(툼스톤)

    made = [wish_id]
    where = _place(trip.destination)
    if where:
        place_id = brain.upsert_entity(user_id, Entity(
            name=where[:120], kind="place",
            attrs={**trust.to_attrs(), "last_considered": stamp},
            valid_from=stamp))
        if place_id:
            made.append(place_id)
            brain.upsert_relation(user_id, Relation(
                src=wish_id, dst=place_id, rel="about",
                attrs={**trust.to_attrs()}, valid_from=stamp))
    if agent is not None:
        provenance.record(brain, user_id, agent, made, now=stamp)
    listed = " · ".join(f"{f.airline} {f.price}" for f in flights[:PAGE_SIZE])
    brain.remember(user_id, MemoryItem(
        text=f"Looked at flights: {route}. {listed}".strip(),
        kind=ITEM_KIND, ts=stamp,
        meta={"route": route, "price": best.price if best else 0,
              **trust.to_attrs(), **entity_links(*made)}))
    return wish_id


def _extend_history(old, stamp: str, price: int) -> list[dict]:
    """관측 하나를 이력에 잇는다. ★같은 값이 이어지면 점을 늘리지 않는다★ —
    반나절마다 같은 값을 찍으면 선은 평평한데 점만 스물넷이 된다. ★순수 함수★"""
    rows = [r for r in (old or []) if isinstance(r, dict) and r.get("price")]
    if rows and int(rows[-1].get("price") or 0) == int(price):
        rows[-1] = {"ts": stamp, "price": int(price)}
        return rows[-MAX_HISTORY:]
    rows.append({"ts": stamp, "price": int(price)})
    return rows[-MAX_HISTORY:]


def _wish_of(brain, user_id: str, route: str):
    """이 노선의 의도 노드. 없으면 None. ★이름으로 정확히 가른다★ — 느슨하게 맞히면
    9월 표의 기억이 12월 표에 붙는다."""
    if brain is None or not route:
        return None
    try:
        rows = brain.find_entities(user_id, kind="wish") or []
    except Exception:
        return None
    for entity in rows:
        if str(getattr(entity, "name", "")).lower() == route.lower():
            return entity
    return None


def recall_route(brain, user_id: str, origin: str = "", destination: str = "",
                 depart: str = "", *, trip: Trip | None = None) -> dict:
    """이 조건으로 전에 봤나. 못 찾으면 빈 dict — ★지어내지 않는다★"""
    trip = trip or Trip(origin=origin, destination=destination, depart=_date(depart))
    route = route_name_of(trip)
    entity = _wish_of(brain, user_id, route)
    if entity is None:
        return {}
    attrs = getattr(entity, "attrs", None)
    attrs = attrs if isinstance(attrs, dict) else {}
    return {"route": route, "wish_id": getattr(entity, "id", ""),
            "price": int(attrs.get("price") or 0),
            "currency": attrs.get("currency", ""),
            "depart": attrs.get("depart", ""),
            "return_on": attrs.get("return_on", ""),
            "airline": attrs.get("airline", ""),
            "nonstop": bool(attrs.get("nonstop")),
            "seen_at": attrs.get("seen_at", ""),
            "booked_at": attrs.get("booked_at", ""),
            "dropped_at": attrs.get("dropped_at", ""),
            "history": price_history(attrs)}


def price_history(attrs: dict) -> list[dict]:
    """관측을 시각순으로. ★되읽는 문★ — 화면의 값 흐름이 이것을 읽는다. ★순수 함수★"""
    rows = [{"ts": str(r.get("ts") or ""), "price": int(r.get("price") or 0)}
            for r in ((attrs or {}).get("history") or [])
            if isinstance(r, dict) and r.get("price")]
    rows.sort(key=lambda r: r["ts"])
    return rows[-MAX_HISTORY:]


def tracked_routes(brain, user_id: str, *, now: str = "") -> list[dict]:
    """지금 보고 있는 노선들 — ★*"내가 요즘 어디 가려 했지?"* 에 답하는 문★"""
    if brain is None:
        return []
    try:
        rows = brain.find_entities(user_id, kind="wish") or []
    except Exception:
        return []
    out = []
    for entity in rows:
        attrs = getattr(entity, "attrs", None)
        attrs = attrs if isinstance(attrs, dict) else {}
        if not attrs.get("destination"):
            continue                 # 항공권 위시만(쇼핑이 남긴 위시와 섞이지 않는다)
        out.append({"route": getattr(entity, "name", ""),
                    "wish_id": getattr(entity, "id", ""),
                    "destination": attrs.get("destination", ""),
                    "depart": attrs.get("depart", ""),
                    "return_on": attrs.get("return_on", ""),
                    "airline": attrs.get("airline", ""),
                    "nonstop": bool(attrs.get("nonstop")),
                    "price": int(attrs.get("price") or 0),
                    "currency": attrs.get("currency", ""),
                    "seen_at": attrs.get("seen_at", ""),
                    "booked_at": attrs.get("booked_at", ""),
                    "dropped_at": attrs.get("dropped_at", ""),
                    "flown": has_flown(attrs.get("depart", ""), now=now)})
    return out


def watchlist(brain, user_id: str, *, now: str = "") -> list[dict]:
    """★배경에서 지켜볼 노선★ — 아직 안 끊었고, 접지 않았고, 안 떠났고, 안 낡은 것.

    되읽는 문이다(원칙 0 ③): 이것이 없으면 `remember_outcome`은 쌓기만 하고
    쓰는 곳이 없어진다 — 이 저장소가 일곱 번 데인 그 실패.
    """
    if brain is None:
        return []
    try:
        rows = brain.find_entities(user_id, kind="wish") or []
    except Exception:
        return []
    out = []
    for entity in rows:
        attrs = getattr(entity, "attrs", None)
        attrs = attrs if isinstance(attrs, dict) else {}
        if not attrs.get("destination") or not int(attrs.get("price") or 0):
            continue
        if not still_wanted(attrs, now=now):
            continue
        out.append({"route": getattr(entity, "name", ""),
                    "wish_id": getattr(entity, "id", ""),
                    "origin": attrs.get("origin", ""),
                    "destination": attrs.get("destination", ""),
                    "depart": attrs.get("depart", ""),
                    # ★조건을 같이 낸다★ 없으면 배경 재점검이 **다른 것**을 보고 온다
                    "trip": Trip(origin=attrs.get("origin", ""),
                                 destination=attrs.get("destination", ""),
                                 depart=attrs.get("depart", ""),
                                 return_on=attrs.get("return_on", ""),
                                 airline=attrs.get("airline", ""),
                                 nonstop=bool(attrs.get("nonstop"))),
                    "price": int(attrs.get("price") or 0),
                    "currency": attrs.get("currency", ""),
                    "last_alert": attrs.get("last_alert", ""),
                    "last_checked": attrs.get("last_checked", "")})
    return out


def remember_outcome(brain, user_id: str, route: str, outcome: str,
                     *, now: str = "") -> str:
    """*"끊었어"* · *"안 가"* 를 남긴다. 손댄 의도 id(없으면 빈 문자열).

    ★묻기만 하고 답을 안 적으면 열 번을 물어도 매번 처음이다★ 그리고 무엇보다
    **끊은 사람에게도 "더 싸졌어요"라고 말하게 된다**.

    ★되돌릴 수 있다★ `outcome=""`면 표시를 지운다 — *"아 아직 안 끊었어"* 라고 다시
    말할 수 있어야 한다. 못 되돌리는 기록은 사람이 말하기를 망설이게 만든다.
    """
    spec = OUTCOMES.get(str(outcome or "").strip().lower())
    if outcome and spec is None:
        return ""
    entity = _wish_of(brain, user_id, route)
    if entity is None:
        return ""
    stamp = now or now_ts()
    marks = {row["attr"]: "" for row in OUTCOMES.values()}   # 둘 다 비우고
    if spec:
        marks[spec["attr"]] = stamp                          # 하나만 채운다
    # ★`provenance="user"`다★ 사람이 말한 것이므로 어떤 자동 파이프라인도 덮지 못한다.
    trust = Trust(confidence=1.0, provenance="user", source_channel=CHANNEL)
    return brain.upsert_entity(user_id, Entity(
        name=entity.name, kind="wish",
        attrs={**trust.to_attrs(), **marks}, valid_from=stamp))


def remember_check(brain, user_id: str, wish_id: str, *,
                   alerted: bool = False, now: str = "") -> None:
    """배경 점검을 **언제 했는지** 적는다 — 안 적으면 매번 다시 검색한다.

    ⚠️ ★알린 시각은 **알렸을 때만**★ 갱신한다. 점검할 때마다 갱신하면 조용히
    기다리는 기간이 영영 안 지나가고, 그러면 두 번째 알림이 나가지 않는다.

    ⚠️ ★적을 것만 넘기면 **나머지가 지워진다**★ (쇼핑에서 실측으로 잡았다 —
    2026-08-19) `update_entity`는 attrs를 병합하지 않고 **통째로 갈아 끼운다**.
    적을 것만 넘겼더니 그 의도가 알던 여덟 칸이 전부 사라지고 `last_checked` 하나만
    남았다 — 값·통화·마지막 알림 시각·`provenance=user`가 거기 있었다.
    그래서 ★우리가 병합해서★ 넘긴다(`upsert_entity`에 맡기지 않는 이유는 고정된
    (`pinned`) 노드에서 그 문이 자동 갱신을 통째로 무시하기 때문이다 — 그러면 점검
    시각이 영영 안 적히고 배경 검색이 대화마다 돈다).
    """
    stamp = now or now_ts()
    fresh = {"last_checked": stamp}
    if alerted:
        fresh["last_alert"] = stamp
    try:
        node = brain.get_entity(user_id, wish_id)
        if node is None:
            return                         # 사용자가 지웠다 — 되살리지 않는다
        brain.update_entity(user_id, wish_id,
                            attrs={**(node.attrs or {}), **fresh})
    except Exception:
        pass                               # 못 적으면 다음번에 다시 본다


# ── 화면 상태 ────────────────────────────────────────────────────────────────
#
# 화면이 읽을 것을 두는 자리. ★코드가 아니라 **상태**의 자리다★ — `data_dir`가
# 그 둘을 갈라 두므로 에이전트를 업데이트해도 보던 목록이 지워지지 않는다.

def _save(ctx: ToolContext, state: dict) -> None:
    (ctx.data_dir("flights") / _STATE_FILE).write_text(
        json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _load(ctx: ToolContext) -> dict:
    """읽지 못하면 **빈 상태**다 — 화면은 빈 것도 그릴 수 있어야 한다(M-H20)."""
    try:
        path = ctx.data_dir("flights") / _STATE_FILE
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _only_json(text: str) -> str:
    """모델이 앞뒤로 말을 붙여도 배열만 꺼낸다."""
    body = str(text or "").strip()
    start, end = body.find("["), body.rfind("]")
    return body[start:end + 1] if 0 <= start < end else "[]"


# ── 에이전트 ─────────────────────────────────────────────────────────────────

class FlightsPlugin(Plugin):
    name = "flights"
    title = "Flight finder"
    summary = ("Remembers where you were trying to fly and what it cost, then tells "
               "you when that fare drops. Compares the options on one screen with "
               "stops and travel time spelled out.")
    category = "shopping"

    # ★왜 사용자가 이것을 들였나★(Phase AG) — `summary`가 *"무엇을 하는가"* 라면
    # 이 칸은 *"이 사람이 왜 이걸 갖고 있는가"* 다. 그것이 **무엇을 남길지**의
    # 기준이 된다(원칙 0 ①).
    #
    # ★그래서 남기는 것과 안 남기는 것이 여기서 갈린다★ 어디에 언제 가려 하는가는
    # 나중에도 참이다(남긴다). 그때의 값은 **관측**으로만 참이다(시각과 함께
    # 남긴다). 어느 항공사를 골랐나는 그 결정에 딸린 것이지 지속되는 취향이
    # 아니다(안 남긴다 — 쇼핑이 `Sean likes Price`로 그래프를 더럽힌 그 자리다).
    purpose = (
        "The user installed this because when they fly is decided by price, and "
        "price moves for weeks before anyone books. None of that watching survives "
        "on its own -- they look on Monday, lose the number by Friday, and start "
        "over. So it keeps where they are trying to go, when they meant to leave, "
        "and what the fare was each time it looked, so the second search can say "
        "'that one dropped' -- and say it without being asked."
    )

    # ★원하는 사람만 들인다★ — ① 늘 필요하지는 않다 · ③ 돈이 걸린다
    optional = True

    # ★값이 내리면 **먼저** 말한다★ 화면을 열어야 보이는 것은 절반만 만든 것이다 —
    # 표가 싸진 사실은 때를 놓치면 값이 없다(특가는 끝난다).
    # 사용자가 이 훅을 끄면 `hooks.enabled()`가 먼저 걸러 `advise()`가 안 불린다.
    raises_notices = True

    # ★말로 이렇게 시킨다★ — 사용자가 이 카드에서 읽는 사용법이다.
    # ★카드의 사용법과 화면의 단추가 **같은 낱말**이다★ 다르면 사용자는 둘 중
    # 하나만 쓰게 되고, 번역도 두 벌이 된다.
    howto = (
        # ★날짜를 말하도록 가르친다★ 같은 노선도 다른 날은 다른 것이라, 날짜 없이
        # 물으면 이 에이전트가 지켜보는 것은 *"언젠가 도쿄"* 가 된다.
        # ⚠️ 예문에 **못 박힌 날짜**를 쓰지 않는다 — 카드에 2026년이 박혀 있으면
        # 2027년 사용자에게 그 카드는 낡은 것으로 읽힌다.
        "Find flights to Tokyo leaving on the 10th",
        "Korean Air to Tokyo, nonstop, back on the 14th",
        "Did that route get cheaper?",
        "Show the next ones",
        "I booked it",
    )
    version = "0.4.0"
    author = "cosmos"
    # ★모델이 이 글을 읽고 **자기를 부를지 말지** 정한다★ (2026-08-23 실사용에서 데였다)
    #
    # 첫 판은 *"항공편을 찾고 지난번과 비교하며 기억한다"* 로 시작했다. 그래서 Sean이
    # *"비행기 티켓 **값** 좀 알아봐"* 라고 했을 때 모델은 ★이것을 안 골랐다★ —
    # `web_search`가 자기 설명에 *"the moment something comes up … **prices**"* 라고
    # 적어 두었기 때문이다. 웹 검색이 **여섯 번** 헛돌았고, 사용자는 결국
    # *"에이전트 활용해서 알아봐 줘"* 라고 **직접 지목해야** 했다.
    #
    # ★도구가 있는 것과 모델이 그것을 고르는 것은 다른 일이다.★ 그래서 첫 문장이
    # **언제 부르는가**를 말한다 — 기억과 비교는 그다음이다.
    description = (
        "USE THIS for anything about flights, airfares or plane tickets -- 'how much "
        "is a ticket to New York', 'find me a flight on the 14th', 'did that route "
        "get cheaper'. Do not use a web search for fares: a search returns the "
        "landing-page headline price for some unknown date, with no flight numbers "
        "and no times, while this opens the actual flight listing.\n"
        "It compares what it finds with what the user saw last time, remembers the "
        "routes and dates they are interested in, checks nearby dates for a cheaper "
        "one, and tells them in the background when a fare they were watching drops.")
    parameters = {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING",
                       "description": " | ".join(f"{k} — {v['desc']}"
                                                 for k, v in ACTIONS.items())},
            "origin": {"type": "STRING", "description": "Where from — city or airport code."},
            "destination": {"type": "STRING", "description": "Where to — city or airport code."},
            "depart": {"type": "STRING",
                       "description": "Departure date (YYYY-MM-DD) if known. The same "
                                      "route on another date is a different trip, so "
                                      "pass what the user actually said."},
            "return_on": {"type": "STRING",
                          "description": "Return date (YYYY-MM-DD). Pass it whenever "
                                         "the user wants a round trip -- a return "
                                         "changes the fare, so it is a different trip "
                                         "from the one-way."},
            "airline": {"type": "STRING",
                        "description": "Only this airline, when the user named one "
                                       "(\'Korean Air\', \'Peach\'). Leave empty to "
                                       "compare all of them."},
            "nonstop": {"type": "BOOLEAN",
                        "description": "True when the user said direct or nonstop only."},
        },
        "required": [],
    }
    # ★브라우저를 쓴다고 **적는다**★ (2026-08-21) 목록 페이지를 직접 열기로 하면서
    # 필요한 것이 늘었다. 설치 화면은 이 줄을 그대로 읽어 사용자에게 보인다 —
    # 안 적고 쓰면 ★사용자가 승인한 것과 실제로 하는 일이 갈린다★(코어가 거부한다).
    #
    # `browser.act`는 ★날짜 표 하나 때문★이다: 그 표는 주소로 안 열리고 눌러야 한다.
    # 없어도 항공편 검색은 그대로 돌고, 더 싼 날 비교만 빠진다.
    capabilities = ["network", "memory", "browser", "browser.act"]
    requires_desktop = False
    view_title = "Flights"

    # ★사용자가 아는 돈으로 보인다★ (Sean 16항목 ③ — 설정이 필요한 것은 설정된다)
    #
    # 값은 **언어가 아니라 값**이다(CLAUDE.md의 그 경계) — 화면 글은 번역되지만
    # 78만원과 $560은 번역이 아니라 다른 사실이다. 비워 두면 페이지가 사용자 지역의
    # 통화로 보여 주므로, ★기본값은 "정하지 않음"이 맞다★.
    settings = (
        {"id": "currency", "kind": "choice", "label": "Currency",
         "options": ["", "KRW", "USD", "JPY", "EUR", "GBP", "CNY"],
         "default": "",
         "hint": "Leave empty to use whatever the flight listing shows for you."},
    )
    # ★이 화면의 성격★(Sean 요구 2026-08-19) 넷을 나란히 놓고 **값으로** 고르는
    # 화면이다. 눈이 카드 사이를 오가야 하므로 넉넉해야 한다.
    character = {"glyph": "route", "density": "airy"}

    brain = {
        # ★어디에 언제 가려 하는가는 나중에도 참이다★ 가격은 **관측**(시각과 함께)
        # 으로 남기므로 거짓이 되지 않는다.
        "stores": ("wish", "place"),
        # ★이것이 두 번째 검색을 값어치 있게 만든다★(원칙 0 ③)
        "reads": ("wish", "place"),
        # ★안 남기기로 한 것도 적는다★ — 뭉개면 고쳐야 할 것이 "검토됨"으로 묻힌다.
        "settled": "Which airline or seat the person picked while comparing one trip "
                   "is never stored as a lasting preference of theirs -- it is a "
                   "judgement about that trip, not a taste, and storing it is how "
                   "'Sean likes Price' got into the graph on the shopping side. "
                   "Booking references, seat numbers and passenger names are never "
                   "stored at all: the brain is searched and put into prompts, and "
                   "nothing that identifies a traveller belongs there.",
    }

    # ★사람이 **말한 것**만 여기 들어온다★ 우리가 발권하지 않으므로 "끊었다"는
    # 추측할 수 없다. 이 표가 없으면 *"끊었나요?"* 를 물어 놓고 답을 버리게 된다.
    _OUTCOME_ACTIONS = tuple(OUTCOMES) + ("still_looking",)

    # ★쪽 넘김은 **말로도 손으로도** 같은 문을 쓴다★ 버튼만 만들면 말로는 못 넘기고,
    # 말만 만들면 손으로는 못 넘긴다.
    _PAGE_ACTIONS = ("next", "prev")

    def __init__(self) -> None:
        super().__init__()
        # 지금 떠 있는 알림들 — ★내리는 것이 알림의 절반이다★
        self._raised: set[str] = set()

    # -- 라우팅 ---------------------------------------------------------------
    def run(self, ctx: ToolContext, **args) -> str:
        action = str(args.get("action") or "").strip().lower()
        if action not in ACTIONS:
            action = DEFAULT_ACTION
        try:
            if action == "plans":
                return self._plans(ctx)
            if action in self._PAGE_ACTIONS:
                return self._turn_page(ctx, action)
            if action in self._OUTCOME_ACTIONS:
                return self._settle(ctx, action, args)
            if action == "forget":
                return self._forget(ctx, args)
            return self._search(ctx, args)
        except Exception as e:
            return i18n.t("The flight search did not work: {detail}", detail=e)

    # -- 검색 -----------------------------------------------------------------
    def _search(self, ctx: ToolContext, args: dict) -> str:
        trip = trip_of(args)
        if not trip.destination:
            return i18n.t("Tell me where you want to fly to.")
        route = route_name_of(trip)
        ctx.write_log(f"[flights] {route}")

        brain = getattr(ctx, "brain", None)
        uid = str(getattr(ctx, "user_id", "") or "local")
        past = recall_route(brain, uid, trip=trip)
        found, dropped = self._find(ctx, trip)
        found = rank(found)
        if not found:
            return self._nothing(route, trip, dropped)
        if brain is not None:
            self._remember(ctx, trip, found)
        diff = compare_with_past(past, found)
        # ★날짜를 바꿔 본다★ — 사람이 표를 살 때 하는 그 일(Sean 요구 2026-08-21).
        # 못 하면 빈 목록이고, 그래도 검색은 그대로 산다.
        nearby = self._other_days(ctx, trip, found)
        # ★화면과 말이 **같은 판정**을 본다★ 두 곳에서 판정하면 서로 다른 것을 말한다.
        self._remember_view(ctx, route, found, past, diff, trip, nearby)
        return self._say(route, found, diff, nearby)

    def _other_days(self, ctx: ToolContext, trip: Trip,
                    found: list[Flight]) -> list[dict]:
        """앞뒤 며칠 중 **더 싼 날**. 못 열면 빈 목록(검색은 그대로 산다).

        ⚠️ ★날짜를 모르면 비교할 것도 없다★ *"도쿄 가는 표"* 처럼 날짜 없이 물으면
        표를 열어도 무엇 대비 싼지 말할 수 없다.
        """
        best = cheapest(found)
        if not trip.depart or best is None or not best.price:
            return []
        page = ctx.read_page(flights_url(trip, currency=self._currency(ctx)),
                             click=DATE_GRID_BUTTON, targets=GRID_TARGETS,
                             settle=GRID_SETTLE_SEC)
        if not page.get("ok"):
            ctx.write_log(f"[flights] no date grid: {page.get('why') or 'unknown'}")
            return []
        if page.get("why"):
            # 읽히긴 했는데 표를 못 열었다 — 열렸을 때와 구별해 남긴다
            ctx.write_log(f"[flights] date grid: {page['why']}")
        grid = read_date_grid(page.get("targets") or (), around=trip.depart)
        cheaper = cheaper_days(grid, than=best.price, on=trip.depart,
                               back=trip.return_on)
        # ★읽은 칸 수를 남긴다★ *"더 싼 날 없음"* 은 두 가지 뜻이다 — 표를 읽었는데
        # 정말 없는 것과, ★표를 한 칸도 못 읽은 것★. 세지 않으면 후자가 전자로 보이고
        # 그러면 기능이 통째로 죽어 있어도 정상으로 읽힌다(이 저장소가 여러 번 데인 자리).
        ctx.write_log(f"[flights] date grid: read {len(grid)} cells, "
                      f"{len(cheaper)} cheaper than {best.price}")
        return cheaper[:MAX_NEARBY_DAYS]

    def _nothing(self, route: str, trip: Trip, dropped: int) -> str:
        """★못 찾았으면 **왜** 못 찾았는지까지 말한다★ (Sean 요구 2026-08-19)

        조건을 받기 시작하면 빈손이 나오는 길이 하나 더 생긴다 — 표는 있는데 **그
        조건에 맞는 것이** 없는 경우다. 그냥 *"못 찾았어요"* 라고 하면 사용자는
        노선이나 날짜를 의심하고, 정작 풀 수 있는 조건은 손대지 않는다.
        """
        if dropped and (trip.airline or trip.nonstop):
            if trip.airline and trip.nonstop:
                return i18n.t("I found {count} flights, but none of them are nonstop "
                              "on {airline}. Shall I drop one of those?",
                              count=dropped, airline=_place(trip.airline))
            if trip.airline:
                return i18n.t("I found {count} flights, but none on {airline}.",
                              count=dropped, airline=_place(trip.airline))
            return i18n.t("I found {count} flights, but none of them are nonstop.",
                          count=dropped)
        return i18n.t("I could not find flights for {route}. Try naming the "
                      "airports, or a different date.", route=route)

    def _find(self, ctx: ToolContext, trip: Trip) -> tuple[list[Flight], int]:
        """항공편 목록 페이지를 **열어** 정규형으로 옮기고 **조건으로 거른다**.

        돌려주는 것은 (남은 것, ★조건 때문에 버린 수★)이다 — 버린 수를 안 세면
        *"표는 있는데 그 항공사가 없다"* 와 *"아무것도 못 찾았다"* 를 구별해서
        말할 수 없고, 그러면 사용자는 풀 수 있는 조건을 손대지 않는다.

        실패는 빈 목록이다(거짓말하지 않는다).
        """
        page = ctx.read_page(flights_url(trip, currency=self._currency(ctx)))
        if not page.get("ok"):
            # ★왜 못 봤는지를 로그에 남긴다★ 빈손만 남기면 다음 사람은 *"항공편이
            # 없었나 보다"* 로 읽는다 — 브라우저가 안 뜬 것과 결과가 없는 것은 다르다.
            ctx.write_log(f"[flights] could not open the listing: "
                          f"{page.get('why') or 'unknown'}")
            return [], 0
        try:
            moved = ctx.think(f"{_EXTRACT}\n\nFlight results page:\n"
                              f"{str(page.get('text') or '')[:6000]}")
        except Exception as e:
            ctx.write_log(f"[flights] could not read the page: {e}")
            return [], 0
        flights = to_flights(_only_json(moved))
        # ★모델이 엉뚱한 노선을 섞어 오면 버린다★ 우리가 물은 곳으로 가는 것만 남긴다.
        #
        # ⚠️ ★공항 코드로 오는 것이 정상이 되었다★(2026-08-21) 목록 페이지는 목적지를
        # `NRT`·`HND`로 적지 *"Tokyo"* 라고 적지 않는다. 이름으로만 맞추면 **전부
        # 버리고** 빈손이 된다 — 그래서 이름이 안 맞으면 통째로 살린다(아래 `or`).
        wanted = _place(trip.destination).lower()
        on_route = [f for f in flights if wanted in f.destination.lower()] or flights
        # ★조건은 **우리가** 건다★ 주소에 넣는 것만으로는 안 걸린다 — 페이지는 비슷한
        # 것을 넉넉히 보여 주고, 모델은 그것을 옮기기만 한다(판정은 우리 코드다).
        kept = [f for f in on_route if matches_trip(f, trip)]
        return kept, len(on_route) - len(kept)

    @staticmethod
    def _currency(ctx: ToolContext) -> str:
        """사용자가 고른 통화. ★설정이 비면 페이지가 알아서 정한다★(빈 문자열).

        여기서 아무 값이나 기본으로 박으면 ★그 통화 사용자에게는 영영 남의 돈으로
        보인다★ — 모르면 비워 두는 편이 낫다. 그때 목록은 그 사람의 지역 통화로 뜬다.
        """
        try:
            from cosmos.core import agent_settings
            got = agent_settings.get("flights", "currency", "")
        except Exception:
            return ""
        return str(got or "").strip().upper()

    # -- 계획 -----------------------------------------------------------------
    def _plans(self, ctx: ToolContext) -> str:
        routes = tracked_routes(getattr(ctx, "brain", None),
                                str(getattr(ctx, "user_id", "") or "local"))
        # ★떠난 것·끊은 것·접은 것은 "보고 있는" 것이 아니다★ 그것까지 읽어 주면
        # 목록이 길어지기만 하고, 사용자가 정말 묻는 것("지금 뭘 고민 중이지")에서 멀어진다
        open_routes = [r for r in routes
                       if not r["flown"] and not r["booked_at"] and not r["dropped_at"]]
        if not open_routes:
            return i18n.t("You have not looked at any flights with me yet.")
        rows = "\n".join(
            "- " + r["route"]
            + (" (" + i18n.t("last seen at {price}",
                             price=money(r["price"], r["currency"])) + ")"
               if r["price"] else "")
            for r in open_routes)
        return i18n.t("Routes you have been watching:") + "\n" + rows

    def _forget(self, ctx: ToolContext, args: dict) -> str:
        """★사용자의 결정이 이긴다★ 그만 보겠다고 하면 그 노선을 철회한다."""
        brain = getattr(ctx, "brain", None)
        uid = str(getattr(ctx, "user_id", "") or "local")
        route = route_name(str(args.get("origin") or ""),
                           str(args.get("destination") or ""),
                           str(args.get("depart") or ""))
        if brain is None or not route:
            return i18n.t("Tell me which route to stop tracking.")
        gone = 0
        for entity in brain.find_entities(uid, kind="wish") or []:
            if str(getattr(entity, "name", "")).lower() == route.lower():
                gone += brain.delete_entity(uid, getattr(entity, "id", ""))
        ctx.write_log(f"[flights] forget {route}")
        # ★지켜보기를 그만두면 그 알림도 지금 내린다★ 안 내리면 사용자는 방금 지운
        # 것에 대한 말을 계속 듣고, 그때 "그만두기"는 동작하지 않는 것으로 읽힌다.
        self._clear(ctx, self._notice_key(route))
        return (i18n.t("I will stop tracking {route}.", route=route) if gone
                else i18n.t("I was not tracking {route}.", route=route))

    # -- ★"끊었어" · "안 가" 를 적는다★ ---------------------------------------
    def _settle(self, ctx: ToolContext, action: str, args: dict) -> str:
        """*"끊었나요?"* 의 답을 남긴다.

        ★안 적으면 열 번을 물어도 매번 처음이다★ 그리고 무엇보다 **끊은 사람에게도
        "더 싸졌어요"라고 말하게 된다** — 도움이 아니라 상처다.
        """
        brain = getattr(ctx, "brain", None)
        uid = str(getattr(ctx, "user_id", "") or "local")
        # ★말할 때는 노선을 다시 안 댄다★ *"응 끊었어"* 라고만 하므로, 방금 보던
        # 것이 무엇인지는 화면 상태가 안다(사람에게 다시 대라고 하면 안 쓴다).
        route = route_name(str(args.get("origin") or ""),
                           str(args.get("destination") or ""),
                           str(args.get("depart") or "")) or _load(ctx).get("route", "")
        if brain is None or not route:
            return i18n.t("Which trip do you mean?")
        outcome = "" if action == "still_looking" else action
        if not remember_outcome(brain, uid, route, outcome):
            return i18n.t("I am not tracking {route}.", route=route)
        # 끊었거나 접었으면 그 노선의 알림은 지금 내려간다
        if outcome:
            self._clear(ctx, self._notice_key(route))
        if action == "booked":
            return i18n.t("Got it — you booked {route}. I will stop watching the "
                          "fare.", route=route)
        if action == "dropped":
            return i18n.t("Got it — I will stop bringing up {route}.", route=route)
        return i18n.t("Got it — {route} is still open. I will keep an eye on the "
                      "fare.", route=route)

    # -- 쪽 넘김 ---------------------------------------------------------------
    def _turn_page(self, ctx: ToolContext, action: str) -> str:
        state = _load(ctx)
        items = state.get("items") or []
        if not items:
            return i18n.t("There is nothing on the screen to page through yet.")
        _, page, pages = page_of(items, state.get("page"))
        wanted = page + (1 if action == "next" else -1)
        if wanted < 0:
            return i18n.t("That is already the first page.")
        if wanted >= pages:
            return i18n.t("That is the last page.")
        shown, page, pages = page_of(items, wanted)
        state["page"] = page
        _save(ctx, state)
        first = page * PAGE_SIZE + 1
        return i18n.t("Numbers {first} to {last} of {total}, page {page} of {pages}.",
                      first=first, last=first + len(shown) - 1, total=len(items),
                      page=page + 1, pages=pages)

    # -- ★값이 내리면 먼저 말한다★ -------------------------------------------
    def advise(self, ctx: ToolContext) -> None:
        """배경에서 지켜보다 **싸졌을 때** 알린다 — 그리고 해소되면 스스로 내린다.

        ## ⚠️ 한 번에 **하나만** 본다

        `advise()`는 말이 오갈 때마다 불린다. 여기서 지켜보는 것을 전부 다시
        검색하면 대화 한 번에 웹 검색이 지켜보는 수만큼 나간다. 그래서 **점검할
        때가 된 것 하나**만 고르고, 나머지는 다음 차례에 본다.

        ## 알림은 **상태**다

        같은 키로 다시 부르면 덮어쓴다. 사람이 *"끊었어"* 라고 하거나 **출발일이
        지나면** 그 노선은 `watchlist`에서 빠지고, 그 순간 이 함수가 알림을
        내린다. 내려가지 않는 알림은 두 번째부터 무시당한다.
        """
        brain = getattr(ctx, "brain", None)
        if brain is None or not callable(getattr(ctx, "notice", None)):
            return
        uid = str(getattr(ctx, "user_id", "") or "local")
        try:
            watching = watchlist(brain, uid)
        except Exception:
            return

        # ★해소되면 스스로 내려간다★ 지켜볼 것에서 빠진 노선의 알림은 여기서 사라진다.
        open_keys = {self._notice_key(row["route"]) for row in watching}
        for key in list(self._raised - open_keys):
            self._clear(ctx, key)

        row = next((r for r in watching if due_for_recheck(r["last_checked"])), None)
        if row is None:
            return
        self._check_one(ctx, row)

    def _check_one(self, ctx: ToolContext, row: dict) -> None:
        """지켜보던 노선 하나를 다시 보고, 말할 만하면 알린다.

        ★사용자가 말한 조건 그대로 다시 본다★(Sean 요구 2026-08-19) 왕복으로 보던
        것을 편도로 다시 보거나 대한항공만 보던 것을 아무 항공사로 다시 보면, 그
        값으로 *"내렸어요"* 라고 말하는 것은 **거짓말**이다.
        """
        brain = ctx.brain
        uid = str(getattr(ctx, "user_id", "") or "local")
        trip = row.get("trip") or Trip(origin=row["origin"],
                                       destination=row["destination"],
                                       depart=row["depart"])
        try:
            fresh = rank(self._find(ctx, trip)[0])
        except Exception:
            return
        best = cheapest(fresh)
        if best is None:
            remember_check(brain, uid, row["wish_id"])
            return
        # ★통화가 바뀌면 값을 견주지 않는다★ 89만 KRW와 690 USD를 빼면 그 숫자는
        # 아무 뜻이 없고, 그 숫자로 "내렸다"고 말하면 그것은 거짓말이다.
        if row["currency"] and best.currency and row["currency"] != best.currency:
            remember_check(brain, uid, row["wish_id"])
            return

        verdict = worth_interrupting(row["price"], best.price,
                                     currency=best.currency or row["currency"],
                                     last_alert=row["last_alert"])
        if not verdict["tell"]:
            remember_check(brain, uid, row["wish_id"])
            return

        # ★새 값을 기억에 남긴다★ 안 남기면 다음번에 **같은 인하를 또** 알린다
        try:
            remember_search(brain, uid, trip.origin, trip.destination, fresh,
                            trip=trip, agent=self)
        except Exception:
            pass
        ctx.notice(
            self._notice_key(row["route"]),
            # ★말로 나가는 줄이다★ 읽는 글이 아니라 **하는 말**로 쓴다
            i18n.t("{route} is {amount} cheaper than when you looked.",
                   route=row["route"],
                   amount=money(abs(verdict["delta"]),
                                best.currency or row["currency"])),
            level="warn",
            detail=i18n.t("Now {price} with {airline}, {stops}.",
                          price=money(best.price, best.currency),
                          airline=best.airline or i18n.t("the airline"),
                          stops=stops_text(best.stops)),
            # ★단추도 **같은 조건**을 들고 간다★ 조건을 빼고 다시 열면 사용자는
            # 방금 들은 것과 다른 목록을 보게 되고, 그 순간 알림이 거짓이 된다.
            action={"label": i18n.t("Show me"), "tool": self.name,
                    "args": {"origin": trip.origin,
                             "destination": trip.destination,
                             "depart": trip.depart, "return_on": trip.return_on,
                             "airline": trip.airline, "nonstop": trip.nonstop}})
        self._raised.add(self._notice_key(row["route"]))
        remember_check(brain, uid, row["wish_id"], alerted=True)

    @staticmethod
    def _notice_key(route: str) -> str:
        """★노선마다 하나★ 항공편마다 키를 만들면 한 여행으로 알림이 넷 뜬다."""
        return "fare:" + str(route or "")[:80]

    def _clear(self, ctx: ToolContext, key: str) -> None:
        try:
            ctx.clear_notice(key)
        except Exception:
            pass
        self._raised.discard(key)

    # -- 화면 -----------------------------------------------------------------
    def view(self, ctx: ToolContext, **params) -> dict:
        """★비교는 여기서 한다★ 말로는 둘까지, 나머지는 이 화면이 보여준다.

        ★우리 어휘로 그린다★ 나란히 비교(`compare`)와 값 흐름(`price_history`)은
        화면 계약에 **이미 있고** 셸도 그릴 줄 안다. 액자(`iframe`)에 넣으면 디자인
        토큰이 안 닿고, 계측기가 못 찍고, 쪽 넘김이 어려워진다(쇼핑에서 셋 다 겪었다).
        """
        state = _load(ctx)
        if not state:
            return {"title": self.view_title,
                    "blocks": [{"type": "text", "tone": "muted",
                                "text": i18n.t(
                                    "Where do you want to fly? Ask me out loud and "
                                    "I will compare the options here.")}]}

        blocks: list[dict] = []
        # ★지난번 이야기가 **맨 위에** 온다★ 이것이 이 에이전트의 값어치다
        for line in _headlines(state.get("diff") or {}):
            blocks.append({"type": "text", "tone": line["tone"], "text": line["text"]})

        items = state.get("items") or []
        shown, page, pages = page_of(items, state.get("page"))
        # ★번호는 **전체에서 몇 번째**다★ 쪽마다 1번부터 세면 3쪽의 1번을 열었을 때
        # 1쪽의 1번이 열린다 — 가리키는 것이 미끄러지는 사고다.
        base = page * PAGE_SIZE
        blocks.append({"type": "group", "icon": "✈",
                       # ★기억의 **열쇠**를 화면에 그대로 쓰지 않는다★ (2026-08-19 ·
                       # 한국어로 찍어 보고 알았다) 노선 이름(`Flights ICN to Tokyo
                       # on 2026-09-10`)은 브레인에서 같은 노선을 하나로 모으는 열쇠라
                       # ★어느 언어에서도 같아야 한다★ — 옮기면 언어를 바꿀 때마다
                       # 같은 노선이 새로 생긴다. 그래서 옮기는 대신 **표시용 줄을
                       # 따로 만든다**: 화살표와 날짜는 어느 언어에서도 읽힌다.
                       "label": self._route_label(state),
                       # 몇 쪽 중 몇 쪽인지 — 없으면 사용자는 이게 전부라고 읽는다
                       "action": {"label": f"{page + 1} / {pages}"} if pages > 1 else None})

        # ★"가장 싸다"는 **전체에서** 정한다★ 화면이 받은 넷에서 고르면 다음 쪽에 더
        # 싼 것이 있을 때 그 글자가 거짓말이 된다(쇼핑에서 2쪽을 찍어 보고 알았다).
        # ★그리고 미는 것은 첫 쪽에서만★ 2쪽에서도 1위를 표시하면 **화면에 없는 것을
        # 가리키는 하이라이트**가 되고, 사용자는 거기서 멈춘다.
        low = cheapest_index(items)
        # ★모두 같은 날이면 카드마다 날짜를 되풀이하지 않는다★ (찍어 보고 알았다)
        # 위 제목이 이미 그 날을 말하는데 카드 넷이 같은 날짜를 또 적고 있었고,
        # 그 한 조각이 이유 문장을 밀어내 카드 밖으로 잘랐다.
        days = {_date(i.get("depart", "")) for i in items}
        cards = [self._card(item, base + n, lead=(base + n == 0),
                            low=(base + n == low), with_day=len(days) > 1)
                 for n, item in enumerate(shown)]
        blocks.append({"type": "compare",
                       # ★아무도 모르는 신호는 칸을 안 만든다★
                       #
                       # ⚠️ ★**카드**를 보고 정한다★ (2026-08-19 · 찍어 보고 알았다)
                       # 화면 상태의 줄에는 `signals` 칸이 아예 없다 — 그것은
                       # `_card()`가 만든다. 상태를 넘겼더니 빈 목록이 나왔고,
                       # 계약은 빈 목록을 *"아무것도 안 골랐다"* 로 읽어 **표 전체로
                       # 되돌린다**. 그래서 화면에 쇼핑 신호 여섯 줄이 카드마다
                       # `Unknown`으로 그려졌다(그물은 그것도 통과시켰다 — 폴백된
                       # 여덟도 "계약의 어휘 안"이기는 하니까).
                       "signals": signals_worth_showing(cards),
                       "items": cards})

        # ★날짜를 바꾸면 얼마인가★ (Sean 요구 2026-08-21) 값 흐름이 *"이 날이
        # 싸지고 있나"* 라면, 이것은 *"다른 날로 가면 싼가"* 다. 사람이 표를 살 때
        # 하는 두 가지가 이 둘이고, 여태 우리는 앞의 하나만 하고 있었다.
        for line in self._nearby_lines(state):
            blocks.append(line)

        if history := (state.get("history") or []):
            blocks.append({"type": "price_history", "items": history,
                           "label": i18n.t("Fare trend")})

        if buttons := self._nav(items, page, pages):
            blocks.append({"type": "actions", "items": buttons})

        if notice := state.get("notice"):
            blocks.append({"type": "text", "tone": "info", "text": str(notice)})
        return {"title": self.view_title, "blocks": blocks,
                "params": {"route": state.get("route", ""), "page": page}}

    def _nearby_lines(self, state: dict) -> list[dict]:
        """*"하루 늦추면 얼마"* 를 화면 줄로. 없으면 빈 목록(빈 상자를 그리지 않는다).

        ★단추를 단다★ 더 싼 날을 보여 주고 **그 날로 다시 찾아 주지 않으면**,
        사용자는 날짜를 손으로 다시 불러야 한다 — 그러면 우리가 알아낸 것이
        그 사람의 일거리가 된다(원칙 ③: 어려우면 만들다 만 것이다).
        """
        rows = [row for row in (state.get("nearby") or []) if isinstance(row, dict)]
        if not rows:
            return []
        out: list[dict] = [{"type": "text", "tone": "info",
                            "text": i18n.t("Cheaper on other days")}]
        buttons = []
        for row in rows[:MAX_NEARBY_DAYS]:
            date, back = str(row.get("date") or ""), str(row.get("back") or "")
            if not date:
                continue
            # ★돌아오는 날도 함께 적는다★ 안 적으면 *"$136이 더 싸다"* 가 실제로는
            # **다른 길이의 여행**일 수 있다(당일치기가 그렇게 섞여 들어왔다).
            when = f"{date} ⇄ {back}" if back else date
            buttons.append({
                "label": f"{when} · {money(row.get('price'), row.get('currency', ''))}",
                "tool": self.name,
                "args": {"action": "search",
                         "origin": _place(str(state.get("origin") or "")),
                         "destination": self._destination_of(state),
                         "depart": date, "return_on": back,
                         "airline": str(state.get("airline") or ""),
                         "nonstop": bool(state.get("nonstop"))}})
        if buttons:
            out.append({"type": "actions", "items": buttons})
        return out

    @staticmethod
    def _destination_of(state: dict) -> str:
        """화면 상태에서 목적지를 되찾는다 — 단추가 그것 없이는 다시 못 찾는다."""
        first = next((i for i in (state.get("items") or []) if isinstance(i, dict)), {})
        return _place(str(first.get("destination") or ""))

    @staticmethod
    def _route_label(state: dict) -> str:
        """화면 머리에 쓸 **표시용** 노선 줄. 기억의 열쇠(`route`)와 일부러 다르다.

        어디서 어디로 가는지는 후보들이 이미 알고 있다 — 그중 하나에서 읽는다.
        모르면 열쇠를 그대로 쓴다(빈 줄보다는 영어 한 줄이 낫다).

        ★조건도 여기 보인다★(Sean 요구 2026-08-19) *"대한항공 직항만"* 으로 본
        목록인지 아닌지가 안 보이면, 사용자는 값이 왜 이렇게 비싼지 모른 채
        **우리가 잘못 찾았다고 읽는다**. 걸린 조건은 화면이 말해야 한다.
        """
        first = next((i for i in (state.get("items") or []) if isinstance(i, dict)), {})
        start, end = _place(first.get("origin", "")), _place(first.get("destination", ""))
        day, back = _date(state.get("depart", "")), _date(state.get("return_on", ""))
        if not end:
            return str(state.get("route", ""))
        # ★왕복은 화살표가 양쪽이다★ 글자로 "왕복"이라 쓰는 것보다 빠르게 읽힌다
        where = (f"{start} ⇄ {end}" if back else f"{start} → {end}") if start else end
        parts = [where]
        if day:
            parts.append(f"{day} ⇄ {back}" if back else day)
        if airline := _place(str(state.get("airline") or "")):
            parts.append(airline)
        if state.get("nonstop"):
            parts.append(i18n.t("Nonstop"))
        return " · ".join(parts)

    def _card(self, item: dict, position: int, *, lead: bool = False,
              low: bool = False, with_day: bool = True) -> dict:
        """항공편 하나를 비교 카드로. `position`은 **0부터 세는 전체 순번**이다.

        ★배지는 하나만 단다★ 미는 것이 마침 가장 싸기도 하면 *"추천"* 이 이긴다 —
        둘을 나란히 붙이면 배지가 정보가 아니라 장식이 된다.
        """
        # ★날짜는 **갈릴 때만** 말한다★ 같은 노선도 다른 날은 다른 것이지만, 한 날로
        # 찾은 결과라면 위 제목이 이미 그 날을 말한다(찍어 보고 알았다 — 카드 넷이
        # 같은 날짜를 되풀이하며 이유 문장을 카드 밖으로 밀어냈다).
        depart = _date(item.get("depart", "")) if with_day else ""
        note = item.get("note", "") or ""
        # ★미는 카드는 **왜 미는지**를 먼저 말한다★
        reason = str(item.get("reason") or "") if lead else ""
        # ★값이 무엇을 덮는지 **먼저** 말한다★ 왕복으로 찾았는데 편도 값이 떠 있으면
        # 사용자는 예산을 절반으로 잘못 잡는다 — 돈에 관한 것은 앞에 온다.
        covers = fare_type_text(str(item.get("fare_type") or ""))
        line = " · ".join(x for x in (covers, reason, depart, note) if x)
        return {"title": item.get("airline", "") or i18n.t("the airline"),
                # ★어디에서 어디로★ 판매처 자리에 노선을 쓴다 — 물건을 견줄 때
                # 판매처가 하는 일을, 표를 견줄 때는 노선이 한다
                "seller": " → ".join(x for x in (item.get("origin", ""),
                                                 item.get("destination", "")) if x),
                "price": item.get("price"), "currency": item.get("currency"),
                "seen_at": item.get("seen_at", ""), "note": line,
                "mark": i18n.t("Best pick") if lead else (i18n.t("Cheapest") if low else ""),
                "lead": lead,
                # ★값이 아니라 **글**로 보낸다★ 분(minutes)을 그대로 실으면 화면에
                # "515"가 뜨고, 그 숫자를 읽을 수 있는 사람은 없다.
                "signals": {"stops": stops_text(item.get("stops")),
                            "duration": duration_text(item.get("minutes")),
                            # ★비면 그 칸은 아예 안 그려진다★(`signals_worth_showing`)
                            # — 모르는 것을 "모름"으로 채우면 여섯 칸이 다 진해진다
                            "when": when_text(item.get("leaves"),
                                              item.get("arrives"))},
                # ★단추는 **번호만** 보낸다★ 주소를 실어 보내면 오염된 화면이 자기
                # 주소를 열 수 있다.
                "action": {"label": i18n.t("Go and look"), "tool": "browser_control",
                           "args": {"url": item.get("url", "")}}
                if item.get("url") else None}

    def _nav(self, items: list, page: int, pages: int) -> list[dict]:
        """아래 단추 줄 — 결정 하나와 쪽 넘김 둘. ★순서가 곧 중요도다★"""
        out: list[dict] = []
        if items:
            # ★"끊었어"를 **누를 수 있어야** 적힌다★ 말로만 받으면 화면을 보다가
            # 결정한 사람은 답할 자리가 없고, 그러면 우리는 계속 묻는다.
            #
            # ⚠️ ★쪽마다 있다★ (2026-08-19 · 찍어 보고 알았다) 처음에는 쇼핑을 따라
            # 첫 쪽에만 두었는데, 쇼핑의 그 단추는 **보이는 후보 하나를 사는** 것이라
            # 안 보이면 위험했다. 이것은 다르다 — *"이 여행 끊었다"* 는 항공편이
            # 아니라 **노선**에 대한 표시라 3쪽에서 눌러도 뜻이 같다. 첫 쪽에만 두면
            # 뒤쪽을 보다 결정한 사람은 답할 자리가 없어진다.
            out.append({"label": i18n.t("I booked it"), "tool": self.name,
                        "style": "primary", "args": {"action": "booked"}})
        if page > 0:
            out.append({"label": "◀ " + i18n.t("Previous"), "tool": self.name,
                        "args": {"action": "prev"}})
        if page + 1 < pages:
            # ★말로 하는 것과 **같은 이름**★ 버튼에 "다음"이라 써 놓고 말로는 다른
            # 낱말을 받으면, 사용자는 둘 중 하나를 못 쓴다.
            out.append({"label": i18n.t("Show the next ones") + " ▶",
                        "tool": self.name, "args": {"action": "next"}})
        return out

    # -- 화면이 읽을 것을 남긴다 ----------------------------------------------
    def _remember_view(self, ctx: ToolContext, route: str, flights: list[Flight],
                       past: dict, diff: dict, trip: Trip,
                       nearby: list[dict] | None = None) -> None:
        """★도구와 화면이 **같은 것**을 본다★ 화면이 다시 검색하면 두 번 돈다."""
        # ★값 흐름은 **브레인에서** 온다★ 화면 상태에만 두면 다른 노선을 한 번
        # 찾아보는 순간 이력이 통째로 사라지고, 선은 영영 두 점을 못 넘는다.
        history = list(past.get("history") or [])
        best = cheapest(flights)
        if best:
            history = _extend_history(history, best.seen_at, best.price)
        pick = best_pick(flights)
        reason = pick_reason(flights, pick)
        try:
            _save(ctx, {
                # ★새 검색은 **첫 쪽부터**★ 3쪽을 보던 중에 다른 노선을 찾으면,
                # 쪽수가 남아 있어 새 목록의 9번째부터 보인다(고장으로 읽힌다).
                "route": route, "depart": trip.depart,
                # ★출발지도 적는다★ 더 싼 날 단추가 이것 없이 다시 찾으면 *"어디서든
                # 도쿄"* 가 되어 **다른 노선의 값**을 가져온다(항공편 줄에서 되찾을
                # 수도 있지만, 그것은 공항 코드라 사용자가 말한 것과 다를 수 있다).
                "origin": trip.origin,
                "return_on": trip.return_on, "airline": trip.airline,
                "nonstop": bool(trip.nonstop), "diff": diff,
                "history": history, "page": 0,
                # ★더 싼 날은 **화면도** 봐야 한다★ 말로만 하면 흘러가 버린다 —
                # 날짜를 바꾸는 것은 값을 보고 **결정하는** 일이라 눈에 남아야 한다.
                "nearby": list(nearby or []),
                "items": [{"airline": f.airline, "origin": f.origin,
                           "destination": f.destination, "depart": f.depart,
                           "leaves": f.leaves, "arrives": f.arrives,
                           "stops": f.stops, "minutes": f.minutes,
                           "fare_type": f.fare_type,
                           "price": f.price, "currency": f.currency,
                           "note": f.note, "seen_at": f.seen_at, "url": f.url,
                           # ★미는 이유를 **그 줄에** 적는다★ 이유 없는 순위는
                           # 광고와 구별되지 않는다(화면이 다시 판정하지 않는다)
                           "reason": reason if f is pick else ""}
                          for f in flights]})
        except Exception as e:
            ctx.write_log("[flights] " + i18n.t(
                "Could not save the screen state: {detail}", detail=e))

    def _say(self, route: str, flights: list[Flight], diff: dict,
             nearby: list[dict] | None = None) -> str:
        """★음성은 짧아야 한다★ 목록을 읽어 주면 사람은 넷째쯤에서 앞을 잊는다."""
        lines = [headline(route, flights, diff)]
        for f in flights[1:2]:
            when = f" {f.leaves}" if f.leaves else ""
            lines.append(f"{f.airline}{when} {money(f.price, f.currency)}, "
                         f"{stops_text(f.stops)}".strip())
        # ★더 싼 날은 **한 줄만**★ 목록을 읽어 주면 음성이 길어져 아무것도 안 남는다.
        # 가장 싼 하루만 말하고 나머지는 화면이 진다.
        if nearby:
            best = nearby[0]
            lines.append(i18n.t(
                "Leaving {date} instead would be {price}.",
                date=best.get("date", ""),
                price=money(best.get("price"), best.get("currency", ""))))
        if len(flights) > PAGE_SIZE:
            lines.append(i18n.t("I lined up {count} of them on the screen.",
                                count=len(flights)))
            # ★더 있다는 것을 **말해 줘야** 넘긴다★ 화면 단추만 두면 말로 쓰는
            # 사람은 뒤 페이지가 있는 줄도 모르고, 마음에 안 들면 검색을 다시 한다.
            lines.append(i18n.t("Say 'show the next ones' for more."))
        return "\n".join(lines)

    # -- 브레인 ---------------------------------------------------------------
    def _remember(self, ctx: ToolContext, trip: Trip,
                  flights: list[Flight]) -> None:
        """★기억은 부산물이다★ 실패해도 사용자는 검색 결과를 받는다."""
        try:
            remember_search(ctx.brain, str(getattr(ctx, "user_id", "") or "local"),
                            trip.origin, trip.destination, flights,
                            trip=trip, agent=self)
        except Exception as e:
            ctx.write_log(f"[flights] could not remember: {e}")


def _headlines(diff: dict) -> list[dict]:
    """지난번과 견줘 **말할 만한 것**만. 없으면 빈 목록이다.

    ★묻는 것은 **답을 받을 자리가 있을 때만**★ *"끊었나요?"* 를 물어 놓고 답을
    아무 데도 안 적으면, 열 번을 물어도 매번 처음이다(쇼핑에서 실측으로 잡았다).
    여기서 묻는 것은 `_settle`이 받아 적는다.
    """
    if not diff:
        return []
    if diff.get("booked"):
        return [{"tone": "muted",
                 "text": i18n.t("You booked this one — I am not watching the fare "
                                "any more.")}]
    if diff.get("first_time") or diff.get("stale"):
        return []
    delta, unit = diff.get("delta"), diff.get("currency") or ""
    if delta is None or not delta:
        return []
    if delta < 0:
        return [{"tone": "good",
                 "text": i18n.t("This route is down {amount} since you last looked. "
                                "Did you book it?", amount=money(abs(delta), unit))}]
    return [{"tone": "warn",
             "text": i18n.t("This route is up {amount} since you last looked.",
                            amount=money(delta, unit))}]
