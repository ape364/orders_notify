import asyncio
from logging import getLogger

from aiotg import Bot

import db
import settings
from exchanges import exchange_apis
from exchanges.base import state_text


class OrderChecker:
    bot = Bot(settings.BOT_TOKEN)

    async def check(self):
        uids = await db.get_uids()
        for uid in uids:
            for exchange_api in exchange_apis:
                exchange_id, exchange_name = exchange_api.api_id, exchange_api.name

                api_key, secret_key = await db.get_keys(uid, exchange_id)
                if not api_key or not secret_key:
                    continue
                api = exchange_api(api_key, secret_key)

                db_orders = await db.get_order_ids(exchange_id, uid)
                api_orders = await api.order_history()

                new_orders = api_orders - db_orders

                if not new_orders:
                    getLogger().info(f'There is no new orders of user id {uid} at exchange {exchange_name!r} '
                                     f'with id {exchange_id}.')
                    continue

                await db.add_orders((uid, exchange_id, order_id) for order_id in new_orders)

                for order_id in new_orders:
                    order = await api.order_info(order_id)
                    state = state_text[order.state]
                    getLogger().info(f'Order {order_id} of user {uid} at exchange {exchange_name!r} '
                                     f'with id {exchange_id} is {state}.')
                    await self.send_message(uid, api.format_order(order))

    async def periodic(self, interval=None):
        while True:
            getLogger().info('sleeping')
            await asyncio.sleep(interval or settings.CHECK_INTERVAL)
            await self.check()

    async def send_message(self, uid, order_info):
        user_chat = self.bot.private(uid)
        await user_chat.send_text(order_info, parse_mode='Markdown')
