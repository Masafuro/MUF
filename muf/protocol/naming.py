# muf/protocol/naming.py

from typing import Tuple, Optional
from .constants import PROTOCOL_ROOT, PATH_SEPARATOR, KEYSPACE_PREFIX_TEMPLATE

def build_path(unit_name: str, status: str, message_id: str) -> str:
    """
    MUFプロトコルに準拠したキーパスを生成します。
    形式: MUF/[UNITNAME]/[STATUS]/[ID]
    """
    return f"{PROTOCOL_ROOT}{PATH_SEPARATOR}{unit_name}{PATH_SEPARATOR}{status}{PATH_SEPARATOR}{message_id}"

def parse_path(path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    キーパスをパースして各構成要素を返します。
    不正な形式の場合は (None, None, None) を返します。
    """
    parts = path.split(PATH_SEPARATOR)
    if len(parts) == 4 and parts[0] == PROTOCOL_ROOT:
        return parts[1], parts[2], parts[3]
    return None, None, None

def build_keyspace_pattern(unit_name: str = "*", status: str = "*", message_id: str = "*") -> str:
    """
    Keyspace Notificationsの監視（PSUBSCRIBE）に使用するパターン文字列を生成します。
    引数にアスタリスクを指定することで、柔軟なワイルドカード監視が可能です。
    """
    path = build_path(unit_name, status, message_id)
    return f"{KEYSPACE_PREFIX_TEMPLATE}{path}"

def get_key_from_channel(channel: bytes) -> str:
    """
    Redisから通知されたチャンネル名（バイト列）から、実際のキーパス部分を抽出します。
    """
    channel_str = channel.decode("utf-8")
    if channel_str.startswith(KEYSPACE_PREFIX_TEMPLATE):
        return channel_str[len(KEYSPACE_PREFIX_TEMPLATE):]
    return channel_str