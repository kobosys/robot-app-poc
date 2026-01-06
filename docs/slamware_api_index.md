# Phoebus(P4M21) Robot App – Required Slamware REST APIs

이 문서는 현재 프로젝트의 Python 코드(`main.py`, `robot_controller.py`, `watchdog.py`)를
**Phoebus(P4M21) Slamware REST API 기반 “웨이포인트 반복 이동 + 통신 단절 시 정지”**로 구현하기 위해
필요한 최소/권장 API를 정리한 것입니다.

---

## 목표 기능

1) **Waypoint(POI) 기반 이동**
- 다중 지점(A→B→C…)을 순차 이동
- 무한 반복(loop) 가능

2) **통신(heartbeat) 단절 시 즉시 정지**
- 일정 시간 동안 heartbeat가 없으면
- 현재 실행 중인 이동 action을 강제 종료하여 stop

---

## 최소 필요 API (MVP)

### 1) POI 목록 조회 (웨이포인트 이름 검증)
- `GET /api/multi-floor/map/v1/pois`
- 목적: 코드의 `waypoints = ["A","B","C"]` 같은 문자열이 **실제 POI 이름(poi_name)** 과 일치하는지 확인

**코드 연결 위치**
- `RobotController.start()` 시작 직후
- 또는 `start()` 전에 waypoint 리스트를 검증하는 함수에서 사용

---

### 2) 이동 Action 생성 (POI로 이동 시작)
- `POST /api/core/motion/v1/actions`
- 목적: 특정 POI로 이동하는 action을 생성하여 로봇 이동 시작

**권장 Action 타입**
- `slamtec.agent.actions.MultiFloorMoveAction` (target: `poi_name`)
- (대안) 다중 지점을 한 번에 넣는 방식이면 `SeriesMoveToAction` 사용 검토

**코드 연결 위치**
- `RobotController._move_to_waypoint(waypoint)` 내부

---

### 3) 이동 Action 상태 조회 (완료/실패/진행 확인)
- `GET /api/core/motion/v1/actions/{action_id}`
- 목적: action이 완료될 때까지 폴링하거나 실패 시 처리

**코드 연결 위치**
- `RobotController._move_to_waypoint()` 내부에서 polling
  - 완료: 다음 waypoint로 진행
  - 실패: retry/skip/stop 등 정책 적용

---

### 4) 현재 Action 강제 종료 (정지)
- `DELETE /api/core/motion/v1/actions/:current`
- 목적: 통신 단절 또는 외부 stop 명령 시 **즉시 정지**

**코드 연결 위치**
- `RobotController.stop()` 내부
- `Watchdog.trigger_stop()`가 stop 호출 시 여기까지 연결

---

## 통신 단절(heartbeat) 감지에 유용한 API (권장)

### 이벤트 폴링 기반 heartbeat
- `GET /api/platform/v1/events`
- 목적: 주기적으로 호출하여 응답이 오면 “alive”, 일정 시간 무응답이면 “disconnect”로 간주

**코드 연결 위치**
- 별도 heartbeat 스레드/루프에서 주기 호출 → 성공 시 `watchdog.feed()`

---

## 운영 안정성(권장)

### 배터리/전원 상태
- `GET /api/core/system/v1/power/status`
- 목적: 배터리 부족/도킹 상태 등으로 이동 정책 제어

### 로봇 헬스
- `GET /api/core/system/v1/robot/health`
- 목적: fault 상태에서 이동 시작 금지, 즉시 stop 등

### 시스템 capabilities
- `GET /api/core/system/v1/capabilities`
- 목적: 시작 시 로봇 가용성 확인 (초기화/서비스 준비)

---

## 구현 매핑(요약)

- 시작 시:
  - `GET .../capabilities`
  - `GET .../pois` (waypoint 유효성 검증)

- waypoint 이동:
  - `POST .../actions` (이동 action 생성)
  - `GET .../actions/{id}` (완료될 때까지 polling)

- stop:
  - `DELETE .../actions/:current`

- heartbeat:
  - 주기적으로 `GET .../events` 성공하면 watchdog feed
  - 일정 시간 무응답이면 watchdog timeout → stop 호출

---

## Next Step (Codex 작업 지시 예시)

- `robot_controller.py`에 HTTP client(예: requests) 추가
- base_url, token(필요 시) 환경변수화
- `_move_to_waypoint()`를 action 생성 + polling으로 교체
- `stop()`을 `DELETE /actions/:current` 호출로 교체
- `watchdog.py`에 heartbeat feed 함수 연결 (events polling 스레드)
