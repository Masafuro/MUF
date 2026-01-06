# check_unit/main.py

import asyncio
import traceback
import sys
from muf import MUFClient

async def run_check():
    """
    MUFシステムの各機能を順次テストし、結果を表示するチェックユニットのメインロジックです。
    エラー発生時には詳細なトレースバックを出力します。
    """
    print("==========================================")
    print(" MUF System Check Unit: Starting Tests")
    print("==========================================")

    try:
        # チェックユニットとしてクライアントを初期化
        async with MUFClient(unit_name="check-unit", host="muf-redis") as client:
            
            # 1. 共有メモリへの書き込みと単発取得のテスト (State Test)
            print("\n[Step 1] Testing State Management (Send/Get)...")
            try:
                test_data = b"system_ok_2026"
                await client.send(status="keep", message_id="health_check", data=test_data)
                
                retrieved = await client.get_state(target_unit="check-unit", message_id="health_check")
                if retrieved == test_data:
                    print(f"  Result: SUCCESS (Retrieved: {retrieved.decode()})")
                else:
                    print(f"  Result: FAILED (Expected {test_data}, got {retrieved})")
            except Exception:
                print("  Result: ERROR (Exception occurred in Step 1)")
                traceback.print_exc()

            # 2. 他ユニットへの処理依頼テスト (Messaging Test)
            print("\n[Step 2] Testing Request/Response with 'echo-service'...")
            try:
                request_content = b"muf_integration_test"
                response = await client.request(
                    target_unit="echo-service",
                    data=request_content,
                    timeout=5.0
                )
                print(f"  Result: SUCCESS (Echo Received: {response.decode()})")
            except asyncio.TimeoutError:
                print("  Result: FAILED (Request timed out. Is echo-service running?)")
            except Exception:
                print("  Result: ERROR (Exception occurred in Step 2)")
                traceback.print_exc()

            # 3. 継続監視のテスト (Watch Test)
            print("\n[Step 3] Testing State Watching...")
            try:
                watch_received = asyncio.Event()

                async def watch_handler(unit, msg_id, data):
                    print(f"  Notification Received: {unit}/{msg_id} = {data.decode()}")
                    watch_received.set()

                # 監視設定
                await client.watch_state(target_unit="check-unit", message_id="notify_test", handler=watch_handler)
                
                # データを書き込んで発火を確認
                await client.send(status="keep", message_id="notify_test", data=b"event_triggered")
                
                await asyncio.wait_for(watch_received.wait(), timeout=3.0)
                print("  Result: SUCCESS (Event handler executed)")
            except asyncio.TimeoutError:
                print("  Result: FAILED (Watch handler was not called)")
            except Exception:
                print("  Result: ERROR (Exception occurred in Step 3)")
                traceback.print_exc()

            # シャットダウン時のエラー（Task exception was never retrieved）を抑制するための猶予
            # バックグラウンドタスクが終了を検知する時間を与えます
            await asyncio.sleep(0.5)

    except Exception:
        print("\n[!] A critical error occurred during the MUFClient context:")
        traceback.print_exc()
    finally:
        print("\n==========================================")
        print(" MUF System Check: Process Finished")
        print("==========================================")

if __name__ == "__main__":
    try:
        asyncio.run(run_check())
    except KeyboardInterrupt:
        # 手動停止時には静かに終了する
        sys.exit(0)
    except Exception:
        # プログラム全体の予期せぬクラッシュを捕捉
        traceback.print_exc()
        sys.exit(1)