# echo_unit/main.py

import asyncio
from muf import MUFClient

async def echo_handler(sender, msg_id, data):
    """
    リクエストを検知した際に呼び出されるバックエンドロジックです。
    受け取ったデータをデコードし、内容を確認した上でそのまま返却します。
    """
    try:
        # 届くデータはbytes型であることを前提にデコードします
        message = data.decode("utf-8")
        print(f"[*] Echo Logic: From={sender}, ID={msg_id}, Content='{message}'")
        
        # 応答データの作成（受け取った内容にプレフィックスを付与）
        response_content = f"Echo: {message}"
        
        # bytes型で返却することで、SDKが自動的に muf/{sender}/res/{msg_id} へ書き込みます
        return response_content.encode("utf-8")
        
    except Exception as e:
        # ここで例外を発生させると、SDKのlistenメソッドがキャッチし、
        # 自動的に muf/{sender}/err/{msg_id} へエラーメッセージを書き込みます
        print(f"[!] Error in echo_handler: {e}")
        raise

async def main():
    """
    ユニットのメインエントリポイントです。
    非同期コンテキストマネージャにより、接続と監視ループの開始・停止を自動管理します。
    """
    # 接続先をDockerネットワーク内の 'muf-redis' に指定
    # ユニット名は大文字を含んでもSDK内部で小文字に正規化されます
    async with MUFClient(unit_name="echo-service", host="muf-redis") as client:
        print("==========================================")
        print(" MUF Echo Unit: Listening for Requests")
        print(" Status: Ready (Case-Insensitive Mode)")
        print("==========================================")
        
        # システム全体のリクエスト（muf/*/req/*）を監視対象としてハンドラを登録
        # dispatcher.py の fnmatch により、ワイルドカードが正常に機能します
        await client.listen(echo_handler)
        
        # ユニットを常駐させるための待機ループ
        # watcherのlisten_loopは別タスクで動いているため、メインスレッドを維持します
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("[*] Echo Unit is shutting down...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 手動停止時のクリーンアップ
        pass