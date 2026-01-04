import uuid
import threading
from typing import Any, Optional

class SyncAccess:
    """
    共有メモリを介した同期的なデータ取得（GETシーケンス）を管理するクラス。
    """
    def __init__(self, connector, observer):
        self.connector = connector
        self.observer = observer

    def get(self, path: str, data: Any, timeout: float = 5.0) -> Any:
        """
        指定されたパスにリクエストを書き込み、回答が返ってくるまで待機します。
        """
        # 1. リクエストの一意性を保証するためのIDを生成
        request_id = str(uuid.uuid4())
        # 待機を制御するためのスレッドセーフなイベントオブジェクト
        response_event = threading.Event()
        result_container = {"data": None, "error": None}

        def on_change(changed_path: str):
            """
            監視対象のパスに変化があった際に呼び出されるコールバック。
            """
            # 現在のハッシュ状態を全取得して確認
            current_state = self.connector.get_hash_all(changed_path)
            
            # 自分のリクエストに対する回答（ans_flag=1）かつIDが一致するかを検証
            if (current_state.get("ans_flag") == "1" and 
                current_state.get("req_id") == request_id):
                result_container["data"] = current_state.get("ans_data")
                response_event.set()  # 待機を解除

        # 2. 監視の開始
        self.observer.observe(path, on_change)

        # 3. リクエストデータの書き込み（アトミック操作）
        # この瞬間にバックエンドユニットが反応可能になる
        write_success = self.connector.set_hash(path, {
            "req_id": request_id,
            "req_flag": "1",
            "req_data": str(data),
            "ans_flag": "0"
        })

        if not write_success:
            raise ConnectionError("Failed to write request to shared memory.")

        # 4. 回答が来るかタイムアウトするまでブロック
        completed = response_event.wait(timeout=timeout)

        if not completed:
            raise TimeoutError(f"MUF Request timed out for path: {path}")

        return result_container["data"]