# muf/protocol/constants.py

from typing import Final

# プロトコルの基本構造
# DB上の物理パスと一致させるため、すべて小文字で定義します
PROTOCOL_ROOT: Final[str] = "muf"
PATH_SEPARATOR: Final[str] = "/"

# ステータス定義（パスの第3層に使用）
STATUS_REQ: Final[str] = "req"
STATUS_RES: Final[str] = "res"
STATUS_ERR: Final[str] = "err"
STATUS_KEEP: Final[str] = "keep"

# 有効期限（TTL）のデフォルト値 - 単位：秒
DEFAULT_TTL_REQ: Final[int] = 10
DEFAULT_TTL_RES: Final[int] = 60    # モニターでの視認性を高めるため、少し長めに設定
DEFAULT_TTL_ERR: Final[int] = 60
DEFAULT_TTL_KEEP: Final[int] = 3600 # 1時間（まずは現実的な範囲で設定）

# Redis Keyspace Notifications 関連
KEYSPACE_PREFIX_TEMPLATE: Final[str] = "__keyspace@0__:"