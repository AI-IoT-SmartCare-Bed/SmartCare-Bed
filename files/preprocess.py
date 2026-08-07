"""
preprocess.py
=============
DB(sensor_reading)에 쌓인 원시 센서값을 읽어서 전처리한다.
  원시값 → 이상치 제거 → 이동평균(window=5) → 0~1 정규화
전처리 목적: 노이즈 섞인 raw 데이터를 AI 모델 입력에 적합한 형태로 정제.

★ 2026-08-07: fake_publisher.py 가 FSR 하나만이 아니라 제작설계서 기준
  6종 센서(FSR·DISTANCE·IMU·LOADCELL·PIR·HR·RESP)를 모두 발행하도록 바뀌어서,
  이 스크립트도 센서 하나만 처리하던 걸 SENSOR_RANGES 딕셔너리 기반으로
  모든 센서를 순회하며 처리하도록 확장했다.
  (회의 답변용) 센서마다 이상치 범위가 다른 이유: 부품 스펙이 서로 다르기
  때문. 예를 들어 FSR은 0~4095(ADC 원값)인데 IMU 각도는 -90~90도라서
  같은 기준으로 이상치를 거르면 안 된다.

실행: python preprocess.py
"""

import pandas as pd
import psycopg2

# ── DB 연결 (subscriber.py와 동일한 smartcare DB) ──────────────
conn = psycopg2.connect(
    host="localhost", port=5432,
    dbname="smartcare", user="postgres", password="smartcare123"
)

# ── 센서별 정상 범위 정의 ────────────────────────────────────
# 이 범위를 벗어난 값은 센서 오류/노이즈로 보고 버린다.
# (제작설계서 "핵심 소스코드" / "배선 상세" 의 부품 스펙 기준)
SENSOR_RANGES = {
    "FSR":      (0, 4095),     # FSR-402, ESP32 12bit ADC 원값
    "DISTANCE": (2, 400),      # HC-SR04 초음파, 데이터시트 측정 거리(cm)
    "IMU":      (-90, 90),     # MPU6050 기울기(도)
    "LOADCELL": (0, 150),      # 로드셀+HX711, 4모서리 합산 체중(kg)
    "PIR":      (0, 1),        # HC-SR501, 움직임 감지 이진값(0/1)
    "HR":       (30, 180),     # MR60BHA1 심박수(bpm), 정상 범위보다 넉넉하게
    "RESP":     (5, 40),       # MR60BHA1 호흡수(회/분)
}

# ── 센서별로 전처리 수행 ─────────────────────────────────────
for sensor_code, (vmin_valid, vmax_valid) in SENSOR_RANGES.items():

    # ① DB에서 원시 데이터 읽기 (해당 센서만, 시간순)
    df = pd.read_sql(
        "SELECT time, value FROM sensor_reading "
        "WHERE sensor_code = %(code)s ORDER BY time",
        conn, params={"code": sensor_code}
    )

    if df.empty:
        print(f"\n[{sensor_code}] 데이터 없음 — 건너뜀 (fake_publisher를 아직 안 돌렸을 수 있음)")
        continue

    print(f"\n[{sensor_code}] 원시 데이터 {len(df)}건 불러옴")

    # ② 이상치 제거: 센서별 정상 범위를 벗어난 값은 오류로 보고 버린다.
    before = len(df)
    df = df[(df["value"] >= vmin_valid) & (df["value"] <= vmax_valid)]
    print(f"[{sensor_code}] 이상치 제거: {before} → {len(df)}건")

    # ③ 이동평균 (window=5)
    # 최근 5개 값의 평균으로 부드럽게. 순간적으로 튀는 노이즈를 완화한다.
    # 설계서 기준 window=5. (PIR처럼 0/1 이진값도 이동평균을 내면 "최근 재실 비율"이 되어 나름 의미가 있다.)
    df["ma"] = df["value"].rolling(window=5).mean()

    # ④ 0~1 정규화 (Min-Max)
    # 값을 (현재값-최소)/(최대-최소)로 0~1 사이에 압축.
    # AI 모델은 센서마다 스케일이 다른 입력을 그대로 섞으면 학습이 불안정하므로
    # 전부 0~1로 맞춰서 같은 스케일로 비교할 수 있게 한다.
    vmin, vmax = df["value"].min(), df["value"].max()
    if vmax > vmin:
        df["norm"] = (df["value"] - vmin) / (vmax - vmin)
    else:
        # 값이 전부 같으면(예: PIR이 계속 0) 분모가 0이 되므로 예외 처리.
        df["norm"] = 0.0

    # ── 결과 확인 ────────────────────────────────────────────
    # value=원시, ma=이동평균, norm=정규화. 앞쪽 ma가 비어있는(NaN) 건
    # 아직 5개가 안 모여서 평균을 못 낸 것 → 정상.
    print(f"[{sensor_code}] 전처리 결과 (마지막 5줄):")
    print(df[["time", "value", "ma", "norm"]].tail(5))

conn.close()
