import redis
from typing import Dict, Any, Optional

class MUFConnector:
    """
    Redisへの物理接続とハッシュ操作に特化したクラス。
    """
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        self.pool = redis.ConnectionPool(
            host=host, 
            port=port, 
            db=db, 
            decode_responses=True
        )
        self.r = redis.Redis(connection_pool=self.pool)

    def set_hash(self, path: str, mapping: Dict[str, Any]) -> bool:
        return self.r.hset(path, mapping=mapping) > 0

    def get_hash_all(self, path: str) -> Dict[str, str]:
        return self.r.hgetall(path)

    def update_field(self, path: str, field: str, value: Any) -> bool:
        return self.r.hset(path, field, value) >= 0

    def get_field(self, path: str, field: str) -> Optional[str]:
        return self.r.hget(path, field)