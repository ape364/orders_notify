import asyncpg

import settings
from exchanges import exchange_apis

pool = None  # asyncpg connection pool


async def create_tables():
    async with pool.acquire() as conn:
        await conn.fetch(
            '''CREATE TABLE IF NOT EXISTS exchange(
                id SERIAL PRIMARY KEY,
                name VARCHAR,
                url VARCHAR)'''
        )

        await conn.fetch(
            '''CREATE TABLE IF NOT EXISTS subscription(
                uid INTEGER NOT NULL,
                exchange_id INTEGER REFERENCES exchange (id) NOT NULL,
                api_key VARCHAR,
                secret_key VARCHAR,
                PRIMARY KEY (uid, exchange_id))'''
        )

        await conn.fetch(
            '''CREATE TABLE IF NOT EXISTS user_order(
                uid INTEGER NOT NULL,
                exchange_id INTEGER REFERENCES exchange (id) NOT NULL,
                order_id VARCHAR NOT NULL,
                PRIMARY KEY (uid, exchange_id, order_id))'''
        )


async def init_db():
    global pool
    pool = await asyncpg.create_pool(settings.DATABASE_URL)
    await create_tables()
    await insert_initial_values()


async def insert_initial_values():
    exchanges = ((api.api_id, api.name, api.url) for api in exchange_apis)
    async with pool.acquire() as conn:
        await conn.executemany(
            '''INSERT INTO exchange (id, name, url) 
               VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING''',
            exchanges
        )


async def user_subscriptions(uid):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''SELECT name
               FROM subscription
                 JOIN exchange ON exchange.id = subscription.exchange_id
               WHERE uid = $1 ''',
            uid
        )
        return (row['name'] for row in rows) if rows else None


async def is_subscribed(uid: int, exchange_id: int) -> bool:
    async with pool.acquire() as conn:
        res = await conn.fetchrow(
            '''SELECT COUNT(*) FROM subscription WHERE 
                uid = $1 AND 
                exchange_id = $2''',
            uid,
            exchange_id
        )
        return res['count'] > 0


async def subscribe(uid, exchange_id, api_key, secret_key):
    async with pool.acquire() as conn:
        await conn.fetch(
            '''INSERT INTO subscription (uid, exchange_id, api_key, secret_key) 
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (uid, exchange_id) DO UPDATE SET 
                api_key = $3,
                secret_key = $4''',
            uid,
            exchange_id,
            api_key,
            secret_key
        )


async def unsubscribe(uid, exchange_id):
    async with pool.acquire() as conn:
        await conn.fetch(
            '''DELETE FROM subscription WHERE uid = $1 AND exchange_id = $2''',
            uid,
            exchange_id
        )


async def add_orders(orders):
    async with pool.acquire() as conn:
        await conn.executemany(
            '''INSERT INTO user_order (uid, exchange_id, order_id) 
               VALUES ($1, $2, $3)
               ON CONFLICT DO NOTHING''',
            orders
        )


async def get_order_ids(exchange_id, uid):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''SELECT order_id FROM user_order WHERE exchange_id = $1 AND uid = $2''',
            exchange_id,
            uid
        )
        return {row['order_id'] for row in rows}


async def get_uids():
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            '''SELECT DISTINCT uid FROM subscription'''
        )
        return (row['uid'] for row in rows)


async def get_keys(uid, exchange_id):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''SELECT api_key, secret_key FROM subscription WHERE uid = $1 AND exchange_id = $2''',
            uid,
            exchange_id
        )
        if not row:
            return None, None
        return row['api_key'], row['secret_key']
