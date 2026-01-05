# terminal/main.py

import asyncio
from muf import MUFClient, STATUS_REQ, STATUS_RES, STATUS_ERR, STATUS_KEEP
from muf.protocol import naming

async def get_user_input(prompt: str) -> str:
    """非同期で入力を受け取るためのヘルパー"""
    return await asyncio.to_thread(input, prompt)

async def main():
    REDIS_HOST = "muf-redis"

    print("========================================")
    print("      MUF Advanced Debug Terminal       ")
    print("========================================\n")

    # 最初にユニット名を入力
    initial_unit_name = await get_user_input("Enter Your Unit Name (Identity) > ")
    unit_name = initial_unit_name.strip() or "terminal-unit"

    try:
        async with MUFClient(unit_name=unit_name, host=REDIS_HOST) as client:
            print(f"\n[Logged in as: {unit_name}]")
            print("Status Options: REQ, RES, ERR, KEEP")
            print("Type 'exit' to quit.\n")

            while True:
                # 1. ステータスの選択
                status_input = await get_user_input(f"[{unit_name}] Command > ")
                status = status_input.upper().strip()
                
                if status in ["EXIT", "QUIT"]:
                    break
                if not status:
                    continue
                if status not in [STATUS_REQ, STATUS_RES, STATUS_ERR, STATUS_KEEP]:
                    print("Invalid status. (Choose: REQ, RES, ERR, KEEP)")
                    continue

                # 2. キー名（ID）の入力
                msg_id = await get_user_input(f"[{unit_name}] Key Name (ID) > ")
                if not msg_id.strip():
                    print("ID cannot be empty.")
                    continue

                # 3. 送信データの入力
                payload = await get_user_input(f"[{unit_name}] Data > ")
                
                print(f"Action: Posting to MUF/{unit_name}/{status}/{msg_id}")

                try:
                    # データの送信
                    await client.send(
                        status=status,
                        message_id=msg_id,
                        data=payload.encode("utf-8")
                    )
                    print("Status: Sent successfully.")

                    # REQの場合はレスポンスを待機
                    if status == STATUS_REQ:
                        print(f"Waiting for response to {msg_id} (10s timeout)...")
                        
                        res_path = naming.build_path(unit_name, STATUS_RES, msg_id)
                        err_path = naming.build_path(unit_name, STATUS_ERR, msg_id)
                        
                        wait_res = asyncio.create_task(client.watcher.wait_for_key(res_path, timeout=10.0))
                        wait_err = asyncio.create_task(client.watcher.wait_for_key(err_path, timeout=10.0))
                        
                        done, pending = await asyncio.wait(
                            [wait_res, wait_err],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        for task in pending:
                            task.cancel()

                        if wait_res.done() and wait_res.result():
                            res_data = await client.connection.get(res_path)
                            print(f"✅ Response: {res_data.decode('utf-8') if res_data else '(Empty)'}")
                        elif wait_err.done() and wait_err.result():
                            err_data = await client.connection.get(err_path)
                            print(f"❌ Error: {err_data.decode('utf-8') if err_data else '(Empty)'}")
                        else:
                            print("⏰ Status: [Timeout]")

                except Exception as e:
                    print(f"⚠️ Failed: {e}")
                
                print("-" * 30)

    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass