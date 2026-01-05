# muf/core/messaging.py

import asyncio
import uuid
from typing import Optional, Callable, Awaitable
from .connection import MUFConnection
from .watcher import MUFWatcher
from .state import MUFStateManager
from ..protocol import naming, constants

class MUFMessenger:
    """
    ユニット間の対話（リクエスト・レスポンス）フローを管理するクラスです。
    """
    def __init__(self, connection: MUFConnection, watcher: MUFWatcher, state_manager: MUFStateManager):
        self.connection = connection
        self.watcher = watcher
        self.state = state_manager

    async def request(self, unit_name: str, target_unit: str, data: bytes, timeout: float = 10.0) -> bytes:
        """リクエストを送信し、レスポンスまたはエラーを待機します。"""
        message_id = str(uuid.uuid4()).lower()
        res_path = naming.build_path(unit_name, constants.STATUS_RES, message_id)
        err_path = naming.build_path(unit_name, constants.STATUS_ERR, message_id)

        wait_res = asyncio.create_task(self.watcher.wait_for_key(res_path, timeout))
        wait_err = asyncio.create_task(self.watcher.wait_for_key(err_path, timeout))

        await self.state.send(unit_name, constants.STATUS_REQ, message_id, data, int(timeout))

        done, pending = await asyncio.wait([wait_res, wait_err], return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()

        if wait_res.done() and wait_res.result():
            result = await self.connection.get(res_path)
            return result if result is not None else b""
        
        if wait_err.done() and wait_err.result():
            error_msg = await self.connection.get(err_path)
            raise RuntimeError(f"Backend reported error: {error_msg.decode() if error_msg else 'unknown'}")

        raise asyncio.TimeoutError(f"Request to {target_unit} timed out after {timeout}s")

    async def listen(self, handler: Callable[[str, str, bytes], Awaitable[Optional[bytes]]]) -> None:
        """バックエンドとして全リクエストを監視し、ハンドラを実行します。"""
        async def _internal_handler(key_path: str):
            sender, status, msg_id = naming.parse_path(key_path)
            if status != constants.STATUS_REQ.lower():
                return

            req_data = await self.connection.get(key_path)
            if req_data is None:
                return

            try:
                response_data = await handler(sender, msg_id, req_data)
                if response_data is not None:
                    await self.state.send(sender, constants.STATUS_RES, msg_id, response_data)
            except Exception as e:
                await self.state.send(sender, constants.STATUS_ERR, msg_id, str(e).encode())

        root = constants.PROTOCOL_ROOT.lower()
        sep = constants.PATH_SEPARATOR
        req_stat = constants.STATUS_REQ.lower()
        req_pattern = f"{root}{sep}*{sep}{req_stat}{sep}*"
        self.watcher.register_handler(req_pattern, _internal_handler)