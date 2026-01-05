# muf/core/state.py

from typing import Optional, Callable, Awaitable
from .connection import MUFConnection
from .watcher import MUFWatcher
from ..protocol import naming, constants

class MUFStateManager:
    """
    共有メモリ上のデータ（状態）の読み書きと監視を管理するクラスです。
    """
    def __init__(self, connection: MUFConnection, watcher: MUFWatcher):
        self.connection = connection
        self.watcher = watcher

    async def send(self, unit_name: str, status: str, message_id: str, data: bytes, ttl: Optional[int] = None) -> str:
        """指定したパスにデータを書き込みます。"""
        status_norm = status.lower()
        if ttl is None:
            ttl_map = {
                constants.STATUS_REQ.lower(): constants.DEFAULT_TTL_REQ,
                constants.STATUS_RES.lower(): constants.DEFAULT_TTL_RES,
                constants.STATUS_ERR.lower(): constants.DEFAULT_TTL_ERR,
                constants.STATUS_KEEP.lower(): constants.DEFAULT_TTL_KEEP
            }
            ttl = ttl_map.get(status_norm, constants.DEFAULT_TTL_RES)

        path = naming.build_path(unit_name, status_norm, message_id)
        await self.connection.set_ex(path, data, ttl)
        return path

    async def get_state(self, target_unit: str, message_id: str, status: str = "keep") -> Optional[bytes]:
        """指定された状態を一度だけ取得します。"""
        path = naming.build_path(target_unit, status, message_id)
        return await self.connection.get(path)

    async def watch_state(self, target_unit: str, message_id: str, handler: Callable[[str, str, bytes], Awaitable[None]], status: str = "keep") -> None:
        """状態の変化をリアルタイムに購読します。"""
        async def _internal_state_handler(key_path: str):
            sender, _, msg_id = naming.parse_path(key_path)
            data = await self.connection.get(key_path)
            if data is not None:
                await handler(sender, msg_id, data)

        pattern = naming.build_path(target_unit, status, message_id)
        self.watcher.register_handler(pattern, _internal_state_handler)