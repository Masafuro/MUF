# muf/core/client.py

import asyncio
import uuid
from typing import Optional, Callable, Awaitable, Any
from .connection import MUFConnection
from .watcher import MUFWatcher
from ..protocol import naming, constants

class MUFClient:
    """
    MUFプロトコルのフロントエンドおよびバックエンド機能を提供するメインクライアントクラスです。
    全ての入力（ユニット名、ID、ステータス）は内部で自動的に小文字に正規化されます。
    """

    def __init__(self, unit_name: str, host: str = "localhost", port: int = 6379, db: int = 0):
        # ユニット名を初期化時に小文字化し、DB上のパスの不整合を未然に防ぎます
        self.unit_name = unit_name.lower()
        self.connection = MUFConnection(host=host, port=port, db=db)
        self.watcher = MUFWatcher(self.connection)
        self._is_running = False

    async def start(self) -> None:
        """クライアントを起動し、Redis接続とイベント監視を開始します。"""
        if self._is_running:
            return
        await self.connection.connect()
        await self.watcher.start()
        self._is_running = True

    async def stop(self) -> None:
        """クライアントを停止し、リソースを安全に解放します。"""
        if not self._is_running:
            return
        await self.watcher.stop()
        await self.connection.disconnect()
        self._is_running = False

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def send(self, status: str, message_id: str, data: bytes, ttl: Optional[int] = None) -> str:
        """指定したステータスでデータをポストします。naming.build_pathにより自動的に小文字化されます。"""
        # ステータスを正規化
        status_norm = status.lower()
        
        if ttl is None:
            # 正規化されたステータスに基づいてTTLを選択
            ttl_map = {
                constants.STATUS_REQ.lower(): constants.DEFAULT_TTL_REQ,
                constants.STATUS_RES.lower(): constants.DEFAULT_TTL_RES,
                constants.STATUS_ERR.lower(): constants.DEFAULT_TTL_ERR,
                constants.STATUS_KEEP.lower(): constants.DEFAULT_TTL_KEEP
            }
            ttl = ttl_map.get(status_norm, constants.DEFAULT_TTL_RES)

        # naming.build_path 内で全ての要素が小文字に変換されます
        path = naming.build_path(self.unit_name, status_norm, message_id)
        await self.connection.set_ex(path, data, ttl)
        return path

    async def request(self, target_unit: str, data: bytes, timeout: float = 10.0) -> bytes:
        """
        特定のユニット（現在は自分自身の空間）に対してリクエストを送り、レスポンスを待機します。
        """
        # UUIDも念のため小文字として扱います
        message_id = str(uuid.uuid4()).lower()
        
        # 監視対象パスとリクエストパスの構築
        res_path = naming.build_path(self.unit_name, constants.STATUS_RES, message_id)
        err_path = naming.build_path(self.unit_name, constants.STATUS_ERR, message_id)

        wait_res = asyncio.create_task(self.watcher.wait_for_key(res_path, timeout))
        wait_err = asyncio.create_task(self.watcher.wait_for_key(err_path, timeout))

        # リクエストのポスト（自分のREQディレクトリへ）
        req_path = naming.build_path(self.unit_name, constants.STATUS_REQ, message_id)
        await self.connection.set_ex(req_path, data, int(timeout))

        done, pending = await asyncio.wait(
            [wait_res, wait_err], 
            return_when=asyncio.FIRST_COMPLETED
        )
        
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
        """
        バックエンドとしてリクエストを待ち受けます。
        """
        async def _internal_handler(key_path: str):
            # naming.parse_path は内部で小文字化して解析します
            sender, status, msg_id = naming.parse_path(key_path)
            
            # constantsの値も小文字と比較
            if status != constants.STATUS_REQ.lower():
                return

            req_data = await self.connection.get(key_path)
            if req_data is None:
                return

            try:
                response_data = await handler(sender, msg_id, req_data)
                if response_data is not None:
                    # レスポンスも正規化されたパスへ書き戻します
                    res_path = naming.build_path(sender, constants.STATUS_RES, msg_id)
                    await self.connection.set_ex(res_path, response_data, constants.DEFAULT_TTL_RES)
            except Exception as e:
                err_path = naming.build_path(sender, constants.STATUS_ERR, msg_id)
                await self.connection.set_ex(err_path, str(e).encode(), constants.DEFAULT_TTL_ERR)

        # 監視パターン自体も小文字で構築
        root = constants.PROTOCOL_ROOT.lower()
        sep = constants.PATH_SEPARATOR
        req_stat = constants.STATUS_REQ.lower()
        
        # 全てのユニットのREQを監視するワイルドカードパターン
        req_pattern = f"{root}{sep}*{sep}{req_stat}{sep}*"
        self.watcher.register_handler(req_pattern, _internal_handler)