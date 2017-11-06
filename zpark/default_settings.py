import logging

DEBUG = False
ZPARK_API_TOKEN = None
SPARK_ACCESS_TOKEN = None
#SPARK_WEBHOOK_SECRET = <generate this with "openssl rand 16 -hex">

APP_LOG_MAXBYTES = 1024 * 1024 * 10
APP_LOG_ROTATECOUNT = 2
APP_LOG_LOGLEVEL = logging.INFO

CELERY_BROKER_URL = 'ampq://user:pass@hostname/vhost'
ZABBIX_SERVER_URL = 'http://zabbix.server'
ZABBIX_USERNAME = 'username'
ZABBIX_PASSWORD = 'password'

#ZPARK_SERVER_URL = 'https://your.spark.bot.url'
