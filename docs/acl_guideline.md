# MUF ACL 導入ガイドライン

### 1. ユニット別環境設定ファイルの作成

各ユニットのディレクトリ直下に `.env` ファイルを作成し、認証情報を定義します。このファイルはユニットごとに固有のパスワードを設定し、他のユニットと情報を共有しないように管理してください。

```text
# [unit_name]/.env
REDIS_USERNAME=[unit_name]
REDIS_PASSWORD=[unique_password_2026]

```

---

### 2. Docker Compose による環境変数の注入

ユニットの `docker-compose.yml` において、先ほど作成した環境変数ファイルを読み込む設定を追加します。これにより、コンテナ内のアプリケーションから認証情報へアクセスが可能になります。

```yaml
# [unit_name]/docker-compose.yml
services:
  muf-[unit_name]:
    build: .
    container_name: muf-[unit_name]
    env_file:
      - .env
    environment:
      - REDIS_HOST=muf-redis
    networks:
      - muf-network
    restart: always

networks:
  muf-network:
    name: muf-network
    external: true

```

---

### 3. アプリケーションコードへの認証ロジック実装

`main.py` 等のメインエントリポイントにおいて、OSの環境変数から接続情報を取得し、`MUFClient` の初期化引数として渡すように実装を修正します。

```python
# [unit_name]/main.py
import asyncio
import os
from muf import MUFClient

async def main():
    # 環境変数から設定を読み込み、未定義の場合はデフォルト値を使用
    redis_host = os.getenv("REDIS_HOST", "muf-redis")
    db_user = os.getenv("REDIS_USERNAME", None)
    db_pass = os.getenv("REDIS_PASSWORD", None)

    # クライアント初期化時に認証情報を渡す
    async with MUFClient(
        unit_name="[unit_name]",
        host=redis_host,
        username=db_user,
        password=db_pass
    ) as client:
        # ハンドラの登録や監視ループの開始
        pass

if __name__ == "__main__":
    asyncio.run(main())

```

---

### 4. Redis ACL 定義の記述

`redis/users.acl` において、ユニットの役割に応じた権限を定義します。他のユニットからのリクエストを処理する「サービス型」と、自身の領域のみで完結する「標準型」でパターンを使い分けてください。

```text
# サービス型ユニット（システム全体の要求・応答を扱う場合）
user [unit_name] on >[password] ~muf/*/req/* ~muf/*/res/* ~muf/*/err/* ~muf/[unit_name]/* &* +@read +@write +@pubsub +@connection

# 標準型ユニット（自身の状態管理や特定のリクエストのみを行う場合）
user [unit_name] on >[password] ~muf/[unit_name]/* &* +@read +@write +@pubsub +@connection

```

---

### 5. 設定の反映と運用プロセス

全てのファイル設定が完了したら、まず `redis/users.acl` を保存した状態で `docker exec -it muf-redis redis-cli ACL LOAD` を実行して Redis の内部設定を即時リロードしてください。その後、対象となるユニットのコンテナを `docker compose restart` により再起動することで、新しい環境変数が読み込まれ ACL 認証が有効化されます。最後に `docker logs` を確認し、権限エラーが発生していないことを確認して導入完了となります。
