# monitor/main.py

import asyncio
import redis.asyncio as redis
from muf.protocol import naming

async def monitor():
    REDIS_HOST = "muf-redis"
    BASE_PATTERN = "muf/*"
    SUBSCRIBE_PATTERN = f"__keyspace@0__:{BASE_PATTERN}"
    
    r = redis.Redis(host=REDIS_HOST, decode_responses=True)
    pubsub = r.pubsub()
    
    print("==============================================================================")
    print(" MUF Logic Monitor: Observing Memory Space Transitions")
    print(f" Status: Active (Subscribed to {BASE_PATTERN})")
    print("==============================================================================\n")

    await pubsub.psubscribe(SUBSCRIBE_PATTERN)

    try:
        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue
            
            event = message["data"]
            channel = message["channel"]
            # チャンネル名からキーパスを抽出 (__keyspace@0__:muf/p/req/s1)
            path = channel.split(":", 1)[1]
            
            # デバッグ行：解析前に必ず受信したことを知らせる
            print(f"DEBUG: Received [{event}] on {path}")
            
            try:
                # パス解析（ここが失敗しても上のデバッグ行は動く）
                unit, status, msg_id = naming.parse_path(path)
                
                if event in ["set", "expired", "del"]:
                    display_data = ""
                    if event == "set":
                        val = await r.get(path)
                        display_data = f"DATA: {val}"
                    else:
                        display_data = f"--- {event.upper()} ---"
                        
                    print(f"[{status.lower():^6}] {unit:<15} | ID: {msg_id:<12} | {display_data}")
                    
            except Exception as e:
                # 解析エラーの内容も表示するように変更
                print(f"  └─ Parse Error: {e} (Path might not follow MUF rules)")
                continue
                
    except asyncio.CancelledError:
        await pubsub.punsubscribe(SUBSCRIBE_PATTERN)
    finally:
        # 警告が出ていた close を aclose に変更
        await r.aclose()

if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        pass