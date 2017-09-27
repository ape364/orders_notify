import os

BOT_TOKEN = os.environ['NOTIFY_BOT_TOKEN']
BOT_NAME = 'OrdersNotifyBot'

DATABASE_URL = os.environ['DATABASE_URL']

CHECK_INTERVAL = int(os.environ['NOTIFY_BOT_CHECK_INTERVAL'])  # seconds

REQUEST_ATTEMPTS_LIMIT = int(os.environ['NOTIFY_BOT_ATTEMPTS_LIMIT'])
