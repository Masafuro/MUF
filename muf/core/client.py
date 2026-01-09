# muf/core/client.py

import os
from typing import Optional, Callable, Awaitable
from .connection import MUFConnection
from .watcher import MUFWatcher
from .state import MUFStateManager
from .messaging import MUFMessenger

class MUFClient:
    """
    MUFプロトコルの全ての機能を集約したメインクライアントです。
    引数または環境変数から自動的にACL認証情報を取得し、セキュアな通信を確立します。
    """
    def __init__(self, 
                 unit_name: str, 
                 host: str = "localhost", 
                 port: int = 6379, 
                 db: int = 0, 
                 username: Optional[str] = None, 
                 password: Optional[str] = None):
        """
        クライアントを初期化します。
        引数が指定されない場合は、環境変数 REDIS_USERNAME / REDIS_PASSWORD を参照します。
        どちらも存在しない場合はデフォルトユーザーとして接続を試みます。
        """
        self.unit_name = unit_name.lower()
        
        # 認証情報の解決ロジック：引数を優先し、なければ環境変数を採用
        effective_user = username or os.getenv("REDIS_USERNAME")
        effective_pass = password or os.getenv("REDIS_PASSWORD")

        # 解決された認証情報を下層の通信レイヤーへ伝達
        self.connection = MUFConnection(
            host=host, 
            port=port, 
            db=db, 
            username=effective_user, 
            password=effective_pass
        )
        self.watcher = MUFWatcher(self.connection)
        
        # 各マネージャーコンポーネントの初期化
        self.state = MUFStateManager(self.connection, self.watcher)
        self.messenger = MUFMessenger(self.connection, self.watcher, self.state)
        self._is_running = False

    async def start(self) -> None:
        """
        Redisへの物理接続を開始します。
        このタイミングで環境変数や引数の認証情報の妥当性がRedisサーバーによって検証されます。
        """
        if self._is_running: return
        await self.connection.connect()
        await self.watcher.start()
        self._is_running = True

    async def stop(self) -> None:
        """
        監視タスクを停止し、接続を安全にクローズします。
        """
        if not self._is_running: return
        await self.watcher.stop()
        await self.connection.disconnect()
        self._is_running = False

    async def __aenter__(self):
        """非同期コンテキストマネージャのエントリポイントです。"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャのイグジットポイントです。"""
        await self.stop()

    # --- 高度な機能を各マネージャーへ委譲するメソッド群 ---

    async def send(self, status: str, message_id: str, data: bytes, ttl: Optional[int] = None) -> str:
        """指定したステータスでデータを書き込みます。"""
        return await self.state.send(self.unit_name, status, message_id, data, ttl)

    async def request(self, target_unit: str, data: bytes, timeout: float = 10.0) -> bytes:
        """特定のユニットに対してリクエストを送信し、応答を待ちます。"""
        return await self.messenger.request(self.unit_name, target_unit, data, timeout)

    async def listen(self, handler: Callable[[str, str, bytes], Awaitable[Optional[bytes]]]) -> None:
        """自分宛てのリクエストを監視し、ハンドラで応答を処理します。"""
        await self.messenger.listen(handler)

    async def get_state(self, target_unit: str, message_id: str, status: str = "keep") -> Optional[bytes]:
        """他ユニットの特定の状態を一度だけ取得します。"""
        return await self.state.get_state(target_unit, message_id, status)

    async def watch_state(self, target_unit: str, message_id: str, handler: Callable[[str, str, bytes], Awaitable[None]], status: str = "keep") -> None:
        """他ユニットの状態変化をリアルタイムで購読します。"""
        await self.state.watch_state(target_unit, message_id, handler, status)