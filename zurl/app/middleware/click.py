from fastapi import Depends
import redis.asyncio as redis
from app.config import get_redis
from app.models.urls import Urls

async def increment_click_count(short_url: str):
    redis_client = await get_redis()
    """
    增加短链接的点击次数
    
    Args:
        short_url: 短链接标识
        redis_client: Redis客户端
    """
    try:
        # 使用Redis HINCRBY命令在hash表中增加计数
        await redis_client.hincrby("zurl:clicks", short_url, 1)
    except Exception as e:
        # 如果Redis操作失败，记录错误但不影响主流程
        print(f"Failed to increment click count for {short_url}: {e}")

async def get_click_count(short_url: str, redis_client: redis.Redis = Depends(get_redis)) -> int:
    """
    获取短链接的点击次数
    
    Args:
        short_url: 短链接标识
        redis_client: Redis客户端
        
    Returns:
        int: 点击次数，如果不存在则返回0
    """
    try:
        count = await redis_client.hget("zurl:clicks", short_url)
        return int(count) if count else 0
    except Exception as e:
        print(f"Failed to get click count for {short_url}: {e}")
        return 0
    
# 获取hash表中所有短链接的点击次数
async def update_click_counts():
    redis_client = await get_redis()
    try:
        all_clicks = await redis_client.hgetall("zurl:clicks")
        # 如果是空的，没获取到，则后面都不执行了
        if not all_clicks:
            print("No click counts found in Redis.")
            return {}
        # 遍历所有all_clicks，然后一次性更新到数据库
        int_clicks = {k: int(v) for k, v in all_clicks.items()}
        # 批量更新到数据库
        Urls.update_click_counts(click_counts=int_clicks)
        # 删除redis里面的所有键和值
        await redis_client.delete("zurl:clicks")

    except Exception as e:
        print(f"Failed to get all click counts: {e}")
        return {}
