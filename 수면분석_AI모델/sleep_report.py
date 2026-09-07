"""
sleep_report.py
================
AI-06 수면 분석: 뒤척임(체위 변화) 횟수 계산 + 수면 깊이 리포트 생성.

역할 분담(개발보고서 기준):
  [AI] AI-06 수면 분석 — 뒤척임·수면 깊이 리포트 "계산"하는 부분 = 이 스크립트(전민주)
  [앱] APP-04 수면 리포트 — 그 결과를 "일별 건강 데이터"로 화면에 보여주는 부분 = 이아인

※ 중요 — "수면 깊이"는 규칙 기반(rule-based) 근사치입니다.
EEG 같은 정식 수면다원검사 데이터/라벨이 없어서, 낙상위험 모델처럼 실측
데이터로 학습시킬 수 없었어요. 대신 "움직임이 적고 심박/호흡이 안정적일수록
깊게 자는 것"이라는 상식적인 가정으로 3단계(깊은 수면/얕은 수면/뒤척임·각성)를
나눈 것뿐이라, 의학적으로 정확한 수면 단계 분류는 아닙니다. 나중에 실제
수면 단계 라벨(예: 워치 등 다른 기기로 검증한 데이터)이 생기면 그때 학습
기반 모델로 바꾸는 게 맞아요.

"뒤척임" 판정 기준은 realtime_fall_scorer.py의 "장시간 동일 자세 감지"와
똑같은 4개 센서(FSR/DIST/SW420/IMU)를 씀 — 두 기능이 같은 정의를 쓰도록
일부러 맞췄습니다.

입력: sensor_reading 테이블에서 지정한 시간 구간 (기본: 최근 8시간)
출력:
  - 콘솔 요약 (총 수면시간, 뒤척임 횟수, 시간당 뒤척임, 수면 단계별 비율)
  - sleep_report_YYYYMMDD_HHMM.json 파일 (이아인 APP-04에서 나중에 가져다 쓸 수 있게)

실행:
  python sleep_report.py                                   # 최근 8시간
  python sleep_report.py "2026-08-30 22:00" "2026-08-31 07:00"   # 구간 직접 지정
"""

import sys
import json
from datetime import timedelta

import numpy as np
import pandas as pd
import psycopg2

DB = dict(host="localhost", port=5432, dbname="smartcare", user="postgres", password="smartcare123")
BED_ID = "bed-01"

FSR_COLS = ["FSR0", "FSR1", "FSR2", "FSR3"]
NEEDED_CODES = FSR_COLS + ["ACCEL_X", "ACCEL_Y", "ACCEL_Z", "DIST", "PIR", "SW420", "HEART", "BREATH"]

# realtime_fall_scorer.py와 동일한 "움직임" 판정 기준 (일관성 유지)
FSR_TOLERANCE = 30
DIST_TOLERANCE_CM = 5
ACCEL_ROLL_STD_MOVE_THRESHOLD = 50.0
MOVE_EVENT_COOLDOWN_SEC = 30   # 이 시간 안의 연속 움직임은 하나의 뒤척임으로 합쳐서 셈(중복 방지)

EPOCH_MIN = 30   # 수면 깊이를 몇 분 단위로 나눠서 볼지


