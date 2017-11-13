import os
import sys
script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(script_dir + '/../')

from ciscosparkapi import SparkApiError

from zpark import app, spark_api


if 'SPARK_WEBHOOK_SECRET' not in app.config:
    raise ValueError('Please define "SPARK_WEBHOOK_SECRET" in app.cfg')
if 'ZPARK_SERVER_URL' not in app.config:
    raise ValueError('Please define "ZPARK_SERVER_URL" in app.cfg')

# This _should_ dynamically get the webhook URL via flask
webhook_url = app.config['ZPARK_SERVER_URL'].rstrip('/') + '/api/v1/webhook'

def create_webhook():
    try:
        webhooks = spark_api.webhooks.list()
    except SparkApiError as e:
        print('Sorry, the Spark service returned an error:\n{}'.format(e))
        sys.exit(1)

    whset = False
    for wh in webhooks:
        if webhook_url == wh.targetUrl:
            whset = True
    if whset:
        from show_spark_webhooks import show_webhooks
        print('There is already a webhook configured that points to {}'
                .format(webhook_url))
        show_webhooks()
        sys.exit(1)

    try:
        rv = spark_api.webhooks.create(name='Zpark incoming webhook',
                                       targetUrl=webhook_url,
                                       resource='messages',
                                       event='created',
                                       secret=app.config['SPARK_WEBHOOK_SECRET'])
        print('Webhook created!\n\nid: {}\nname: {}\ntargetUrl: {}'
                .format(rv.id, rv.name, rv.targetUrl))
    except SparkApiError as e:
        print('Sorry, the Spark service returned an error:\n{}'.format(e))

if __name__ == '__main__':
    create_webhook()

