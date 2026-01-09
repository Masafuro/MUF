# muf/check_unit/main.py

import asyncio
import traceback
import sys
from muf import MUFClient
from redis.exceptions import AuthenticationError
from cases import test_state_management, test_echo_messaging, test_state_watching

async def run_check():
    """
    cases.py に定義されたテストを順次実行するメインスクリプトです。
    """
    print("==========================================")
    print(" MUF System Check Unit: Starting Tests")
    print("==========================================")

    try:
        # SDK側で環境変数を自動取得するため、認証情報は渡さずに初期化します
        async with MUFClient(unit_name="check-unit", host="muf-redis") as client:
            await test_state_management(client)
            await test_echo_messaging(client)
            await test_state_watching(client)
            await asyncio.sleep(0.5)

    except AuthenticationError:
        # check-unitでは方針通りトレースバックを表示せず、メッセージを出して異常終了させます
        print("\n[!] 認証エラー: Redisへのアクセスが拒否されました。")
        print("    環境変数 REDIS_USERNAME / REDIS_PASSWORD の設定を確認してください。")
        sys.exit(1)

    except Exception:
        print("\n[!] MUFClientの実行中に致命的なエラーが発生しました:")
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        print("\n==========================================")
        print(" MUF System Check: Process Finished")
        print("==========================================")

if __name__ == "__main__":
    try:
        asyncio.run(run_check())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        traceback.print_exc()
        sys.exit(1)