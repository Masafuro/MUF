# muf/core/connection.py

import redis.asyncio as redis
from typing import Optional, Any

class MUFConnection:
    """
    Redisとの非同期接続および基本的なデータ操作を管理するクラスです。
    """

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """
        Redisサーバーへの非同期接続を確立します。
        コネクションプールは redis-py によって内部的に管理されます。
        """
        if self.client is None:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=False  # データ本体はバイナリとして扱うためデコードしない
            )

    async def disconnect(self) -> None:
        """
        Redis接続を安全に閉じます。
        """
        if self.client:
            await self.client.close()
            self.client = None

    async def set_ex(self, key: str, value: bytes, ttl: int) -> None:
        """
        指定されたTTL（有効期限）付きでデータを書き込みます。
        """
        if self.client is None:
            await self.connect()
        await self.client.set(key, value, ex=ttl)

    async def get(self, key: str) -> Optional[bytes]:
        """
        指定されたキーのデータを取得します。
        """
        if self.client is None:
            await self.connect()
        return await self.client.get(key)

    def get_client(self) -> redis.Redis:
        """
        高度な操作（Pub/Subなど）のためにRedisクライアントインスタンスを直接提供します。
        """
        if self.client is None:
            raise RuntimeError("Redis client is not connected. Call connect() first.")
        return self.client