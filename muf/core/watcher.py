# muf/core/watcher.py

import asyncio
from typing import Callable, Optional, Awaitable, Any
from redis.asyncio.client import PubSub
from .connection import MUFConnection
from .dispatcher import MUFEventDispatcher
from ..protocol import naming

class MUFWatcher:
    """
    RedisとのPubSub接続を管理し、待機ループを実行するクラスです。
    実質的な配送処理は MUFEventDispatcher に委譲します。
    """
    def __init__(self, connection: MUFConnection):
        self.connection = connection
        self.dispatcher = MUFEventDispatcher()
        self._pubsub: Optional[PubSub] = None
        self._listen_task: Optional[asyncio.Task] = None

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
        # 内部で __keyspace@0__:muf/*/*/* のようなパターンが構築されます
        pattern = naming.build_keyspace_pattern("*", "*", "*")
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
        Redisからの通知を常時監視し、Dispatcherに配送する内部ループです。
        """
        if self._pubsub is None:
            return

        while True:
            try:
                # ignore_subscribe_messages=Trueにより、購読成功時のメッセージをスキップ
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=None)
                if not message or message["type"] != "pmessage":
                    continue

                # チャンネル名からキーパスを抽出
                # naming.get_key_from_channelはbytes/strの両方を処理できるよう修正済みです
                channel = message["channel"]
                key_path = naming.get_key_from_channel(channel)
                
                # 実質的なパターンマッチングと配送処理はDispatcherが行います
                self.dispatcher.handle_event(key_path)

            except asyncio.CancelledError:
                break
            except Exception as e:
                # 接続断などの例外時はログを出力して短い待機を挟んで再開します
                print(f"DEBUG: Watcher loop error: {e}")
                await asyncio.sleep(1)

    async def wait_for_key(self, path: str, timeout: float) -> bool:
        """
        Dispatcherを介して特定のパスの出現を非同期で待ちます。
        """
        future = self.dispatcher.add_waiter(path)
        try:
            await asyncio.wait_for(future, timeout=timeout)
            return True
        except asyncio.TimeoutError:
            self.dispatcher.remove_waiter(path)
            return False

    def register_handler(self, pattern: str, handler: Callable[[str], Awaitable[None]]) -> None:
        """
        Dispatcherに特定のパターンに対するハンドラを登録します。
        """
        self.dispatcher.add_handler(pattern, handler)