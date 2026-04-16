# ControlCentor

리니지2M, 오딘, 카르발 게임 자동화 컨트롤 센터

## 요구사항

- Windows 10 이상
- Python 3.9 이상
- Git

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/<저장소주소>.git
cd MyProject
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

## 실행 방법

### 방법 1 — run.bat 더블클릭 (권장)

`run.bat` 파일을 더블클릭하면 자동으로 최신 버전을 받고 실행됩니다.

### 방법 2 — 직접 실행

```bash
python AutogameCentor/Gui.py
```

## 업데이트 방법

`run.bat` 을 실행하면 매번 자동으로 최신 버전을 받아옵니다.

수동 업데이트:

```bash
git pull
```

## 주요 기능

| 기능 | 설명 |
|------|------|
| 게임 자동화 | 리니지2M, 오딘, 카르발 일일 콘텐츠 자동화 |
| 매크로 녹화 | F8/F9/F10 단축키로 마우스 동작 녹화 및 재생 |
| 멀티창 지원 | 3x3 (9개) 창 동시 제어 |
| 긴급 정지 | 실행 중 즉시 중단 |
| 로그 콘솔 | 실행 이력 실시간 확인 |

## 지원 게임

- 리니지2M (Lineage2M)
- 오딘 (Odin)
- 카르발 (Carbal)

## 주의사항

- **Windows 전용** 프로그램입니다
- 게임 클라이언트가 실행 중이어야 합니다
- 관리자 권한으로 실행하면 더 안정적으로 동작합니다
