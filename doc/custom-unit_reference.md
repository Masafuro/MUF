# カスタムユニット開発リファレンス

詳しくは
https://github.com/Masafuro/muf-sample-unit

## ディレクトリ構造

```md
(Project-root)/
├── docker-compose.yml         # プロジェクト全体用
├── custom-unit/               # カスタムユニットディレクトリ
│   ├── Dockerfile             # ユニット単体試験用
│   ├── docker-compose.yml     # ユニット単体試験用
│   ├── main.py                # カスタムユニットの動作プログラム等
│   ├── requirements.txt       # 依存関係等
│   └── static/, templates/    # 関連ファイル等
└── muf/                       # **サブモジュール** MUF SDK本体
```

## プロジェクト全体用 (Project-root)/docker-compose.yml のサンプル
```yml
# Project-root
# /docker-compose.yml
include:
  # muf SDK 不要なものはコメントアウトする。
  - muf/redis/docker-compose.yml
  - muf/monitor/docker-compose.yml
  - muf/terminal/docker-compose.yml
  - muf/echo-unit/docker-compose.yml
  - muf/check-unit/docker-compose.yml
  
  # custom-unit
  - custom-unit/docker-compose.yml
```

## カスタムユニット用 custom-unit/docker-compose.yml のサンプル
```yml
# custom-unit/docker-compose.yml
# custom-unitでFastAPIでサーバーを立てる場合のサンプル
services:
  muf-sample-unit:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: muf-sample-unit
    # ホストの8000番ポートをコンテナの8000番に繋ぎ、ブラウザアクセスを許可します
    ports:
      - "8000:8000"
    volumes:
      # サブモジュール（親ディレクトリ）のmufをSDKとしてマウント
      - ../muf:/app/muf
      # ユニット自身のソースコードをマウント
      - .:/app/sample-unit
    networks:
      - muf-network
    restart: always

# muf-networkに参加することで、MUFによる通信ができる。
networks:
  muf-network:
    name: muf-network
    # external: true をつかってはいけない。
```

## カスタムユニット用 custom-unit/Dockerfile のサンプル
```Dockerfile
# custom-unitでFastAPIでサーバーを立てる場合のサンプル
FROM python:3.11-alpine

# Webサーバー、テンプレートエンジン、Redisライブラリをインストール
RUN pip install redis fastapi uvicorn jinja2

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/muf:/app

# 起動コマンド
CMD ["uvicorn", "sample-unit.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
## カスタムユニット用 custom-unit/main.py について
```python

# MUFライブラリのインポート
from muf import MUFClient

```

