import argparse
import os
import sys
script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(script_dir + '/../')

from ciscosparkapi import SparkApiError

from zpark import spark_api


def delete_webhook(webhookid):
    try:
        spark_api.webhooks.delete(webhookid)
        print('Webhook deleted.')
    except SparkApiError as e:
        print('Sorry, the Spark service returned an error:\n{}'.format(e))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('webhookId', action='store')
    args = parser.parse_args()
    delete_webhook(args.webhookId)

