from functools import wraps
from datetime import datetime as dt
import traceback

from flask import current_app, request
from flask_restful import abort

from zpark import app
from zpark.tasks import *


def authorize_webhook(webhook_data):
    """
    Authorize webhook requests so that only trusted users can issue commands.

    This implementation of the authorization scheme is very basic, but
    effective for now. Crawl, walk, run. Authorization is successful if
    the 'personEmail' in the incoming webhook data is found in a list of
    trusted email addresses.

    The authorization check is disabled if the list of trusted users is
    empty.

    The default list of trusted users is ``None`` which means that no users
    are trusted.

    The list of trusted users is stored in the SPARK_TRUSTED_USERS config
    parameter.

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

    if len(app.config['SPARK_TRUSTED_USERS']) > 0:
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
                    " supported: webhook:\"{}\" resource:{} event:{}"
                    .format(data['name'], data['resource'], data['event']))
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

    app.logger.info("A command was received via Spark (task {}):"
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
    # The appropriate dict needs to be passed to the task. This is a
    # reasonably reliable but not fool-proof way to determine if the
    # recipient is a user or a room.
    if '@' in sendto:
        to = {'emails': [sendto]}
    else:
        to = {'id': sendto}

    if message is not None:
        text = '\n\n'.join([subject, message])
    else:
        text = subject

    try:
        task = task_send_spark_message.apply_async((to, text))
    except (TypeError, task_send_spark_message.OperationalError) as e:
        app.logger.error("Unable to create task 'task_send_spark_message'."
                " Spark alert dropped! {}: {}\n{}"
                .format(type(e).__name__, e, traceback.format_exc()))
        return (
            {'error': 'Unable to create worker task'},
            500
        )

    app.logger.info("Dispatched an alert message to Spark (task {}): to:{} "
                    " subject:\"{}\""
                        .format(task.id, sendto, subject))

    return {
        'to': sendto,
        'message': text,
        'taskid': task.id
    }

def requires_api_token(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        """
        Authenticate API requests by checking for a valid token in the request.

        The API token is configured in the ZPARK_API_TOKEN config parameter
        in app.cfg. A client that calls a Zpark API endpoint must pass the
        same value as configured for ZPARK_API_TOKEN via the Token header
        in the HTTP request. The request is successfully authenticated if
        the Token header value matches the ZPARK_API_TOKEN value. The request
        fails authentication if the values differ or if the client didn't
        provide a Token header.

        Zpark must be configured with a static token in the ZPARK_API_TOKEN
        config parameter. If this parameter is not present in the config,
        the app will reject incoming API requests as a safety measure.

        Use of the token may be disabled by setting ZPARK_API_TOKEN to None.
        This is almost certainly not what you want and should not be done
        unless you clearly understand what you're doing.

        Args:
            - None

        Returns:
            - This is a decorator function so it returns the wrapped function
                when authentication is successful.
            - When authentication fails, the decorator calls the Flask::abort
                function with an appropriate HTTP status code.

        Throws:
            - None
        """

        req_token = request.headers.get('Token', None)

        if 'ZPARK_API_TOKEN' not in current_app.config:
            current_app.logger.error("Request rejected: ZPARK_API_TOKEN"
                                     " must be set in app.cfg")
            abort(500)
        else:
            our_token = current_app.config['ZPARK_API_TOKEN']

        if not req_token and our_token is not None:
            current_app.logger.warning("Request rejected: client"
                                      " did not provide a ZPARK_API_TOKEN")
            abort(401)

        if req_token == our_token or our_token is None:
            return func(*args, **kwargs)
        else:
            current_app.logger.warning("Request rejected: Invalid"
                                       " ZPARK_API_TOKEN received from"
                                       " client")
            abort(401)

    return decorated

