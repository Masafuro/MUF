# muf/protocol/constants.py

from typing import Final

# プロトコルの基本構造
PROTOCOL_ROOT: Final[str] = "MUF"
PATH_SEPARATOR: Final[str] = "/"

# ステータス定義（パスの第3層に使用）
STATUS_REQ: Final[str] = "REQ"    # リクエスト（依頼）
STATUS_RES: Final[str] = "RES"    # レスポンス（正常完了）
STATUS_ERR: Final[str] = "ERR"    # エラー（異常終了）
STATUS_KEEP: Final[str] = "KEEP"  # 保持型データ（セッション・ステート）

# 有効期限（TTL）のデフォルト値 - 単位：秒
# ネットワーク遅延や処理負荷を考慮した実用的な数値を設定
DEFAULT_TTL_REQ: Final[int] = 10    # バックエンドが処理を開始するまでの猶予
DEFAULT_TTL_RES: Final[int] = 30    # フロントエンドが結果を回収するまでの猶予
DEFAULT_TTL_ERR: Final[int] = 30    # フロントエンドが異常を検知するまでの猶予
DEFAULT_TTL_KEEP: Final[int] = 86400 # 24時間（状態保持用）

# Redis Keyspace Notifications 関連
# デフォルトでDB番号0のキー空間イベントを対象とする
KEYSPACE_PREFIX_TEMPLATE: Final[str] = "__keyspace@0__:"