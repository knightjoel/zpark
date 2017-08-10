from functools import wraps
from datetime import datetime as dt

from ciscosparkapi import SparkApiError
from flask import current_app, request
from flask_restful import abort

from zpark import spark_api


def ping(api_version):
    return {
        'hello': 'Hello!',
        'apiversion': api_version,
        'utctime': str(dt.utcnow())
    }

def spark_send_alert_message(sendto, subject, message):
    try:
        msg = spark_api.messages.create(
                toPersonEmail=sendto,
                text='\n\n'.join([subject, message]))
    except SparkApiError as e:
        # XXX log the error
        abort(409)

    return {
        'to': msg.toPersonEmail,
        'message': msg.text,
        'message_id': msg.id,
        'created': msg.created
    }

def requires_token(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        token = request.headers.get('Token', None)

        if not token or not current_app.config['SB_API_TOKEN']:
            abort(401)

        if token == current_app.config['SB_API_TOKEN']:
            return func(*args, **kwargs)
        else:
            abort(401)

    return decorated

