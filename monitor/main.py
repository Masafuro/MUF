# monitor/main.py

import asyncio
import os
import sys
import traceback
import redis.asyncio as redis
from redis.exceptions import AuthenticationError
from muf.protocol import naming
import logging
from logging.handlers import RotatingFileHandler

# Configure logging with rotating file handler
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "monitor.log")
max_bytes = 51200  # 50kB max file size
backup_count = 5  # Keep 5 backup files

# Setup rotating file handler
file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Setup console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

async def monitor():
    REDIS_HOST = "muf-redis"
    BASE_PATTERN = "muf/*"
    SUBSCRIBE_PATTERN = f"__keyspace@0__:{BASE_PATTERN}"
    
    db_user = os.getenv("REDIS_USERNAME", None)
    db_pass = os.getenv("REDIS_PASSWORD", None)
    
    r = redis.Redis(
        host=REDIS_HOST, 
        username=db_user,
        password=db_pass,
        decode_responses=True
    )
    
    pubsub = r.pubsub()
    
    logger.info("==============================================================================")
    logger.info(" MUF Logic Monitor: Observing Memory Space Transitions")
    logger.info(f" User: {db_user if db_user else 'default'}")
    logger.info(f" Status: Active (Subscribed to {BASE_PATTERN})")
    logger.info("==============================================================================\n")
    
    try:
        # 権限チェックはここで行われます
        await pubsub.psubscribe(SUBSCRIBE_PATTERN)

        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue
            
            event = message["data"]
            channel = message["channel"]
            path = channel.split(":", 1)[1]
            
            logger.debug(f"Received [{event}] on {path}")
            
            try:
                unit, status, msg_id = naming.parse_path(path)
                
                if event in ["set", "expired", "del"]:
                    display_data = ""
                    if event == "set":
                        val = await r.get(path)
                        display_data = f"DATA: {val}"
                    else:
                        display_data = f"--- {event.upper()} ---"
                        
                    logger.info(f"[{status.lower():^6}] {unit:<15} | ID: {msg_id:<12} | {display_data}")
                    
            except Exception:
                # 解析エラー時もトレースバックを表示して詳細を確認できるようにします
                logger.error("  └─ Parse Error (Path might not follow MUF rules)")
                logger.debug(traceback.format_exc())
                continue
          
    except AuthenticationError:
        logger.error("\n[!] 認証エラーが発生しました:")
        logger.debug(traceback.format_exc())
    except asyncio.CancelledError:
        await pubsub.punsubscribe(SUBSCRIBE_PATTERN)
    except Exception:
        logger.error("\n[!] 実行中に予期しないエラーが発生しました:")
        logger.debug(traceback.format_exc())
    finally:
        await r.aclose()

if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
