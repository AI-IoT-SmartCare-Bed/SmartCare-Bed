-- ==============================================================================
-- sensor_reading 테이블 초기화 스크립트
-- ==============================================================================
-- 이 스크립트는 timescaledb 컨테이너 최초 기동 시(docker-entrypoint-initdb.d)
-- 자동 실행된다. 이미 데이터 볼륨이 존재하면 다시 실행되지 않는다.
--
-- 범위 주의: 전체 ERD(8테이블) 중 이번 배포는 sensor_reading 하나만 다룬다.
-- 나머지 ERD 테이블(침대/환자/이벤트 등)은 이번 범위가 아니며 별도 마이그레이션으로
-- 추가한다.
--
-- 대상 코드(수정 금지)와 컬럼을 정확히 맞춤:
--   subscriber.py  INSERT INTO sensor_reading (time, bed_id, sensor_code, value, quality)
--   preprocess.py  SELECT time, value FROM sensor_reading WHERE sensor_code = ... ORDER BY time
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 컬럼 제약은 기존 운영 DB 덤프(dumpsmartcare, 2026-08-09)와 일치시킴:
--   bed_id / sensor_code 는 NOT NULL (subscriber.py 가 항상 값을 채워 보냄).
CREATE TABLE IF NOT EXISTS sensor_reading (
    time        timestamptz      NOT NULL,
    bed_id      text             NOT NULL,
    sensor_code text             NOT NULL,
    value       double precision,
    quality     smallint
);

-- 하이퍼테이블 전환 (시간 파티셔닝). 이미 하이퍼테이블이면 건너뜀.
SELECT create_hypertable('sensor_reading', 'time', if_not_exists => TRUE);

-- preprocess.py 의 "WHERE sensor_code = ... ORDER BY time" 조회 패턴 가속용 인덱스.
CREATE INDEX IF NOT EXISTS idx_sensor_reading_code_time
    ON sensor_reading (sensor_code, time DESC);
