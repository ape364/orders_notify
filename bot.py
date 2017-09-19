import asyncio
import logging

from aiotg import Bot, Chat

import db
import settings
from exchanges import get_api_by_name, get_supported_info
from order_checker import OrderChecker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(settings.BOT_NAME)

bot = Bot(api_token=settings.BOT_TOKEN)


async def run_loop():
    # send updates
    checker = OrderChecker()
    await checker.check()
    asyncio.ensure_future(checker.periodic(), loop=loop)
    await bot.loop()


@bot.command(r'(/start|/help)')
async def start(chat: Chat, match):
    await chat.send_text(
        'Hello! I can notify you about your closed orders on next exchanges:\n'
        f'{get_supported_info()}\n'
        'Just send command like `/sub exchange_name api_key secret_key` (keys with read only permissions) '
        'to subscribe order notifications and `/unsub exchange_name` to unsubscribe.',
        parse_mode='Markdown'
    )


@bot.command(r'/subs')
async def subscriptions(chat: Chat, match):
    uid = chat.sender['id']
    subs = await db.user_subscriptions(uid)
    if not subs:
        await chat.send_text('You have no active subscriptions.')
        return
    await chat.send_text(
        'You are subscribed to the following exchange notifications:\n' +
        '\n'.join(subs)
    )


@bot.command(r'\/sub(.*)')
async def subscribe(chat: Chat, match):
    uid = chat.sender['id']
    data = match.group(1).strip().split(' ')
    if not data or len(data) != 3:
        await chat.send_text(
            'Please specify exchange name with keys. For example:\n'
            '`/sub bittrex a1s2d3f4g5h6j7k8l9a1s2d3f4g5h6j7 a1s2d3f4g5h6j7k8l9a1s2d3f4g5h6j7`',
            parse_mode='Markdown'
        )
        return
    exchange_name, api, secret = data
    exchange_cls = get_api_by_name(exchange_name)
    if not exchange_cls:
        await chat.send_text('Unsupported exchange.')
        return
    if not exchange_cls.check_keys(api, secret):
        await chat.send_text(f'Invalid format.')
        return
    if await db.is_subscribed(uid, exchange_cls.api_id):
        await chat.send_text(f'You are already subscribed to {exchange_name!r}.')
        return

    exchange_api = exchange_cls(api, secret)
    order_history = await exchange_api.order_history()
    await db.add_orders((uid, exchange_cls.api_id, order_id) for order_id in order_history)

    await db.subscribe(uid, exchange_cls.api_id, api, secret)
    await chat.send_text(f'You are subscribed to {exchange_name!r}.')


@bot.command(r'/unsub(.*)')
async def unsubscribe(chat: Chat, match):
    uid = chat.sender['id']
    exchange_name = match.group(1).strip()
    if not exchange_name:
        await chat.send_text(
            'Please specify exchange name. For example:\n'
            '`/unsub bittrex`',
            parse_mode='Markdown')
        return
    exchange_api = get_api_by_name(exchange_name)
    if not exchange_api:
        await chat.send_text('Unsupported exchange.')
        return
    if not await db.is_subscribed(uid, exchange_api.api_id):
        await chat.send_text(f'You are not subscribed to {exchange_name!r}.')
        return
    await db.unsubscribe(uid, exchange_api.api_id)
    await chat.send_text(f'You are unsubscribed from {exchange_name!r}.')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.init_db())
    try:
        logger.info('bot started')
        loop.run_until_complete(run_loop())
    except KeyboardInterrupt:
        pass
    finally:
        logger.info('bot stopped')
