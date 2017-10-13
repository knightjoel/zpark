from functools import wraps
from datetime import datetime as dt

from ciscosparkapi import SparkApiError
from flask import current_app, request
from flask_restful import abort

from zpark import app, spark_api


def ping(api_version):
    return {
        'hello': 'Hello!',
        'apiversion': api_version,
        'utctime': str(dt.utcnow())
    }

def spark_send_alert_message(sendto, subject, message):
    # crude but good enough to tell the difference between roomId and
    # toPersonEmail inputs.
    if '@' in sendto:
        msg_args = dict(toPersonEmail=sendto)
    else:
        msg_args = dict(roomId=sendto)

    if message is not None:
        msg_args.update(text='\n\n'.join([subject, message]))
    else:
        msg_args.update(text=subject)

    try:
        msg = spark_api.messages.create(**msg_args)
    except SparkApiError as e:
        msg = "The Spark API returned an error: {}".format(e)
        app.logger.error(msg)
        abort(e.response_code, message=msg)

    app.logger.info("New message: toPersonEmail:{} toRoomId:{} messageId:{}"
                        .format(msg.toPersonEmail, msg.roomId, msg.id))

    return {
        'toPersonEmail': msg.toPersonEmail,
        'toRoomId': msg.roomId,
        'message': msg.text,
        'messageId': msg.id,
        'created': msg.created
    }

def requires_api_token(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        token = request.headers.get('Token', None)

        if not token or not current_app.config['ZPARK_API_TOKEN']:
            current_app.logger.warning("Request was missing ZPARK_API_TOKEN")
            abort(401)

        if token == current_app.config['ZPARK_API_TOKEN']:
            return func(*args, **kwargs)
        else:
            current_app.logger.warning("Invalid ZPARK_API_TOKEN")
            abort(401)

    return decorated

