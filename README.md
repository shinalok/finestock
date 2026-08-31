# finestock
Korean Stock OpenAPI Package (EBest, LS, KIS, Kiwoom, NH)
Created by alshin

---

## Table of Contents
1. [설치](#설치)
2. [지원 브로커](#지원-브로커)
3. [환경변수 설정 (.env)](#환경변수-설정-env)
4. [아키텍처](#아키텍처)
5. [사용법](#사용법)
6. [테스트](#테스트)
7. [Release Notes](#release-notes)
8. [License](#license)

---

## 설치

PyPI에 배포된 버전을 쓰려면:

```bash
pip install finestock
```

저장소를 직접 클론해서 최신 소스로 개발/테스트하려면(editable install):

```bash
git clone https://github.com/shinalok/finestock.git
cd finestock
pip install -e .
```

런타임 의존성은 `websockets`, `requests`, `loguru` 세 개뿐입니다(`requirements.txt` 참고).

---

## 지원 브로커

`APIProvider` enum(`finestock/api_factory.py`)으로 브로커를 선택합니다. `V`로 끝나는 값은 모의투자(Virtual) 전용입니다.

| Provider | 브로커 | 실전/모의 |
| --- | --- | --- |
| `APIProvider.EBEST` | 이베스트투자증권 | 실전 |
| `APIProvider.LS` | LS증권 | 실전 |
| `APIProvider.LSV` | LS증권 | 모의투자 |
| `APIProvider.KIS` | 한국투자증권 | 실전 |
| `APIProvider.KISV` | 한국투자증권 | 모의투자 |
| `APIProvider.KIWOOM` | 키움증권 | 실전 |
| `APIProvider.KIWOOMV` | 키움증권 | 모의투자 |
| `APIProvider.NH` | NH투자증권(나무) | 실전 |
| `APIProvider.NHV` | NH투자증권(나무) | 모의투자 |

```python
import finestock
from finestock import APIProvider

api = finestock.create_api(APIProvider.LS)
```

브로커마다 지원하는 메서드 범위가 조금씩 다릅니다(예: NH는 지수 조회 TR이 없고, 전종목 리스트는 REST가 아니라 `.mst` 마스터 파일로만 제공됩니다). 자세한 브로커별 차이는 각 클래스의 docstring(`finestock/{ebest,ls,kis,kiwoom,nh}/*.py`)을 참고하세요.

---

## 환경변수 설정 (.env)

브로커 앱키/시크릿/계좌번호/액세스 토큰은 코드에 직접 하드코딩하지 말고 환경변수로 주입합니다. 저장소 루트의 `.env.example`을 복사해 `.env`로 만들고 실제 값을 채워 넣으세요.

```bash
cp .env.example .env
```

`.env` 파일 내용:

```
APP_KEY=YOUR_APP_KEY
APP_SECRET=YOUR_APP_SECRET
ACCOUNT_NUM=YOUR_ACCOUNT_NUM
ACCOUNT_NUM_SUB=01
ACCESS_TOKEN=
```

`.env`는 `.gitignore`에 의해 커밋되지 않습니다(`.env.example`만 커밋 대상).

> ⚠️ 실제 앱키/시크릿을 스크립트에 직접 문자열로 적어두고 커밋하지 마세요. 한 번이라도 원격 저장소(특히 public)에 올라간 값은 즉시 노출된 것으로 간주하고 발급처(브로커 개발자센터)에서 폐기 후 재발급받아야 합니다.

### 값 로드 방법

**1) python-dotenv로 자동 로드 (권장)**

```bash
pip install python-dotenv
```

스크립트 최상단에서 아래처럼 호출하면 `.env` 값이 `os.environ`에 채워집니다(설치돼 있지 않으면 `ImportError`를 잡아 조용히 건너뛰도록 작성하는 게 일반적입니다).

```python
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
app_key = os.environ.get("APP_KEY")
app_secret = os.environ.get("APP_SECRET")
```

**2) 셸에서 직접 환경변수 설정**

```powershell
# PowerShell
$env:APP_KEY = "YOUR_APP_KEY"
$env:APP_SECRET = "YOUR_APP_SECRET"
```

```bash
# bash
export APP_KEY="YOUR_APP_KEY"
export APP_SECRET="YOUR_APP_SECRET"
```

---

## 아키텍처

`finestock`은 **파사드 패턴(Facade Pattern)**과 **인터페이스 분리 원칙(ISP)**을 결합하여 설계되었습니다.

### 1. 통합된 상태 관리 (Facade)
`create_api`로 생성되는 객체는 인증, 시세, 주문, 잔고, 실시간 등 모든 기능을 통합하여 관리합니다. 이를 통해 로그인 세션이나 소켓 연결 상태를 여러 모듈이 공유할 수 있어 사용이 편리합니다.

### 2. 인터페이스를 통한 명확한 사용 (ISP)
하나의 거대한 객체이지만, **타입 힌팅(Type Hinting)**을 통해 필요한 기능만 노출하여 안전하게 사용할 수 있습니다. `finestock/comm/api_interface.py`에 정의된 세그먼트:

- `AuthenticationProvider`: 로그인 및 토큰 관리(`oauth`, `set_oauth_info`, `set_access_token`)
- `MarketDataProvider`: 시세/OHLCV/지수/호가 조회(`get_price`, `get_ohlcv`, `get_ohlcv_min`, `get_index`, `get_orderbook`, ...)
- `TradingProvider`: 주문 실행/취소(`do_order`, `do_order_cancel`)
- `RealtimeProvider`: WebSocket 실시간 구독(`set_data_queue`, `recv_price`, `recv_orderbook`, ...)
- `AccountProvider`: 계좌 잔고/보유종목 조회(`get_balance`, `get_holds`)
- `InfoProvider`: 종목/지수 마스터 목록(`get_stock_list`, `get_index_list`)

이 인터페이스들의 합집합(`BaseProvider`)을 모든 브로커 클래스가 구현합니다. 타입 힌팅은 IDE 자동완성을 좁히기 위한 것일 뿐, 런타임 제약은 없습니다.

### 3. 데이터 모델 (`finestock/model/`)
브로커가 반환하는 원시 JSON/TR 응답은 파싱되어 공통 `@dataclass(frozen=True)` 타입(`Price`, `OrderBook`, `Hold`, `Account`, `Order`, `Trade`, `Stock`, `Index`)으로 통일됩니다.

---

## 사용법

### 1. 기본 사용 (Factory & Interface)

```python
import finestock
from finestock import APIProvider
from finestock.comm.api_interface import AuthenticationProvider, MarketDataProvider

# 1. API 객체 생성 (통합 객체)
api = finestock.create_api(APIProvider.LS)

# 2. 인증 (AuthenticationProvider 인터페이스 활용)
if isinstance(api, AuthenticationProvider):
    api.set_oauth_info("YOUR_APP_KEY", "YOUR_APP_SECRET")
    # api.oauth() # 로그인 필요 시 호출

# 3. 데이터 조회 (MarketDataProvider 인터페이스 활용)
if isinstance(api, MarketDataProvider):
    # IDE에서 get_ohlcv 등 시세 관련 메서드만 자동완성됨
    ohlcvs = api.get_ohlcv("005930", frdate="20260101", todate="20260110")
    print(ohlcvs)
```

### 2. 계좌 조회 (AccountProvider)

```python
from finestock.comm.api_interface import AccountProvider

if isinstance(api, AccountProvider):
    account = api.get_balance()
    if account:
        print(account.deposit, len(account.hold))
```

### 3. 실시간 데이터 (Queue Injection)

```python
import queue
from finestock.comm.api_interface import RealtimeProvider

if isinstance(api, RealtimeProvider):
    # 1. 데이터를 받을 큐 생성
    q = queue.Queue()

    # 2. 큐 주입
    api.set_data_queue(q)

    # 3. 데이터 수신 (asyncio 이벤트 루프에서 api.connect()/api.run() 실행 필요)
    #    브로커별 recv_price / recv_orderbook / recv_trade 등을 구독한 뒤
    #    q.get()으로 파싱된 finestock.Price / OrderBook / Trade 객체를 받는다.
```

### 4. 타입 힌팅 활용 (Type Hinting)

IDE에서 각 인터페이스별 메서드만 자동완성되도록 하려면 변수에 타입을 명시할 수 있습니다.

```python
from finestock.comm.api_interface import MarketDataProvider

# api 변수는 모든 기능을 가지고 있지만...
full_api = finestock.create_api(APIProvider.LS)

# MarketDataProvider로 타입을 명시하면 시세 관련 메서드만 자동완성에 노출됩니다.
market_api: MarketDataProvider = full_api

# market_api. (여기서 get_ohlcv 등만 보임)
ohlcvs = market_api.get_ohlcv("005930", frdate="20260101", todate="20260110")
```

---

## 테스트

```bash
python -m unittest discover tests          # 전체 테스트
python -m unittest tests.test_model -v      # 특정 모듈만
```

`pytest` 설정은 없으며 표준 라이브러리 `unittest`를 사용합니다.

---

## Release Notes

전체 변경 이력은 [CHANGELOG.md](./CHANGELOG.md)를 참고하세요. 최근 주요 변경:

- **1.0.1.0**: `MarketDataProvider`에 `get_price(code)` 추가(당일 OHLCV를 단일 `Price`로 반환)
- **1.0.0.1**: `APIFactory` lazy loading 도입, 인터페이스 분리(ISP) 리팩터링, 메서드 네이밍 PEP 8 표준화
- (개발 중) NH투자증권(나무) 브로커 지원 추가 — `APIProvider.NH` / `APIProvider.NHV`

---

## License

별도의 LICENSE 파일은 아직 저장소에 포함되어 있지 않습니다. 라이선스 조건이 필요하다면 저장소 관리자(`shinalok`)에게 문의해 주세요.
