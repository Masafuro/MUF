import threading

class MUFObserver:
    """
    共有メモリの更新イベントを購読し、通知を行うクラス。
    """
    def __init__(self, connector):
        self.connector = connector
        self.pubsub = self.connector.r.pubsub()
        self.callbacks = {}

    def observe(self, path: str, callback):
        """
        特定のキーパスの更新を監視し、変化時にコールバックを実行します。
        """
        # RedisのKeyspace Notificationチャンネルを構築
        # __keyspace@0__:<path> はキーに対する全ての操作を通知します
        channel = f"__keyspace@0__:{path}"
        self.pubsub.psubscribe(**{channel: self._handle_event})
        
        if path not in self.callbacks:
            self.callbacks[path] = []
        self.callbacks[path].append(callback)

        # 監視用のスレッドを開始（未開始の場合）
        if not hasattr(self, 'thread') or not self.thread.is_alive():
            self.thread = self.pubsub.run_in_thread(sleep_time=0.01)

    def _handle_event(self, message):
        """
        Redisからの通知を受け取り、対応するパスのコールバックを呼び出します。
        """
        # メッセージから対象のキーパスを抽出
        channel = message['channel']
        path = channel.split(':', 1)[1]
        
        if path in self.callbacks:
            for cb in self.callbacks[path]:
                cb(path)