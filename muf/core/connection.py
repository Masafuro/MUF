# muf/core/connection.py

import redis.asyncio as redis
from typing import Optional, Any

class MUFConnection:
    """
    Redisとの非同期接続および基本的なデータ操作を管理するクラスです。
    ACL（ユーザー名とパスワードのペア）による認証に対応しています。
    """

    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 6379, 
                 db: int = 0, 
                 username: Optional[str] = None, 
                 password: Optional[str] = None):
        """
        初期化時には引数を保持するのみで、実際の接続は行いません。
        username や password が None の場合、Redisのデフォルトユーザーとして接続を試みます。
        """
        self.host = host
        self.port = port
        self.db = db
        self.username = username
        self.password = password
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """
        Redisサーバーへの非同期接続を確立します。
        このメソッドの実行時に、Redisサーバー側で認証が必要な場合は
        redis.exceptions.AuthenticationError が発生します。
        """
        if self.client is None:
            # redis.Redis クラスに username と password を引き渡します
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                username=self.username,
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
        未接続の場合は自動的に connect() を呼び出します。
        """
        if self.client is None:
            await self.connect()
        await self.client.set(key, value, ex=ttl)

    async def get(self, key: str) -> Optional[bytes]:
        """
        指定されたキーのデータを取得します。
        未接続の場合は自動的に connect() を呼び出します。
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