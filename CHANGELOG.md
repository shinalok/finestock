# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



## [1.0.1.0] - 2026-03-11

### Added
- Added `get_price(self, code)` method to `MarketDataProvider` interface and all broker implementations (`LS`, `Kis`, `Kiwoom`).
  - Fetches the current day's OHLCV data and returns it as a single `finestock.Price` object.

## [1.0.0.1] - 2026-03-06

### Changed
- **Structural Refactoring**:
  - Decoupled `APIFactory` to support lazy loading of broker implementations.
  - Split `IAPI` into segregated interfaces: `MarketDataProvider`, `RealtimeProvider`, `AuthenticationProvider`.
  - Deprecated `set_queue` in favor of `set_data_queue(queue)` which no longer requires a `threading.Condition`.
  - Standardized naming conventions (PEP 8):
    - Private methods now use single underscore `_` prefix.
    - Renamed `do_order_cancle` to `do_order_cancel`.

## [0.5.3.1]

### Fixed
- remove unused log
---


## [0.5.3.0]

### Changed
- `exchgubun` parameter to `get_ohlcv(self, code, todate="", exchgubun="K", cts_date="", cts_time="", tr_cont_key="")` for specifying the exchange (default: `"K"` for KRX)

### Fixed
- LS API recv_order_status error
---

---

## [0.5.2.1] - 2025.11.05

### Fixed
- LS API response parsing error(do_oder return None)
---

## [0.5.2.0] - 2025.05.15

### Added
- Introduce `def get_index(self, code, frdate="", todate="", cts_date="", tr_cont_key=""):`  
  ‒ Fetches minute-level INDEX data with optional continuation tokens.
- Introduce `get_ohlcv_min(self, code, todate="", exchgubun="K", cts_date="", cts_time="", tr_cont_key="")`  
  ‒ Fetches minute-level OHLCV data with optional continuation tokens.
---

## [0.0.0.0]

### Added
- 최초 릴리스: EBest OpenAPI 래퍼 기본 기능 제공

---ex) `get_realtime_data()` 메서드 지원

### Changed
- 기존 기능이 대규모로 변경되었을 때 기록하세요.
- ex) 내부 API 응답 포맷 변경

### Deprecated
- 앞으로 제거될 예정인 기능을 명시하세요.
- ex) `old_fetch_price()` 메서드 (v1.3.0에서 제거 예정)

### Removed
- 기능이 제거되었을 때 기록하세요.
- ex) `legacy_mode` 옵션 제거

### Fixed
- 버그 수정 내용을 기록하세요.
- ex) 날짜 필터링 시 경계값 오류 수정

### Security
- 보안 이슈 대응 내역을 기록하세요.
- ex) OAuth 토큰 누수 취약점 패치

---
