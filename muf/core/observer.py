import threading
import sys

class MUFObserver:
    """
    共有メモリの更新イベントを購読し、通知を行うクラス。
    ワイルドカード（* や ?）によるパターン監視に対応しています。
    """
    def __init__(self, connector):
        self.connector = connector
        # connector側のRedisインスタンスで decode_responses=True が設定されていることを想定
        self.pubsub = self.connector.r.pubsub()
        self.callbacks = {}

    def observe(self, path: str, callback):
        """
        特定のパス、またはパターン（muf/* 等）の更新を監視します。
        """
        channel = f"__keyspace@0__:{path}"
        
        # 既に同じパス・パターンで購読を開始しているか確認
        if channel not in self.callbacks:
            self.callbacks[channel] = []
            # Redisのpsubscribeを使用してパターン監視を開始
            # **{channel: self._handle_event} の形式で、このパターン専用のハンドラを登録
            self.pubsub.psubscribe(**{channel: self._handle_event})
        
        self.callbacks[channel].append(callback)

        # 監視用のスレッドを開始（未開始、または停止している場合）
        if not hasattr(self, 'thread') or not self.thread.is_alive():
            # sleep_timeを適切に設定し、レスポンス性を確保
            self.thread = self.pubsub.run_in_thread(sleep_time=0.01, daemon=True)

    def _handle_event(self, message):
        """
        Redisからの通知を解析し、合致したパターンの全コールバックを実行します。
        """
        # psubscribeの場合、message['pattern'] に登録時のパターン（__keyspace@0__:muf/* 等）が入る
        # message['channel'] には実際に変更された具体的なキー（__keyspace@0__:muf/hiyoko 等）が入る
        pattern_channel = message.get('pattern')
        actual_channel = message.get('channel')

        if not pattern_channel or not actual_channel:
            return

        # Redisのレスポンスがバイト列の場合は文字列に変換
        if isinstance(pattern_channel, bytes):
            pattern_channel = pattern_channel.decode('utf-8')
        if isinstance(actual_channel, bytes):
            actual_channel = actual_channel.decode('utf-8')

        # 実際に変更があった具体的なパス名を抽出
        try:
            actual_path = actual_channel.split(':', 1)[1]
        except IndexError:
            return

        # 登録されたパターンに紐づくすべてのコールバックを呼び出し
        # 引数には「実際に変更があった具体的なパス」を渡す
        if pattern_channel in self.callbacks:
            for cb in self.callbacks[pattern_channel]:
                try:
                    cb(actual_path)
                except Exception as e:
                    print(f"Error in MUFObserver callback for {actual_path}: {e}", file=sys.stderr)