import asyncio
import logging

from utils.shop_db import expire_orders

logger = logging.getLogger(__name__)

async def expire_orders_loop():
    while True:
        try:
            n = await expire_orders(limit=200)
            if n:
                logger.info(f"Expired orders: {n}")
        except Exception as e:
            logger.exception(f"expire_orders_loop error: {e}")
        await asyncio.sleep(3600)
