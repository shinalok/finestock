# finestock
Korean Stock OpenAPI Package (LS, KIS)  
Created by alshin

---

## Table of Contents
1. [설치](#설치)
2. [환경변수 설정 (.env)](#환경변수-설정-env)
3. [아키텍처](#아키텍처)
4. [사용법](#사용법)
5. [Release Notes](#release-notes)
6. [License](#license)

---

## 설치

```bash
pip install finestock
```

---

## 환경변수 설정 (.env)

브로커 앱키/시크릿/계좌번호/액세스 토큰은 코드에 직접 하드코딩하지 말고 환경변수로 주입한다. 저장소 루트의 `.env.example`을 복사해 `.env`로 만들고 실제 값을 채워 넣는다.

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

`.env`는 `.gitignore`에 의해 커밋되지 않는다(`.env.example`만 커밋 대상).

### 값 로드 방법

`example.py`, `example_async.py`는 모두 `os.environ.get("APP_KEY", ...)` 형태로 값을 읽는다. `.env` 파일 자체는 셸이나 파이썬이 자동으로 읽어주지 않으므로 아래 두 방법 중 하나가 필요하다.

**1) python-dotenv로 자동 로드 (권장)**

```bash
pip install python-dotenv
```

예제 스크립트는 `python-dotenv`가 설치되어 있으면 시작 시 자동으로 `.env`를 읽어 `os.environ`에 채워 넣는다(설치돼 있지 않으면 조용히 건너뛴다). 직접 스크립트를 작성할 때도 아래처럼 최상단에서 호출하면 된다.

```python
from dotenv import load_dotenv
load_dotenv()

import os
app_key = os.environ.get("APP_KEY")
app_secret = os.environ.get("APP_SECRET")
```

**2) 셸에서 직접 환경변수 설정**

```powershell
# PowerShell
$env:APP_KEY = "YOUR_APP_KEY"
$env:APP_SECRET = "YOUR_APP_SECRET"
python example.py
```

```bash
# bash
export APP_KEY="YOUR_APP_KEY"
export APP_SECRET="YOUR_APP_SECRET"
python example.py
```

---

## 아키텍처

`finestock`은 **파사드 패턴(Facade Pattern)**과 **인터페이스 분리 원칙(ISP)**을 결합하여 설계되었습니다.

### 1. 통합된 상태 관리 (Facade)
`create_api`로 생성되는 객체는 인증, 시세, 주문 등 모든 기능을 통합하여 관리합니다. 이를 통해 로그인 세션이나 소켓 연결 상태를 여러 모듈이 공유할 수 있어 사용이 편리합니다.

### 2. 인터페이스를 통한 명확한 사용 (ISP)
하나의 거대한 객체이지만, **타입 힌팅(Type Hinting)**을 통해 필요한 기능만 노출하여 안전하게 사용할 수 있습니다.

- `AuthenticationProvider`: 로그인 및 토큰 관리
- `MarketDataProvider`: 과거 시세(이력) 조회
- `RealtimeProvider`: 실시간 시세 수신
- `TradingProvider`: 주식 주문 및 잔고 조회

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
    df = api.get_ohlcv("005930", frdate="20250101", todate="20250110")
    print(df)
```

### 2. 실시간 데이터 (Queue Injection)

```python
import queue
from finestock.comm.api_interface import RealtimeProvider

if isinstance(api, RealtimeProvider):
    # 1. 데이터를 받을 큐 생성
    q = queue.Queue()
    
    # 2. 큐 주입
    api.set_data_queue(q)
    
    # 3. 데이터 수신 (비동기 루프 실행 필요)
    # ... (자세한 예제는 example_v1.py 참조)
```

### 3. 타입 힌팅 활용 (Type Hinting)

IDE에서 각 인터페이스별 메서드만 자동완성되도록 하려면 변수에 타입을 명시할 수 있습니다.

```python
from finestock.comm.api_interface import MarketDataProvider

# api 변수는 모든 기능을 가지고 있지만...
full_api = finestock.create_api(APIProvider.LS)

# MarketDataProvider로 타입을 명시하면 시세 관련 메서드만 자동완성에 노출됩니다.
market_api: MarketDataProvider = full_api

# market_api. (여기서 get_ohlcv 등만 보임)
df = market_api.get_ohlcv("005930")
```

