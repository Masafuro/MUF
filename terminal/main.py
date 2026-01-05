# terminal/main.py

import asyncio
import sys
from muf import MUFClient
from muf.protocol import naming, constants

async def main():
    REDIS_HOST = "muf-redis"
    
    # ターミナル自体のアイデンティティは最小限に定義
    client = MUFClient(unit_name="terminal-operator", host=REDIS_HOST)
    
    print("MUF Memory Portal")
    print("Format: [path] [data]")
    print("Example: MUF/sensor-01/REQ/msg-100 25.5")
    print("Type 'exit' to quit.\n")

    try:
        await client.connection.connect()
        
        while True:
            # 非同期で標準入力を監視
            line = await asyncio.to_thread(input, "MUF > ")
            line = line.strip()
            
            if not line:
                continue
            if line.lower() in ["exit", "quit"]:
                break

            # スペースでパスとデータを分離
            parts = line.split(maxsplit=1)
            path = parts[0]
            payload = parts[1] if len(parts) > 1 else ""

            try:
                # パスを解析してステータスに応じたTTLを決定
                _, status, _ = naming.parse_path(path)
                
                ttl_map = {
                    constants.STATUS_REQ: constants.DEFAULT_TTL_REQ,
                    constants.STATUS_RES: constants.DEFAULT_TTL_RES,
                    constants.STATUS_ERR: constants.DEFAULT_TTL_ERR,
                    constants.STATUS_KEEP: constants.DEFAULT_TTL_KEEP
                }
                ttl = ttl_map.get(status, constants.DEFAULT_TTL_RES)

                # 指定されたパスへ直接書き込み（待機なし）
                await client.connection.set_ex(path, payload.encode("utf-8"), ttl)
                print(f"Posed: {path} (TTL: {ttl}s)")

            except Exception as e:
                print(f"Error: {e}")

    except Exception as e:
        print(f"Connection Error: {e}")
    finally:
        await client.connection.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass