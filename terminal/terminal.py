import os
import sys
import time
from muf import MUF

def main():
    # 環境変数からRedisの接続情報を取得
    redis_host = os.getenv("REDIS_HOST", "muf-redis")
    sdk = MUF(host=redis_host)

    print("========================================")
    print("      MUF Terminal Unit Ready          ")
    print("========================================")
    print("Type 'exit' or 'quit' to stop.")
    print("Format: <path> <data>")
    print("----------------------------------------")

    while True:
        try:
            user_input = input("MUF Terminal > ").strip()
            
            if not user_input:
                continue
            
            # exit/quit でプロセスごと確実に終了させる
            if user_input.lower() in ['exit', 'quit']:
                print("Shutting down terminal...")
                sys.exit(0)

            parts = user_input.split(maxsplit=1)
            if len(parts) < 2:
                print("Error: Invalid format. Use '<path> <data>'")
                continue

            target_path, send_data = parts
            print(f"[*] Sending request to [{target_path}]...")

            try:
                # タイムアウトを短め（5秒）に設定してテストしやすくします
                result = sdk.get(target_path, send_data, timeout=5.0)
                print(f"[+] Response received: {result}")
            except TimeoutError:
                print("[-] Error: Request timed out. No responder unit found.")
                print("    (Note: req_flag remains '1' until cleared)")
            except Exception as e:
                print(f"[-] Unexpected error: {e}")
                print("    (Check if a previous request is still pending)")

        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            sys.exit(0)

if __name__ == "__main__":
    main()