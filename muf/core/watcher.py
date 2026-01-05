# muf/core/watcher.py

import asyncio
from typing import Callable, Dict, Optional, Awaitable
from redis.asyncio.client import PubSub
from .connection import MUFConnection
from ..protocol import naming

class MUFWatcher:
    """
    Keyspace Notificationsを監視し、イベントを各ハンドラや待機中のFutureへ配送するクラスです。
    """

    def __init__(self, connection: MUFConnection):
        self.connection = connection
        self._pubsub: Optional[PubSub] = None
        self._listen_task: Optional[asyncio.Task] = None
        # 特定のパス（RES等）の出現を待機しているFutureの管理
        self._waiters: Dict[str, asyncio.Future] = {}
        # 特定のパス接頭辞（REQ等）に対して実行する非同期ハンドラの管理
        self._handlers: Dict[str, Callable[[str], Awaitable[None]]] = {}

    async def start(self) -> None:
        """
        監視ループをバックグラウンドで開始します。
        """
        if self._listen_task is not None:
            return

        if self.connection.client is None:
            await self.connection.connect()

        self._pubsub = self.connection.get_client().pubsub()
        # プロトコルで定義された全てのMUFパス（ワイルドカード）を購読対象とする
        pattern = naming.build_keyspace_pattern(unit_name="*", status="*", message_id="*")
        await self._pubsub.psubscribe(pattern)
        
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def stop(self) -> None:
        """
        監視ループを停止し、PubSubリソースを解放します。
        """
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        if self._pubsub:
            await self._pubsub.punsubscribe()
            await self._pubsub.close()
            self._pubsub = None

    async def _listen_loop(self) -> None:
        """
        Redisからの通知を常時監視し、適切な配送を行う内部メインループです。
        """
        if self._pubsub is None:
            return

        while True:
            try:
                # ignore_subscribe_messages=Trueにより、購読成功時のメッセージをスキップ
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=None)
                if not message:
                    continue

                if message["type"] == "pmessage":
                    channel: bytes = message["channel"]
                    key_path = naming.get_key_from_channel(channel)
                    
                    # 1. 待機中のFuture（レスポンス待ち等）のチェック
                    if key_path in self._waiters:
                        future = self._waiters.pop(key_path)
                        if not future.done():
                            future.set_result(key_path)

                    # 2. 登録された汎用ハンドラ（リクエスト処理等）のチェック
                    for prefix, handler in self._handlers.items():
                        if key_path.startswith(prefix):
                            # ハンドラを別タスクで実行し、リスニングループのブロッキングを防ぐ
                            asyncio.create_task(handler(key_path))

            except asyncio.CancelledError:
                break
            except Exception:
                # 接続断などの例外時は短い待機を挟んで再開
                await asyncio.sleep(1)

    async def wait_for_key(self, path: str, timeout: float) -> bool:
        """
        指定されたパスのキーが生成されるのを非同期で待ちます。
        タイムアウト内に生成されればTrueを返し、そうでなければFalseを返します。
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._waiters[path] = future

        try:
            await asyncio.wait_for(future, timeout=timeout)
            return True
        except asyncio.TimeoutError:
            # タイムアウト時は待機リストから削除
            self._waiters.pop(path, None)
            return False

    def register_handler(self, prefix: str, handler: Callable[[str], Awaitable[None]]) -> None:
        """
        特定のパス接頭辞に合致するキーが生成された際のコールバックを登録します。
        """
        self._handlers[prefix] = handler