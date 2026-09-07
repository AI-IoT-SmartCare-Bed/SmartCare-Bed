"""
train_fall_rf_v2.py
=====================
낙상 위험 예측 Random Forest 모델 — 09-05 재수집 데이터 기반 2차 버전
(FSR 위치 재배치 이후, 강아지 인형 시나리오로 재수집)

라벨 정의 (전민주 지정, 2026-09-05):
  안전(safe)     : 17:50:00 ~ 17:55:00 (정자세) + 17:55:00 ~ 18:04:00 (안전상태) — 연속 구간이라 하나로 합침
  낙상위험(risk) : 18:06:00 ~ 18:30:00 (위험)  — 실제 데이터는 18:25:36까지만 존재(그 이후로는 자동으로 잘림)
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib

# ── 1. 원시 데이터 로드 & 구간 추출 ──────────────────────────
df = pd.read_csv("sensor_reading_202609051826.csv")
df["time"] = pd.to_datetime(df["time"])

SAFE_START = pd.Timestamp("2026-09-05 17:50:00+09:00")
SAFE_END = pd.Timestamp("2026-09-05 18:04:00+09:00")     # 정자세+안전상태 통합(연속 구간)
RISK_START = pd.Timestamp("2026-09-05 18:06:00+09:00")
RISK_END = pd.Timestamp("2026-09-05 18:30:00+09:00")     # 실제 데이터는 18:25:36까지만 있음(자동으로 잘림)

safe = df[(df["time"] >= SAFE_START) & (df["time"] <= SAFE_END)].copy()
risk = df[(df["time"] >= RISK_START) & (df["time"] <= RISK_END)].copy()
safe["label"] = "safe"
risk["label"] = "fall_risk"
d = pd.concat([safe, risk], ignore_index=True)

# ── 2. long → wide 피벗 ───────────────────────────────────
wide = d.pivot_table(index=["time", "label"], columns="sensor_code", values="value", aggfunc="first")
wide = wide.reset_index().sort_values("time").reset_index(drop=True)

print(f"[전체] {len(wide)}행 ({wide['label'].value_counts().to_dict()})")

# ── 3. 특징(feature) 생성 (train_fall_rf.py와 동일 로직) ──
fsr_cols = ["FSR0", "FSR1", "FSR2", "FSR3"]
wide["fsr_mean"] = wide[fsr_cols].mean(axis=1)
wide["fsr_std"] = wide[fsr_cols].std(axis=1)
wide["fsr_max"] = wide[fsr_cols].max(axis=1)
wide["fsr_min"] = wide[fsr_cols].min(axis=1)
wide["fsr_range"] = wide["fsr_max"] - wide["fsr_min"]
wide["accel_mag"] = np.sqrt(wide["ACCEL_X"]**2 + wide["ACCEL_Y"]**2 + wide["ACCEL_Z"]**2)

# label별로 나눠서 rolling (안전→위험 사이 2분 공백이 섞여 들어가지 않도록)
wide["fsr_mean_roll_std"] = wide.groupby("label")["fsr_mean"].transform(
    lambda s: s.rolling(5, min_periods=1).std()
).fillna(0)
wide["accel_mag_roll_std"] = wide.groupby("label")["accel_mag"].transform(
    lambda s: s.rolling(5, min_periods=1).std()
).fillna(0)

FEATURES = [
    "fsr_mean", "fsr_std", "fsr_max", "fsr_min", "fsr_range",
    "accel_mag", "fsr_mean_roll_std", "accel_mag_roll_std",
    "DIST", "PIR", "SW420", "HEART", "BREATH",
]

wide = wide.dropna(subset=FEATURES)
wide.to_csv("fall_risk_labeled_dataset_v2.csv", index=False)
print(f"라벨링된 데이터셋 저장: fall_risk_labeled_dataset_v2.csv ({len(wide)}행)")

# ── 4. 학습/테스트 분리 (시간 기준 — 각 구간 뒤쪽 20%를 테스트로) ──
def time_split(g, test_frac=0.2):
    g = g.sort_values("time")
    n_test = int(len(g) * test_frac)
    return g.iloc[:-n_test], g.iloc[-n_test:]

safe_w = wide[wide["label"] == "safe"]
risk_w = wide[wide["label"] == "fall_risk"]
safe_tr, safe_te = time_split(safe_w)
risk_tr, risk_te = time_split(risk_w)

train = pd.concat([safe_tr, risk_tr]).sample(frac=1, random_state=42).reset_index(drop=True)
test = pd.concat([safe_te, risk_te]).sample(frac=1, random_state=42).reset_index(drop=True)

X_train, y_train = train[FEATURES], train["label"]
X_test, y_test = test[FEATURES], test["label"]

print(f"\n학습 {len(X_train)}행 / 테스트 {len(X_test)}행 (시간 기준 분리, 각 구간 뒤 20%를 테스트로)")

# ── 5. Random Forest 학습 ────────────────────────────────
clf = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    min_samples_leaf=5,
    random_state=42,
    class_weight="balanced",
)
clf.fit(X_train, y_train)

pred = clf.predict(X_test)
acc = accuracy_score(y_test, pred)
print(f"\n=== 테스트 정확도: {acc:.3f} ===")
print(classification_report(y_test, pred))
print("혼동행렬 (rows=실제, cols=예측):")
print(pd.DataFrame(
    confusion_matrix(y_test, pred, labels=["safe", "fall_risk"]),
    index=["실제:safe", "실제:fall_risk"],
    columns=["예측:safe", "예측:fall_risk"],
))

print("\n특징 중요도:")
imp = pd.Series(clf.feature_importances_, index=FEATURES).sort_values(ascending=False)
print(imp.round(4))

joblib.dump(clf, "fall_risk_rf_model_v2.joblib")
print("\n모델 저장: fall_risk_rf_model_v2.joblib")
