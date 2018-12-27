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
    the ``personEmail`` value in the incoming webhook data is found in a list
    of trusted email addresses or if the domain part of the ``personEmail``
    (ie, everything to the right of and including the ``@`` character) is
    found in the same trusted list.

    The authorization check is disabled if the list of trusted users is
    empty.

    The default list of trusted users is :py:obj:`None` which means that no
    users are trusted.

    The list of trusted users and domains is stored in the
    :py:attr:`zpark.default_settings.SPARK_TRUSTED_USERS` config parameter.

    Args:
        webhook_data (dict): The JSON data that Spark POSTed to our webhook
            URL.

    Returns:
        bool:

            - :py:obj:`True`: If authorization is successful or if the list of
              trusted users is empty (signalling that
              authorization should not be used).
            - :py:obj:`False`: If authorization fails.

    Raises:
        :py:exc:`KeyError`: If the ``webhook_data`` dictionary is missing
            expected keys.

    """

    try:
        caller = webhook_data['data']['personEmail']
    except KeyError as e:
        app.logger.error("Received corrupt or incomplete JSON data: {}"
                .format(e))
        raise

    if len(app.config['SPARK_TRUSTED_USERS']) > 0:
        domain = '@' + caller.rsplit('@', 1)[1]
        return (caller in app.config['SPARK_TRUSTED_USERS']
                or domain in app.config['SPARK_TRUSTED_USERS'])
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
    trusted list of Zpark users.

    Args:
        data (dict): The JSON data that Spark POSTed to our webhook URL.

    Returns:
        set: A two-element :py:obj:`set` which contains:

            - A :py:obj:`dict` containing some status information about how we
              processed the webhook request.
            - An :py:obj:`int` that is the HTTP status code which will be
              returned to the Spark webhook client.

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
            app.logger.debug("Received a command from unauthorized user"
                    " {}".format(data['data']['personEmail']))
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
    """
    Respond to an API ping request.

    The ``ping`` endpoint is meant for validating that the Zpark API service
    is configured and operating correctly. It's safe for testing as it does
    not emit any messages to Spark or make any third-party API calls.

    Args:
        api_version (int): The version of the Zpark API that handled the
            request.

    Returns:
        dict: A :py:obj:`dict` which contains some basic information about
        the API and acts as confirmtion that the request was processed
        successfully.

    """

    return {
        'hello': 'Hello!',
        'apiversion': api_version,
        'utctime': str(dt.utcnow())
    }

def send_spark_alert_message(sendto, subject, message=None):
    """
    Send a message to Spark indicating that a new Zabbix alert was received.

    This function takes the information received from Zabbix as inputs and
    formats them into a Spark message for the given recipient.

    Args:
        sendto (str): The Spark recipient who will receive the message. The
            value may be the email address of a Spark user which indicates the
            recipient is a person or it may be a valid Spark room id. The
            function will examine the value it receives and "do the right
            thing" based on whether it's an email address or a room id.
        subject (str): The subject of the Zabbix alert.
        message (str): The message body of the Zabbix alert.

    """

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
    """
    Authenticate API requests by checking for a valid token in the request.

    The API token is configured in the
    :py:attr:`zpark.default_settings.ZPARK_API_TOKEN` config parameter in
    ``app.cfg``. A client that calls a Zpark API endpoint must pass the same
    value as configured for :py:attr:`zpark.default_settings.ZPARK_API_TOKEN`
    via the ``Token`` header in the HTTP request. The request is successfully
    authenticated if the ``Token`` header value matches the
    :py:attr:`zpark.default_settings.ZPARK_API_TOKEN` value. The request fails
    authentication if the values differ or if the client didn't provide a
    ``Token`` header.

    Zpark **must** be configured with a static token in the
    :py:attr:`zpark.default_settings.ZPARK_API_TOKEN` config parameter. If this
    parameter is set to :py:obj:`None` (which is the default), the app will
    reject incoming API requests as a safety measure.

    Returns:

        - This is a decorator function so it returns the wrapped function
          when authentication is successful.
        - When authentication fails, the decorator calls the
          :py:func:`flask.abort` function with an appropriate HTTP status
          code.

    """

    @wraps(func)
    def decorated(*args, **kwargs):
        req_token = request.headers.get('Token', None)
        our_token = current_app.config['ZPARK_API_TOKEN']

        if our_token is None:
            current_app.logger.error("Request rejected: ZPARK_API_TOKEN"
                                     " must be set in app.cfg")
            abort(500)

        if req_token is None:
            current_app.logger.warning("Request rejected: client"
                                      " did not send a Token header")
            abort(401)

        if req_token == our_token:
            return func(*args, **kwargs)
        else:
            current_app.logger.warning("Request rejected: Invalid"
                                       " Token header received from"
                                       " client")
            abort(401)

    return decorated

