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
    # crude but good enough to tell the difference between roomId and
    # toPersonEmail inputs.
    if '@' not in sendto:
        abort(400, message="\"to\" must be an email address that represents "
                       "a Spark user.")

    try:
        msg = spark_api.messages.create(
                toPersonEmail=sendto,
                text='\n\n'.join([subject, message]))
    except SparkApiError as e:
        # XXX log the error
        abort(e.response_code,
              message="The Spark API returned an error: {}".format(e))

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

