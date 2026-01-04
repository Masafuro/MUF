from .core.connector import MUFConnector
from .core.observer import MUFObserver
from .protocol.sync_access import SyncAccess
from .protocol.handler import Handler

class MUF:
    """
    Memory Unit Framework (MUF) SDK のメインクラス。
    共有メモリを介した分散連携のすべての機能を集約します。
    """
    def __init__(self, host='localhost', port=6379, db=0):
        # 基盤レイヤーの初期化
        self._connector = MUFConnector(host=host, port=port, db=db)
        self._observer = MUFObserver(self._connector)
        
        # プロトコルレイヤーの初期化
        self._sync_access = SyncAccess(self._connector, self._observer)
        self._handler = Handler(self._connector, self._observer)

    def get(self, path, data, timeout=5.0):
        """
        指定されたパスにデータを書き込み、同期的に回答を取得します。
        内部でリクエストIDの生成とフラグ監視を自動的に行います。
        """
        return self._sync_access.get(path, data, timeout=timeout)

    def listen(self, path, callback):
        """
        指定されたパスを監視し、要求が届いた際に関数を実行して回答を返します。
        PLCの割り込みタスクのように、イベント駆動で動作します。
        """
        return self._handler.listen(path, callback)