from functools import wraps
from datetime import datetime as dt
import traceback

from flask import current_app, request
from flask_restful import abort

from zpark import app
from zpark.tasks import task_send_spark_message


def ping(api_version):
    return {
        'hello': 'Hello!',
        'apiversion': api_version,
        'utctime': str(dt.utcnow())
    }

def send_spark_alert_message(sendto, subject, message):
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
        task = task_send_spark_message.apply_async((msg_args,))
    except (TypeError, task_send_spark_message.OperationalError) as e:
        app.logger.error("Unable to create task 'task_send_spark_message'."
                " Spark alert dropped! {}: {}\n{}"
                .format(type(e).__name__, e, traceback.format_exc()))

    app.logger.info("New Spark alert message (task {}): toPersonEmail:{} "
                    "toRoomId:{}"
                        .format(task.id,
                                msg_args.get('toPersonEmail', 'None'),
                                msg_args.get('roomId', 'None')))


    return {
        'toPersonEmail': msg_args.get('toPersonEmail', None),
        'toRoomId': msg_args.get('roomId', None),
        'message': msg_args.get('text'),
        'taskid': task.id
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

