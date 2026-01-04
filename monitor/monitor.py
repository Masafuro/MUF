import os
import time
from muf import MUF

def display_state(path, data):
    print(f"\n--- Current State: {path} ---")
    if not data:
        print("Empty")
        return
    for key, value in data.items():
        print(f"  {key.ljust(15)}: {value}")
    print("-" * (len(path) + 25))

def main():
    # 環境変数から設定を読み込み
    redis_host = os.getenv("REDIS_HOST", "muf-redis")
    target_path = os.getenv("TARGET_PATH", "muf/test/unit")
    
    # SDKの初期化
    sdk = MUF(host=redis_host)
    
    print(f"Starting Monitor Unit for path: {target_path}")
    
    # 最初に全データをダンプして表示
    initial_data = sdk._connector.get_hash_all(target_path)
    display_state(target_path, initial_data)
    
    # 変更を監視するコールバック
    def on_change(path):
        # 変更後の最新データを取得
        current_data = sdk._connector.get_hash_all(path)
        display_state(path, current_data)

    # 監視開始
    sdk._observer.observe(target_path, on_change)
    
    # メインスレッドを維持
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Monitor stopped.")

if __name__ == "__main__":
    main()