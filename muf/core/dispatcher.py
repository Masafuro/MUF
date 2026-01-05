# muf/core/dispatcher.py

import asyncio
import fnmatch
from typing import Callable, Dict, Awaitable

class MUFEventDispatcher:
    """
    受信したキーイベントを解析し、待機中のFutureや登録されたハンドラへ配送するクラスです。
    """
    def __init__(self):
        # 特定のパスの出現を待機しているFutureの管理（完全一致用）
        self._waiters: Dict[str, asyncio.Future] = {}
        # ワイルドカードパターン（muf/*/req/*等）に対するハンドラの管理（パターン一致用）
        self._handlers: Dict[str, Callable[[str], Awaitable[None]]] = {}

    def add_waiter(self, path: str) -> asyncio.Future:
        """
        パスに対する待機Futureを生成・登録します。
        入力パスは自動的に小文字化されます。
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        normalized_path = path.lower()
        self._waiters[normalized_path] = future
        return future

    def remove_waiter(self, path: str):
        """待機リストから指定パスを削除します。"""
        self._waiters.pop(path.lower(), None)

    def add_handler(self, pattern: str, handler: Callable[[str], Awaitable[None]]):
        """
        パターン合致時のコールバックを登録します。
        パターン文字列は自動的に小文字化されます。
        """
        self._handlers[pattern.lower()] = handler

    def handle_event(self, key_path: str):
        """
        届いたパスを評価し、適切な宛先へ配送します。
        fnmatchを使用してワイルドカード比較を行います。
        """
        # key_pathは naming.get_key_from_channel 経由ですでに小文字化されていますが、念のため
        target_path = key_path.lower()

        # 1. 待機中のFuture（requestメソッドのレスポンス待ち等）への通知
        if target_path in self._waiters:
            future = self._waiters.pop(target_path)
            if not future.done():
                future.set_result(target_path)

        # 2. 登録されたハンドラ（listenメソッドのバックエンド処理等）への通知
        for pattern, handler in self._handlers.items():
            # fnmatchにより、muf/*/req/* のようなワイルドカードが
            # muf/terminal/req/msg1 のような実際のパスにヒットするようになります
            if fnmatch.fnmatch(target_path, pattern):
                # ハンドラを別タスクとして実行し、配送ループのブロッキングを防ぎます
                asyncio.create_task(handler(target_path))