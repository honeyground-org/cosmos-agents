"""그물이 코스모스를 **찾을 수 있게** 한다 — 못 찾으면 ★그렇다고 말하고 멈춘다★.

에이전트는 코스모스의 계약(`cosmos.contracts.*`)을 임포트한다. 그 체크아웃이 어디
있는지는 사람마다 다르므로 세 곳을 차례로 본다:

    ① 환경변수 `COSMOS_HOME`
    ② 이 저장소의 형제 폴더 `../cosmos-billy`
    ③ 이미 `sys.path`에 있는 경우(설치된 코스모스 안에서 도는 경우)

★못 찾으면 **건너뛰지 않고 멈춘다**★ 조용히 건너뛰면 전부 초록인데 아무것도 검사하지
않은 상태가 되고, 그 초록을 보고 릴리스하게 된다(이 프로젝트가 여러 번 데인 자리).

그리고 에이전트 폴더 자체를 경로에 넣는다 — `shopping_scout`가 `shopping_core`를
이름 그대로 임포트하기 때문이다(설치되면 그 폴더가 곧 패키지 자리다).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _cosmos_root() -> Path | None:
    candidates = []
    if home := os.environ.get("COSMOS_HOME", "").strip():
        candidates.append(Path(home).expanduser())
    candidates.append(HERE.parent / "cosmos-billy")
    for path in candidates:
        if (path / "cosmos" / "contracts" / "__init__.py").is_file():
            return path
    return None


def pytest_configure(config):
    root = _cosmos_root()
    if root is None:
        try:
            import cosmos.contracts  # noqa: F401
        except ImportError:
            raise pytest.UsageError(
                "코스모스를 못 찾았습니다 — 그물이 아무것도 검사하지 못합니다.\n"
                "  COSMOS_HOME=/path/to/cosmos-billy python -m pytest shopping/tests\n"
                "또는 이 저장소 옆에 cosmos-billy 를 체크아웃하세요.")
    else:
        sys.path.insert(0, str(root))
    # 에이전트 폴더들 — 설치되면 각 폴더가 곧 임포트 자리다
    for folder in sorted(p for p in HERE.iterdir() if (p / "cosmos-agent.yaml").is_file()):
        sys.path.insert(0, str(folder))
