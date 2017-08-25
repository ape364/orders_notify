import asyncio
from logging import getLogger

from aiotg import Bot

import db
import settings
from exchanges import exchange_apis
from exchanges.base import Order, state_text, State


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

                # get user active orders from db
                order_ids = await db.get_order_ids(exchange_id, uid)
                for order_id in order_ids:
                    order = await api.order_info(order_id)
                    if State(order.state) != State.ACTIVE:
                        state = state_text[order.state]
                        getLogger().info(f'Order {order_id} of user {uid} at exchange {exchange_name!r} '
                                         f'with id {exchange_id} is {state}.')
                        await self.send_message(uid, self.format_order(exchange_name, order))
                        await db.remove_order(uid, exchange_api.api_id, order_id)

                # fetch new orders from api
                active_orders = await api.active_orders()
                new_orders_ids = set(order.order_id for order in active_orders) - order_ids
                if not new_orders_ids:
                    getLogger().info(f'There is no new orders of user id {uid} at exchange {exchange_name!r} '
                                     f'with id {exchange_id}.')
                    continue
                for new_order_id in new_orders_ids:
                    getLogger().info(f'New order {new_order_id} of user id {uid} at exchange {exchange_name!r} '
                                     f'with id {exchange_id}.')

                await db.add_orders((uid, exchange_id, order_id) for order_id in new_orders_ids)

    async def periodic(self, interval=None):
        while True:
            getLogger().info('sleeping')
            await asyncio.sleep(interval or settings.CHECK_INTERVAL)
            await self.check()

    async def send_message(self, uid, order_info):
        user_chat = self.bot.private(uid)
        await user_chat.send_text(order_info, parse_mode='Markdown')

    @staticmethod
    def format_order(exchange_name: str, order: Order):
        return f'*Exchange:* {exchange_name}\n' \
               f'*Pair:* {order.pair}\n' \
               f'*Price:* {order.price}\n' \
               f'*Amount:* {order.amount}\n' \
               f'*State:* {state_text[order.state]}'
