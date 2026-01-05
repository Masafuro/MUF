# muf/core/client.py

from typing import Optional, Callable, Awaitable
from .connection import MUFConnection
from .watcher import MUFWatcher
from .state import MUFStateManager
from .messaging import MUFMessenger

class MUFClient:
    """
    MUFプロトコルの全ての機能を集約したメインクライアントです。
    """
    def __init__(self, unit_name: str, host: str = "localhost", port: int = 6379, db: int = 0):
        self.unit_name = unit_name.lower()
        self.connection = MUFConnection(host=host, port=port, db=db)
        self.watcher = MUFWatcher(self.connection)
        
        # マネージャーの初期化
        self.state = MUFStateManager(self.connection, self.watcher)
        self.messenger = MUFMessenger(self.connection, self.watcher, self.state)
        self._is_running = False

    async def start(self) -> None:
        if self._is_running: return
        await self.connection.connect()
        await self.watcher.start()
        self._is_running = True

    async def stop(self) -> None:
        if not self._is_running: return
        await self.watcher.stop()
        await self.connection.disconnect()
        self._is_running = False

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    # 既存メソッドの委譲
    async def send(self, status: str, message_id: str, data: bytes, ttl: Optional[int] = None) -> str:
        return await self.state.send(self.unit_name, status, message_id, data, ttl)

    async def request(self, target_unit: str, data: bytes, timeout: float = 10.0) -> bytes:
        return await self.messenger.request(self.unit_name, target_unit, data, timeout)

    async def listen(self, handler: Callable[[str, str, bytes], Awaitable[Optional[bytes]]]) -> None:
        await self.messenger.listen(handler)

    # 参照系メソッドの追加
    async def get_state(self, target_unit: str, message_id: str, status: str = "keep") -> Optional[bytes]:
        return await self.state.get_state(target_unit, message_id, status)

    async def watch_state(self, target_unit: str, message_id: str, handler: Callable[[str, str, bytes], Awaitable[None]], status: str = "keep") -> None:
        await self.state.watch_state(target_unit, message_id, handler, status)