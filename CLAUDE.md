# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`finestock` is a Python package unifying Korean stock brokerage OpenAPIs (EBest, LS, KIS, Kiwoom, NH — live and mock/simulated variants) behind one facade object. It wraps each broker's REST/WebSocket API and normalizes results into shared dataclasses (`Price`, `OrderBook`, `Account`, `Order`, `Trade`, ...).

## Commands

```bash
pip install -e .              # install package in editable mode (requirements: websockets, requests, loguru)
python -m unittest discover tests   # run tests (unittest, not pytest — no pytest config in repo)
python -m unittest tests.test_model -v   # run a single test module
```

There is no lint/format tooling configured in the repo.

## Architecture

### Facade + Factory + ISP

`finestock.create_api(APIProvider.X)` (thin wrapper around `APIFactory.create_api`, in `finestock/api_factory.py`) lazy-imports and instantiates one broker class. Every broker class multiply-inherits `BaseProvider` (`finestock/comm/api_interface.py`), a union of segregated `ABC` interfaces:

- `AuthenticationProvider` — oauth/token handling
- `MarketDataProvider` — price/OHLCV/index/orderbook queries
- `TradingProvider` — order placement/cancellation
- `RealtimeProvider` — WebSocket subscribe/unsubscribe (`recv_price`, `recv_orderbook`, etc.)
- `AccountProvider` — balance/holdings
- `InfoProvider` — stock/index master lists

Callers narrow the fat facade object to one interface via type hints (`market_api: MarketDataProvider = full_api`) purely for IDE autocomplete — there is no runtime restriction. When adding a method, add it to the relevant interface in `api_interface.py` first, then implement it in each concrete broker.

### Class hierarchy per broker

Each broker directory (`finestock/{ebest,ls,kis,kiwoom,nh}/`) has a real/live class and, in most cases, a mock-trading (`*V`) subclass that only overrides `DOMAIN`/`DOMAIN_WS` (via `finestock/path.py`) or a handful of TR IDs:

- `finestock.comm.api.API` — shared base (`finestock/comm/api.py`): holds `app_key`/`app_secret`/`access_token`, generic `headers` dict, generic `oauth()` (client_credentials POST), and `set_data_queue`/`add_data` for realtime fan-out.
- `LS(API)` — the fullest, canonical implementation (`finestock/ls/ls.py`, ~860 lines): TR-code-based REST calls (`t8410`, `t8407`, `t8452`, ...) plus a WebSocket `connect`/`run`/`recv_*` loop keyed by `tr_cd`.
  - `EBest(LS)` — EBest's API is wire-compatible with LS, so it inherits everything and only swaps `DOMAIN`/`DOMAIN_WS` via `path.py`.
  - `LSV(LS)` — LS mock trading; same overrides pattern.
