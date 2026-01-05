# MUF ユニット開発実装リファレンス (v2.0)

## 1. クライアントの初期化とコンテキスト管理

ユニット開発の基本は MUFClient のインスタンス化から始まります。非同期コンテキストマネージャを使用することで、Redisへの接続、バックグラウンドでの監視タスク（Watcher）の起動、および終了時のクリーンアップが自動化されます。
```Python
import asyncio
from muf import MUFClient

async def run_unit():
    # ユニット名（unit_name）を指定して初期化します
    # 内部で自動的に小文字化されるため、大文字混じりの指定も可能です
    async with MUFClient(unit_name="my-service", host="muf-redis") as client:
        # ここにメインロジックを記述します
        print(f"Unit '{client.unit_name}' is now active.")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_unit())
```

## 2. バックエンド（リクエスト待機型）の実装

他ユニットからのリクエスト（req）を検知し、自動的にレスポンス（res）を返すユニットの実装パターンです。client.listen にハンドラを渡すことで、パスのパースや応答の書き込みをSDKに委譲できます。
```Python
async def my_logic_handler(sender, msg_id, data):
    """
    リクエスト検知時に実行される非同期ハンドラ
    sender: 依頼元ユニット名, msg_id: メッセージID, data: 受信データ(bytes)
    """
    # 1. 受信データのデコード
    request_text = data.decode("utf-8")
    
    # 2. ビジネスロジックの実行
    print(f"[*] Received from {sender}: {request_text}")
    result = f"Processed: {request_text}"
    
    # 3. 戻り値として bytes を返すと、SDKが自動で muf/{sender}/res/{msg_id} に書き込みます
    # ハンドラ内で例外が発生した場合は、自動的に err ステータスで書き込まれます
    return result.encode("utf-8")

async def main():
    async with MUFClient(unit_name="backend-unit", host="muf-redis") as client:
        # listenを実行すると、システム全体の req (muf/*/req/*) の監視が始まります
        await client.listen(my_logic_handler)
        
        # ユニットを常駐させるために待機します
        while True:
            await asyncio.sleep(1)
```

## 3. フロントエンド（処理依頼型）の実装

特定のユニットに対して処理を依頼し、その結果を非同期で待機する実装パターンです。client.request を使用することで、UUIDの生成からレスポンスの回収までを一括して行えます。

```Python
async def call_service():
    async with MUFClient(unit_name="caller-unit", host="muf-redis") as client:
        try:
            # target_unit の空間に対してリクエストを投げ、最大5秒待機します
            # 内部では muf/caller-unit/req/[UUID] が生成されます
            response = await client.request(
                target_unit="backend-unit",
                data=b"Hello MUF",
                timeout=5.0
            )
            print(f"Success: {response.decode('utf-8')}")
            
        except asyncio.TimeoutError:
            print("Error: The request timed out.")
        except RuntimeError as e:
            # 相手ユニットが例外を投げ、errパスにデータが書き込まれた場合に発生します
            print(f"Backend Error: {e}")
```

## 4. 単方向の状態通知（keep）の実装

リクエスト・レスポンスの枠組みを使わずに、自身の状態やパラメータを共有メモリ上に配置するパターンです。TTL（有効期限）を長めに設定することで、定常的な監視データとして利用できます。
```Python
async def publish_status():
    async with MUFClient(unit_name="sensor-unit", host="muf-redis") as client:
        # 自身の空間 muf/sensor-unit/keep/cpu_usage にデータを配置します
        # デフォルトのKEEP用TTL（3600秒）が適用されます
        await client.send(
            status="keep",
            message_id="cpu_usage",
            data=b"45%"
        )
```
## 5. SDK主要メソッドと通信ステータス仕様

SDKが提供する主要なメソッドの役割と、各ステータスに紐付くデフォルトの有効期限（TTL）を以下の表にまとめました。

|メソッド名|主な役割|推奨されるステータス|
|---|---|---|
|listen(handler)|システム全体のリクエストを監視し、自動応答する。|req (受信) / res (送信)|
|request(target, data)|依頼を投げ、結果（res/err）が返るまで非同期で待機する。|req (送信) / res (受信)|
|send(status, id, data)|任意のステータスでデータを即座に共有メモリへ配置する。|keep, res, err|

|ステータス名|意味|デフォルトTTL|
|---|---|---|
|req|リクエスト（処理依頼）|10秒|
|res|レスポンス（成功応答）|60秒|
|err|エラー（異常通知）|60秒|
|keep|ステート（状態保持）|3600秒|