# muf/protocol/naming.py

from typing import Tuple, Optional
from .constants import PROTOCOL_ROOT, PATH_SEPARATOR, KEYSPACE_PREFIX_TEMPLATE

def build_path(unit_name: str, status: str, message_id: str) -> str:
    """
    MUFプロトコルに準拠したキーパスを生成します。
    すべての構成要素を強制的に小文字に変換します。
    形式: muf/[unitname]/[status]/[id]
    """
    u = unit_name.lower()
    s = status.lower()
    m = message_id.lower()
    root = PROTOCOL_ROOT.lower()
    return f"{root}{PATH_SEPARATOR}{u}{PATH_SEPARATOR}{s}{PATH_SEPARATOR}{m}"

def parse_path(path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    キーパスをパースして各構成要素を返します。
    解析前にパス全体を小文字に正規化します。
    不正な形式の場合は (None, None, None) を返します。
    """
    if not path:
        return None, None, None
        
    normalized_path = path.lower()
    parts = normalized_path.split(PATH_SEPARATOR)
    root_lower = PROTOCOL_ROOT.lower()
    
    if len(parts) == 4 and parts[0] == root_lower:
        return parts[1], parts[2], parts[3]
    return None, None, None

def build_keyspace_pattern(unit_name: str = "*", status: str = "*", message_id: str = "*") -> str:
    """
    Keyspace Notificationsの監視に使用するパターンを生成します。
    内部でbuild_pathを呼び出すため、自動的に小文字化されます。
    """
    path = build_path(unit_name, status, message_id)
    return f"{KEYSPACE_PREFIX_TEMPLATE}{path}"

def get_key_from_channel(channel: bytes) -> str:
    """
    チャンネル名からキーパスを抽出し、小文字に正規化して返します。
    """
    channel_str = channel.decode("utf-8").lower()
    if channel_str.startswith(KEYSPACE_PREFIX_TEMPLATE.lower()):
        return channel_str[len(KEYSPACE_PREFIX_TEMPLATE):]
    return channel_str