def fetch_session(bed_id, start, end):
    """DB에서 지정 구간의 sensor_reading을 wide 포맷으로 가져온다."""
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT time, sensor_code, value
        FROM sensor_reading
        WHERE bed_id = %s AND time >= %s AND time < %s
        ORDER BY time
        """,
        (bed_id, start, end),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["time", "sensor_code", "value"])
    return _pivot(df)


def _pivot(df):
    wide = df.pivot_table(index="time", columns="sensor_code", values="value", aggfunc="first")
    missing = [c for c in NEEDED_CODES if c not in wide.columns]
    if missing:
        print(f"경고: 구간 내 일부 센서 데이터 없음({missing}) — 있는 것만으로 진행")
    return wide.sort_index()


def detect_movement_events(wide):
    """realtime_fall_scorer.py와 같은 기준(FSR/DIST/SW420/IMU)으로 '뒤척임' 시점을 찾는다."""
    have_accel = all(c in wide.columns for c in ["ACCEL_X", "ACCEL_Y", "ACCEL_Z"])
    if have_accel:
        accel_mag = np.sqrt(wide["ACCEL_X"] ** 2 + wide["ACCEL_Y"] ** 2 + wide["ACCEL_Z"] ** 2)
        accel_roll_std = accel_mag.rolling(5, min_periods=1).std().fillna(0)
    else:
        accel_roll_std = pd.Series(0.0, index=wide.index)

    have_fsr = all(c in wide.columns for c in FSR_COLS)

    events = []
    ref_fsr = None
    ref_dist = None
    last_event_time = None

    for ts, row in wide.iterrows():
        fsr = row[FSR_COLS].astype(float).values if have_fsr else None
        dist = float(row["DIST"]) if "DIST" in wide.columns and not pd.isna(row["DIST"]) else None
        sw420 = float(row["SW420"]) if "SW420" in wide.columns and not pd.isna(row["SW420"]) else 0.0
        a_std = accel_roll_std.loc[ts]

        if ref_fsr is None and ref_dist is None:
            ref_fsr, ref_dist = fsr, dist
            continue

        moved = False
        if fsr is not None and ref_fsr is not None and np.max(np.abs(fsr - ref_fsr)) > FSR_TOLERANCE:
            moved = True
        if not moved and dist is not None and ref_dist is not None and abs(dist - ref_dist) > DIST_TOLERANCE_CM:
            moved = True
        if not moved and sw420 >= 1:
            moved = True
        if not moved and a_std > ACCEL_ROLL_STD_MOVE_THRESHOLD:
            moved = True

        if moved:
            if last_event_time is None or (ts - last_event_time).total_seconds() > MOVE_EVENT_COOLDOWN_SEC:
                events.append(ts)
                last_event_time = ts
            ref_fsr, ref_dist = fsr, dist

    return events


def classify_depth(n_moves, hr_std, br_std, pir_ratio):
    """규칙 기반 근사치 — 실제 수면다원검사 라벨 없이 만든 휴리스틱(본문 설명 참고)."""
    if n_moves == 0 and hr_std < 3 and br_std < 2 and pir_ratio < 0.3:
        return "깊은 수면"
    if n_moves >= 3 or pir_ratio >= 0.7:
        return "뒤척임/각성"
    return "얕은 수면"


def build_epochs(wide, events, epoch_min):
    """EPOCH_MIN 단위로 구간을 나눠서, 각 구간의 뒤척임 횟수/생체신호 안정성으로 수면 깊이를 매긴다."""
    start, end = wide.index.min(), wide.index.max()
    epoch = pd.Timedelta(minutes=epoch_min)
    events_idx = pd.DatetimeIndex(events) if events else pd.DatetimeIndex([], tz=wide.index.tz)
    epochs = []
    t = start
    while t < end:
        t_next = t + epoch
        window = wide[(wide.index >= t) & (wide.index < t_next)]
        if window.empty:
            t = t_next
            continue

        n_moves = int(((events_idx >= t) & (events_idx < t_next)).sum())

        hr = window["HEART"].replace(0, np.nan).dropna() if "HEART" in window.columns else pd.Series(dtype=float)
        br = window["BREATH"].replace(0, np.nan).dropna() if "BREATH" in window.columns else pd.Series(dtype=float)
        pir_ratio = float(window["PIR"].mean()) if "PIR" in window.columns else 0.0
        hr_std = float(hr.std()) if len(hr) > 1 else 0.0
        br_std = float(br.std()) if len(br) > 1 else 0.0

        depth = classify_depth(n_moves, hr_std, br_std, pir_ratio)

        epochs.append({
            "start": t.isoformat(), "end": t_next.isoformat(),
            "n_moves": n_moves,
            "hr_mean": float(hr.mean()) if len(hr) else None,
            "br_mean": float(br.mean()) if len(br) else None,
            "pir_ratio": round(pir_ratio, 2),
            "depth": depth,
        })
        t = t_next
    return epochs


def save_report_to_db(summary, epochs):
    """아인이 앱(APP-04)이 조회할 수 있게 DB의 sleep_report 테이블에도 저장."""
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sleep_report
            (bed_id, session_start, session_end, total_hours,
             total_turning_events, turning_per_hour, sleep_depth_ratio, epochs)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            summary["bed_id"],
            summary["session_start"],
            summary["session_end"],
            summary["total_hours"],
            summary["total_turning_events"],
            summary["turning_per_hour"],
            json.dumps(summary["sleep_depth_ratio_percent"], ensure_ascii=False),
            json.dumps(epochs, ensure_ascii=False),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def build_report(wide):
    events = detect_movement_events(wide)
    epochs = build_epochs(wide, events, EPOCH_MIN)

    total_hours = (wide.index.max() - wide.index.min()).total_seconds() / 3600
    n_events = len(events)
    per_hour = n_events / total_hours if total_hours > 0 else 0

    depth_counts = pd.Series([e["depth"] for e in epochs]).value_counts()
    depth_ratio = (depth_counts / len(epochs) * 100).round(1).to_dict() if epochs else {}

    summary = {
        "bed_id": BED_ID,
        "session_start": wide.index.min().isoformat(),
        "session_end": wide.index.max().isoformat(),
        "total_hours": round(total_hours, 2),
        "total_turning_events": n_events,
        "turning_per_hour": round(per_hour, 2),
        "sleep_depth_ratio_percent": depth_ratio,
    }
    return summary, epochs, events


def main():
    if len(sys.argv) >= 3:
        start = pd.Timestamp(sys.argv[1])
        end = pd.Timestamp(sys.argv[2])
    else:
        end = pd.Timestamp.now(tz="Asia/Seoul")
        start = end - timedelta(hours=8)

    print(f"조회 구간: {start} ~ {end}")
    wide = fetch_session(BED_ID, start, end)
    if wide is None or wide.empty:
        print("해당 구간에 데이터가 없습니다.")
        return

    summary, epochs, events = build_report(wide)

    print("\n=== 수면 리포트 요약 ===")
    print(f"수면 구간: {summary['session_start']} ~ {summary['session_end']} ({summary['total_hours']}시간)")
    print(f"총 뒤척임 횟수: {summary['total_turning_events']}회 (시간당 {summary['turning_per_hour']}회)")
    print("수면 단계 비율(%):", summary["sleep_depth_ratio_percent"])

    out = {"summary": summary, "epochs": epochs, "events": [e.isoformat() for e in events]}
    fname = f"sleep_report_{wide.index.min().strftime('%Y%m%d_%H%M')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n저장됨: {fname}")

    try:
        save_report_to_db(summary, epochs)
        print("DB에도 저장 완료 (sleep_report 테이블 → 아인이 앱이 여기서 조회하면 됨)")
    except Exception as e:
        print(f"DB 저장 실패 (sleep_report 테이블이 아직 없으면 먼저 CREATE TABLE 해야 함): {e}")


if __name__ == "__main__":
    main()
