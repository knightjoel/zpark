from functools import wraps
from datetime import datetime as dt
import traceback

from flask import current_app, request
from flask_restful import abort

from zpark import app
from zpark.tasks import *


def authorize_webhook(webhook_data):
    """
    Authorize webhook requests so only trusted users can issue commands.

    This implementation of the authorization scheme is very basic, but
    effective for now. Crawl, walk, run. Authorization is successful if
    the 'personEmail' in the incoming webhook data is found in a list of
    trusted email addresses.

    Args:
        webhook_data (dict): The JSON data that Spark POSTed to our webhook
            URL.

    Returns:
        True: if authorization is successful or if the list of trusted
            users has not been configured (signalling that authorization
            should not be used).
        False: if authorization fails.

    Raises:
        KeyError: if the webhook_data dictionary is missing expected keys.
    """

    try:
        caller = webhook_data['data']['personEmail']
    except KeyError as e:
        app.logger.error("Received corrupt or incomplete JSON data: {}"
                .format(e))
        raise

    if 'SPARK_TRUSTED_USERS' in app.config:
        return caller in app.config['SPARK_TRUSTED_USERS']
    else:
        return True


def handle_spark_webhook(data):
    """
    Handle a webhook request received from Spark.

    What's interesting here is that because of Spark's security architecture,
    the webhook doesn't actually provide the plain text of a "message"
    webhook in the webhook notification. We have to issue a request back
    to Spark to get the plain text and only then do we know what the actual
    command was that the user issued.

    Because a Spark API call is needed to properly handle the webhook, we
    defer the work to an async task in order to provide a speedy reply to the
    Spark webhook client.

    The Zpark bot only responds to webhooks sent in response to a new
    message being created and only if the actor (caller) is part of the
    authorized list of Zpark users.

    Args:
        data (dict): The JSON data that Spark POSTed to our webhook URL.

    Returns:
        A sequence which contains two elements:
            - A dict containing some status information about how we processed
                the webhook request.
            - An HTTP status code which will be returned to the Spark webhook
                client.
    """

    try:
        if data['resource'] != 'messages' or data['event'] != 'created':
            app.logger.error("Received a webhook notification that is not"
                    " supported: resource:{} event:{} name:\"{}\""
                    .format(data['resource'], data['event'], data['name']))
            return (
                {'error': 'No support for that type of resource and/or event'},
                400
            )

        if not authorize_webhook(data):
            return (
                # Spark API will disable the webhook if it receives too many
                # non 20x replies in a given time window. Since this code
                # path can be entered based on user input, play it safe and
                # return 200 so as not to allow for a DoS.
                {'error': 'User not authorized'},
                200
            )
    except KeyError as e:
        app.logger.error("Received webhook data that is incomplete or"
                " malformed: {}".format(e))
        return (
            {'error': 'The webhook envelope appears to be malformed'},
            400
        )

    try:
        task = task_dispatch_spark_command.apply_async((data,))
    except (TypeError, task_dispatch_spark_command.OperationalError) as e:
        app.logger.error("Unable to create task 'task_dispatch_spark_command'."
                " Spark command response has been dropped! {}: {}\n{}"
                .format(type(e).__name__, e, traceback.format_exc()))
        return (
            {'error': 'Unable to create worker task'},
            500
        )

    app.logger.info("A Spark command was received (task {}):"
                        " webhook:\"{}\" resource:{} event:{}"
                        .format(task.id, data['name'], data['resource'],
                                data['event']))

    return ({
        'taskid': task.id
    }, 200)


def ping(api_version):
    return {
        'hello': 'Hello!',
        'apiversion': api_version,
        'utctime': str(dt.utcnow())
    }

def send_spark_alert_message(sendto, subject, message):
    if message is not None:
        text = '\n\n'.join([subject, message])
    else:
        text = subject

    try:
        task = task_send_spark_message.apply_async((sendto, text))
    except (TypeError, task_send_spark_message.OperationalError) as e:
        app.logger.error("Unable to create task 'task_send_spark_message'."
                " Spark alert dropped! {}: {}\n{}"
                .format(type(e).__name__, e, traceback.format_exc()))
        return {
            'error': 'Unable to create task \'task_send_spark_message\':'
                    ' {}: {} {}'.format(type(e).__name__, e,
                                        traceback.format_exc())
        }, 500

    app.logger.info("New Spark alert message (task {}): to:{} subject:\"{}\""
                        .format(task.id, sendto, subject))

    return {
        'to': sendto,
        'message': text,
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