- `Kis(API)` (`finestock/kis/kis.py`) — KIS uses `tr_id` header-based REST TRs. `do_order`/`do_order_cancel`/`do_order_modify` use the post-NXT (2025-03 Nextrade) TR IDs (`TTTC0012U`/`TTTC0011U`/`TTTC0013U`, verified against `koreainvestment/open-trading-api`'s `examples_llm/domestic_stock/order_cash`+`order_rvsecncl`) and require `EXCG_ID_DVSN_CD` (KRX/NXT/SOR). `do_order_cancel`/`do_order_modify` share one endpoint (`order-rvsecncl`, `RVSE_CNCL_DVSN_CD` 01=정정/02=취소) via the private `_order_rvsecncl` helper, and need the `krx_fwdg_ord_orgno` that `do_order()` returns on `Order.krx_fwdg_ord_orgno` — pass it straight through, don't invent a value. **Never guess a TR ID by pattern-matching the TTTC↔VTTC real/demo prefix convention** — verify it against the actual `koreainvestment/open-trading-api` source (or live-test it) first; `get_order_status`'s `TTTC0084R` (주식정정취소가능주문조회) has no `VTTC` counterpart in the official examples, and live-testing both `TTTC0084R` and a guessed `VTTC0084R` against the mock (`openapivts`) server got this TR rejected either way (`EGW02006`/`OPSQ0002`) — it looks like KIS's mock environment just doesn't offer this TR at all, real or fake tr_id.
  - `KisV(Kis)` — mock trading; overrides `get_balance`/`do_order`/`do_order_cancel`/`do_order_modify` with VTS-prefixed `tr_id`s (`VTTC...` vs `TTTC...`); does *not* override `get_order_status` (see above).
- `Kiwoom(API)` (`finestock/kiwoom/kiwoom.py`, ~850 lines) — Kiwoom's REST+WS shape differs most from the others (`api-id` header instead of `tr_cd`/`tr_id`, `trnm`/`REG` WS subscription protocol).
  - `KiwoomV(Kiwoom)` — mock trading, `DOMAIN`/`DOMAIN_WS` swapped to `mockapi.kiwoom.com`.
- `Nh(API)` (`finestock/nh/nh.py`) — NH투자증권(나무/Namuh) uses a uniform `POST {"Input_0": {...}}` → `{rsp_cd, Output_0[, Output_1, Output_2], message}` envelope for every REST TR, auth via `Authorization`/`x-client-id`/`x-client-secret` headers (`set_oauth_info` overridden to set the latter two). No dedicated 호가/지수 TRs — `get_orderbook` reuses the `currentPrice` TR's `askp1..10`/`bidp1..10` fields, and `get_index`/`get_index_list`/`get_stock_list` are unimplemented stubs (지수 TR 없음; 종목은 REST가 아니라 `.mst` 마스터 파일로만 제공). `oauth()` always targets the fixed live domain (`OAUTH_DOMAIN` in `path.py`) even for `NhV`, since 접근토큰발급 is live-only regardless of which domain trades run against.
  - `NhV(Nh)` — mock trading (`moapi.nhplug.com`); no method overrides needed, only `DOMAIN`/`DOMAIN_WS` swapped via `path.py`.

`finestock/path.py` centralizes all per-broker base URLs and endpoint path fragments in dict constants (`_LS_`, `_KIS_`, `_KIWOOM_`, ...) merged into `_API_PATH_`, keyed by class name; `API._init_path()` reads `_API_PATH_[self.api_type]` and sets each entry as an instance attribute (so `self.DOMAIN`, `self.CHART`, `self.ORDER`, etc. exist post-`__init__`). When adding a broker or endpoint, edit `path.py`, not the broker class, unless the URL needs runtime logic.

### Data models (`finestock/model/`)

All public dataclasses are frozen (`@dataclass(frozen=True)`) and re-exported through `finestock/model/__init__.py` and top-level `finestock/__init__.py`. Broker methods parse raw JSON/TR responses and construct these dataclasses directly (e.g. `finestock.Price(...)`, `finestock.Order(...)`) rather than returning raw dicts — new broker code should follow the same convention. `Price.from_values` / `Price.from_series` are the two supported construction paths for `Price` beyond the raw constructor.

### Realtime data flow

Realtime WebSocket data does not use callbacks; a caller injects a `queue.Queue`-like object via `set_data_queue()` (in `comm/api.py`), and broker WS loops (`LS.run`, `Kiwoom.run`) push parsed messages onto it via `add_data`/`add_price`/`add_trade`/`add_orderbook`. Broker-specific TR/type codes in the incoming WS frame determine how a message is parsed and dispatched.

## Conventions worth knowing

- Continuation/pagination in REST calls follows a broker-specific `cts_date`/`cts_time`/`tr_cont_key` (LS, Kiwoom) or `CTX_AREA_FK100`/`NK100` (KIS) pattern — recursive calls with `time.sleep()` between pages are the existing pattern for LS's `get_ohlcv`.
- Method names are standardized across brokers per `CHANGELOG.md` (PEP 8, single-underscore private prefix, `do_order_cancel` not `do_order_cancle`) — `KisV` used to keep a stub under the old misspelled name, but it's now `do_order_cancel` like everywhere else and actually implemented.
- `TradingProvider.do_order_modify(order_num, code, price, qty)` (정정) exists on every broker class (ABC requires it), but is only actually implemented for `Kis`/`KisV` — `LS`/`EBest`/`LSV`, `Kiwoom`/`KiwoomV`, `Nh`/`NhV` all have a `# TODO: ... 미연동` stub that just returns `None`. Check before assuming it works on a non-KIS broker.
- `debug.log` at the repo root is loguru output, not source.
