# MUF ユニット実装リファレンス (v2.0)

## 1. クライアントの初期化とコンテキスト管理

ユニット開発の基本は MUFClient のインスタンス化から始まります。非同期コンテキストマネージャを使用することで、Redisへの接続、バックグラウンドでの監視タスクであるWatcherの起動、および終了時のリソース解放といったライフサイクル管理がすべて自動化されます。

```python
import asyncio
from muf import MUFClient

async def run_unit():
    # ユニット名を指定して初期化します。内部で自動的に小文字化されます。
    async with MUFClient(unit_name="my-service", host="muf-redis") as client:
        # ここにメインロジックを記述します。
        print(f"Unit '{client.unit_name}' is now active.")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_unit())

```

## 2. バックエンド（リクエスト待機型）の実装

他ユニットからのリクエストを検知し、自動的にレスポンスを返すユニットの実装パターンです。client.listen に非同期ハンドラを渡すことで、パスの解析や応答の書き込みといったプロトコル制御をSDKに委譲できます。

```python
async def my_logic_handler(sender, msg_id, data):
    # 受信データはbytes型として渡されるため、必要に応じてデコードします。
    request_text = data.decode("utf-8")
    print(f"[*] Received from {sender}: {request_text}")
    
    # 処理結果をbytes型で返すと、SDKが自動で依頼元のresパスに応答を書き戻します。
    # ハンドラ内で例外が発生した場合は、自動的にerrステータスとして書き込まれます。
    result = f"Processed: {request_text}"
    return result.encode("utf-8")

async def main():
    async with MUFClient(unit_name="backend-unit", host="muf-redis") as client:
        # listenを実行するとシステム全体のreqの監視が開始されます。
        await client.listen(my_logic_handler)
        # ユニットを常駐させるために無限ループで待機します。
        while True:
            await asyncio.sleep(1)

```

## 3. フロントエンド（処理依頼型）の実装

特定のユニットに対して処理を依頼し、その結果を非同期で待機する実装パターンです。client.request を使用することで、一意なIDの生成からレスポンスの回収までを一括して非同期で行うことができます。

```python
async def call_service():
    async with MUFClient(unit_name="caller-unit", host="muf-redis") as client:
        try:
            # 指定したユニットに対してリクエストを送り、最大5秒間応答を待ちます。
            response = await client.request(
                target_unit="backend-unit",
                data=b"Hello MUF",
                timeout=5.0
            )
            print(f"Success: {response.decode('utf-8')}")
        except asyncio.TimeoutError:
            print("Error: The request timed out.")
        except RuntimeError as e:
            # 相手ユニット側で例外が発生し、errパスが生成された場合に発生します。
            print(f"Backend Error: {e}")

```

## 4. 状態の公開（keep）の実装

リクエストとレスポンスの枠組みを利用せずに、自身の現在の状態やパラメータを共有メモリ上に配置するパターンです。有効期限を長めに設定することで、システム全体で参照可能な定常データとして利用されます。

```python

async def publish_status():
    async with MUFClient(unit_name="sensor-unit", host="muf-redis") as client:
        # 自身の空間であるkeepディレクトリ配下にデータを配置します。
        # デフォルトのKEEP用TTLである3600秒が適用されます。
        await client.send(
            status="keep",
            message_id="temperature",
            data=b"25.5"
        )

```

## 5. 状態の参照と監視（データの取得）
- ※※※※令和8年1月6日時点　実装中※※※※

他ユニットが公開しているkeepなどの状態データを読み取るパターンです。一度だけ値を取得する単発取得と、値が更新されるたびに通知を受け取る継続監視の二種類が提供されています。

```python
async def observe_state():
    async with MUFClient(unit_name="observer", host="muf-redis") as client:
        # 単発取得：特定のユニットの現在の値を読み取ります。
        val = await client.get_state(target_unit="sensor-unit", message_id="temperature")
        if val:
            print(f"Current Value: {val.decode('utf-8')}")

        # 継続監視：値が更新された際に呼び出されるハンドラを定義します。
        async def on_change(unit, msg_id, data):
            print(f"[*] Update from {unit}: {msg_id} = {data.decode('utf-8')}")

        # 指定したパスの更新をリアルタイムに購読します。
        await client.watch_state(target_unit="sensor-unit", message_id="temperature", handler=on_change)
        while True:
            await asyncio.sleep(1)

```

## 6. 主要メソッドおよびステータス仕様

SDKが提供する主要なメソッドと、各ステータスにおけるデフォルトの有効期限は以下の通り定義されています。

[主要メソッド一覧]
- listen(handler): システム全体のリクエストを監視し、自動応答を実行します。
- request(target, data): 依頼を送信し、resまたはerrが返るまで非同期で待機します。
- send(status, id, data): 自身のディレクトリへ即座にデータを書き込みます。
- get_state(unit, id): 指定されたパスのデータを一度だけ取得します。
- watch_state(unit, id, h): 指定されたパスの更新をリアルタイムに購読します。

[ステータス定義とデフォルトTTL]
- req: リクエスト（処理依頼）。有効期限は10秒です。
- res: レスポンス（成功応答）。有効期限は60秒です。
- err: エラー（異常通知）。有効期限は60秒です。
- keep: ステート（状態保持）。有効期限は3600秒です。