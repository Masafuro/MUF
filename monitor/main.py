# monitor/main.py

import asyncio
import os
import sys
import traceback
import redis.asyncio as redis
from redis.exceptions import AuthenticationError
from muf.protocol import naming

async def monitor():
    REDIS_HOST = "muf-redis"
    BASE_PATTERN = "muf/*"
    SUBSCRIBE_PATTERN = f"__keyspace@0__:{BASE_PATTERN}"
    
    db_user = os.getenv("REDIS_USERNAME", None)
    db_pass = os.getenv("REDIS_PASSWORD", None)
    
    r = redis.Redis(
        host=REDIS_HOST, 
        username=db_user,
        password=db_pass,
        decode_responses=True
    )
    
    pubsub = r.pubsub()
    
    print("==============================================================================")
    print(" MUF Logic Monitor: Observing Memory Space Transitions")
    print(f" User: {db_user if db_user else 'default'}")
    print(f" Status: Active (Subscribed to {BASE_PATTERN})")
    print("==============================================================================\n")

    try:
        # 権限チェックはここで行われます
        await pubsub.psubscribe(SUBSCRIBE_PATTERN)

        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue
            
            event = message["data"]
            channel = message["channel"]
            path = channel.split(":", 1)[1]
            
            print(f"DEBUG: Received [{event}] on {path}")
            
            try:
                unit, status, msg_id = naming.parse_path(path)
                
                if event in ["set", "expired", "del"]:
                    display_data = ""
                    if event == "set":
                        val = await r.get(path)
                        display_data = f"DATA: {val}"
                    else:
                        display_data = f"--- {event.upper()} ---"
                        
                    print(f"[{status.lower():^6}] {unit:<15} | ID: {msg_id:<12} | {display_data}")
                    
            except Exception:
                # 解析エラー時もトレースバックを表示して詳細を確認できるようにします
                print(f"  └─ Parse Error (Path might not follow MUF rules)")
                traceback.print_exc()
                continue
                
    except AuthenticationError:
        print("\n[!] 認証エラーが発生しました:")
        traceback.print_exc()
    except asyncio.CancelledError:
        await pubsub.punsubscribe(SUBSCRIBE_PATTERN)
    except Exception:
        print("\n[!] 実行中に予期しないエラーが発生しました:")
        traceback.print_exc()
    finally:
        await r.aclose()

if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()