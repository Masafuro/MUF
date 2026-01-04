from typing import Callable, Any

class Handler:
    """
    共有メモリ上のリクエストを監視し、登録された関数を実行するバックエンド用クラス。
    """
    def __init__(self, connector, observer):
        self.connector = connector
        self.observer = observer

    def listen(self, path: str, callback: Callable[[Any], Any]):
        """
        指定されたパスを監視し、要求フラグ（req_flag）が1になったら関数を実行します。
        """
        def on_change(changed_path: str):
            # 現在のメモリの状態を確認
            current_state = self.connector.get_hash_all(changed_path)
            
            # 要求フラグが「1」かつ、まだ回答していない（ans_flag=0）状態を検知
            if (current_state.get("req_flag") == "1" and 
                current_state.get("ans_flag") == "0"):
                
                # リクエストデータの取り出し
                req_data = current_state.get("req_data")
                req_id = current_state.get("req_id")

                try:
                    # ユーザー定義の処理を実行
                    ans_data = callback(req_data)
                    
                    # 処理結果と完了フラグ（ans_flag=1）を書き込む
                    # これにより待機中のクライアントSDKが目覚める
                    self.connector.set_hash(changed_path, {
                        "ans_data": str(ans_data),
                        "ans_flag": "1"
                    })
                except Exception as e:
                    # エラー発生時もフラグを立てつつ、エラー内容を戻す
                    self.connector.set_hash(changed_path, {
                        "ans_data": f"Error: {str(e)}",
                        "ans_flag": "1"
                    })

        # coreレイヤーのobserverを使用して監視を開始
        self.observer.observe(path, on_change)