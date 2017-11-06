import dateutil.parser
import dateutil.tz
import os
import sys
script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(script_dir + '/../')

from ciscosparkapi import SparkApiError

from zpark import spark_api


def show_webhooks():
    try:
        webhooks = spark_api.webhooks.list()
    except SparkApiError as e:
        print('Sorry, the Spark service returned an error:\n{}'.format(e))
        sys.exit(1)

    print('Zpark has the following webhooks configured in Spark:\n')
    tz = dateutil.tz.tzlocal()
    for wh in webhooks:
        created = dateutil.parser.parse(wh.created).astimezone(tz)
        print('id: {id}\nname: {name}\ntargetUrl: {url}\n'
                'secret: {secret}\nstatus: {status}\ncreated: {created}\n'
                .format(id=wh.id, name=wh.name, url=wh.targetUrl,
                        secret=wh.secret, status=wh.status,
                        created=created))

if __name__ == '__main__':
    show_webhooks()

