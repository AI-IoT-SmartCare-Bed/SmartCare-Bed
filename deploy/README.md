# 스마트 케어 침대 데이터서버 배포 (deploy/)

대상: `../data-server/{subscriber,fake_publisher,preprocess}.py` (수정하지 않음)

## 0. (1GB RAM 서버, 예: Lightsail 소형 인스턴스) 스왑 2GB 추가

TimescaleDB + mosquitto + python 스크립트를 1GB RAM에서 동시에 돌리면 메모리가
빠듯하다. OOM-kill 방지용으로 스왑을 먼저 만든다.

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h   # 확인
```

## 1. 컨테이너 기동

```bash
cd deploy
docker compose up -d
docker compose ps       # timescaledb, mosquitto 둘 다 healthy/running 확인
docker compose logs -f timescaledb   # init.sql 정상 실행됐는지 확인 (최초 1회만)
```

- `timescaledb`: 5432 포트, DB `smartcare` / user `postgres` / password `smartcare123`.
  기동 시 `init.sql` 이 자동 실행되어 `sensor_reading` 하이퍼테이블이 생성된다.
- `mosquitto`: 1883 포트, 인증 없음(데모).

## 2. 파이썬 가상환경 + 의존성 설치

```bash
cd data-server
python3 -m venv venv
source venv/bin/activate
pip install -r ../deploy/requirements.txt
```

## 3. 실행 순서

터미널 3개(또는 tmux/screen 세션 3개)를 열어 각각 실행한다.

```bash
# 터미널 1: 구독자 (MQTT → DB 저장) — 먼저 띄워둔다
python subscriber.py

# 터미널 2: 가짜 발행자 (테스트용, 실제 ESP32가 있으면 생략)
python fake_publisher.py

# 터미널 3: 전처리 (쌓인 데이터를 어느 정도 확보한 뒤 실행)
python preprocess.py
```

## 참고: preprocess.py 쿼리 범위 주의

`preprocess.py` 는 현재 `sensor_code` 조건만 걸고 **테이블 전체를 시간순 정렬**해서
읽어온다(`ORDER BY time`, 기간 제한 없음). 데이터가 오래 쌓일수록 조회 부하와
메모리 사용량이 커지므로, 1GB RAM 서버에서 장기 운영한다면 쿼리에
`AND time > now() - interval '6 hours'` 같은 "최근 N시간만" 조건을 추가하는 것을
권장한다. (이번 배포 범위는 컨테이너/설정 파일까지이며, 이 개선은 `preprocess.py`
코드 수정이 필요하므로 별도 작업으로 남겨둔다 — 코드는 손대지 않았다.)

## (선택) 기존 운영 DB 데이터 복원

기존에 쓰던 데이터(`dumpsmartcare...sql`)를 새 서버로 옮기려면. **이 덤프는 확장자만 `.sql`이고 실제로는 pg_dump custom-format 아카이브(PGDMP)라 `psql`이 아니라 `pg_restore`로 복원한다.** TimescaleDB 하이퍼테이블이 포함돼 있어 pre/post_restore 절차가 필요하다.

```bash
# 0) 덤프 파일을 서버로 복사 (로컬에서)
scp -i <키.pem> dumpsmartcare....sql ubuntu@<host>:/home/ubuntu/dump.sql

# 1) 컨테이너 기동(위 1번) 후, init.sql이 만든 빈 sensor_reading는 비우고 복원 준비
docker cp /home/ubuntu/dump.sql smartcare-timescaledb:/tmp/dump.sql
docker exec -it smartcare-timescaledb bash

# 2) 컨테이너 안에서 — TimescaleDB 복원 절차
psql -U postgres -d smartcare -c "SELECT timescaledb_pre_restore();"
pg_restore -U postgres -d smartcare --no-owner --clean --if-exists /tmp/dump.sql
psql -U postgres -d smartcare -c "SELECT timescaledb_post_restore();"

# 3) 확인
psql -U postgres -d smartcare -c "SELECT count(*) FROM sensor_reading;"
```

> 새로 시작(빈 DB)할 거면 이 절차는 건너뛰고 `init.sql`이 만든 빈 테이블을 그대로 쓴다.

## 정리

```bash
docker compose down          # 컨테이너만 종료 (데이터 볼륨은 유지)
docker compose down -v       # 데이터까지 삭제할 때만 (주의)
```

## 보안 체크리스트 (운영 전환 시)

- [ ] `POSTGRES_PASSWORD` 를 강한 값으로 교체하고 `.env`/secrets 로 분리
- [ ] mosquitto `allow_anonymous false` + 비밀번호 파일 적용
- [ ] 5432/1883 포트를 공인 IP에 그대로 노출하지 말 것 — 방화벽/보안그룹으로
      제한하거나 `docker-compose.yml` 의 ports 를 `127.0.0.1:PORT:PORT` 로 바꿔
      로컬호스트 전용으로 제한
