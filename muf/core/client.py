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
    """

    def __init__(self, unit_name: str, host: str = "localhost", port: int = 6379, db: int = 0):
        self.unit_name = unit_name
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
        """指定したステータスでデータをポストします。パスを返します。"""
        if ttl is None:
            # ステータスに応じたデフォルトTTLを選択
            ttl_map = {
                constants.STATUS_REQ: constants.DEFAULT_TTL_REQ,
                constants.STATUS_RES: constants.DEFAULT_TTL_RES,
                constants.STATUS_ERR: constants.DEFAULT_TTL_ERR,
                constants.STATUS_KEEP: constants.DEFAULT_TTL_KEEP
            }
            ttl = ttl_map.get(status, constants.DEFAULT_TTL_RES)

        path = naming.build_path(self.unit_name, status, message_id)
        await self.connection.set_ex(path, data, ttl)
        return path

    async def request(self, target_unit: str, data: bytes, timeout: float = 10.0) -> bytes:
        """
        特定のユニットに対してリクエストを送り、レスポンスを待機します。
        内部でRESおよびERRパスを監視し、結果を返却または例外を発生させます。
        """
        message_id = str(uuid.uuid4())
        # 自分(ユニット名)宛てのRESとERRのパスを構築
        res_path = naming.build_path(self.unit_name, constants.STATUS_RES, message_id)
        err_path = naming.build_path(self.unit_name, constants.STATUS_ERR, message_id)

        # 監視を開始してからリクエストをポストする（レースコンディション防止）
        wait_res = asyncio.create_task(self.watcher.wait_for_key(res_path, timeout))
        wait_err = asyncio.create_task(self.watcher.wait_for_key(err_path, timeout))

        # リクエストをポスト
        req_path = naming.build_path(self.unit_name, constants.STATUS_REQ, message_id)
        await self.connection.set_ex(req_path, data, int(timeout))

        # いずれかのパスが出現するのを待機
        done, pending = await asyncio.wait(
            [wait_res, wait_err], 
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # 残りのタスクをキャンセル
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
        handlerは (sender_unit, message_id, data) を受け取り、返値をRESとして送り返します。
        """
        async def _internal_handler(key_path: str):
            sender, status, msg_id = naming.parse_path(key_path)
            if status != constants.STATUS_REQ:
                return

            req_data = await self.connection.get(key_path)
            if req_data is None:
                return

            try:
                # ユーザー定義のハンドラを実行
                response_data = await handler(sender, msg_id, req_data)
                if response_data is not None:
                    # 成功パス: 元のリクエスト元(sender)のRESディレクトリへ返信
                    res_path = naming.build_path(sender, constants.STATUS_RES, msg_id)
                    await self.connection.set_ex(res_path, response_data, constants.DEFAULT_TTL_RES)
            except Exception as e:
                # 失敗パス: 元のリクエスト元(sender)のERRディレクトリへ通知
                err_path = naming.build_path(sender, constants.STATUS_ERR, msg_id)
                await self.connection.set_ex(err_path, str(e).encode(), constants.DEFAULT_TTL_ERR)

        # REQステータスのパスを全て監視対象として登録
        req_prefix = f"{constants.PROTOCOL_ROOT}{constants.PATH_SEPARATOR}*{constants.PATH_SEPARATOR}{constants.STATUS_REQ}"
        self.watcher.register_handler(req_prefix, _internal_handler)