"""
The :py:mod:`zpark.default_settings` module documents the default settings for
the Zpark app.

To override a default setting with your own::

    cp default_settings.py ../app.cfg
    $EDITOR ../app.cfg

Settings in ``app.cfg`` will override the defaults. If you modify
:py:mod:`zpark.default_settings` instead of creating ``app.cfg``, you will lose
all of your settings when you upgrade Zpark to a new version.

There are some settings that **must** be overridden. Eg, usernames and passwords.

This module (and ``app.cfg``) are interpreted by Python and must be valid
Python syntax.
"""

#
# The following settings MUST be configured in app.cfg
#

ZPARK_API_TOKEN = None
"""
This token is used by consumers of the Zpark bot's API to authenticate
themselves. If consumers don't provide the correct token, their API
requests will be ignored. Most notably, this token value is used in
the ``zpark_alert.sh`` script on the Zabbix server.

A value of ``None`` will cause all API requests to be rejected.

You can securely generate this token with the command::

    openssl rand 16 -hex
"""


SPARK_ACCESS_TOKEN = None
"""
This token is used by Zpark to authenticate itself to the Spark API. You
will receive this token when you register a new bot account at
https://developer.ciscospark.com/apps.html. This token is **required** in
order for Zpark to function.
"""


SPARK_WEBHOOK_SECRET = None
"""
This secret is used by Spark to authenticate itself to the Zpark API. The
Spark webhook callback will use this secret to generate a SHA1 HMAC of the
callback payload. Zpark will ignore the callback unless the HMAC is present
and correct. This is a form of access control to ensure that only webhook
callbacks received from Spark will be processed. More info on this
mechanism can be found here:
https://developer.ciscospark.com/webhooks-explained.html#auth

You can securely generate this token with the command::

    openssl rand 16 -hex
"""


CELERY_BROKER_URL = 'amqp://user:pass@hostname/vhost'
"""
The URL by which Celery will access the message broker service. The example
given is appropriate for a RabbitMQ broker. More information on brokers
and how to configure them is here:
http://docs.celeryproject.org/en/latest/getting-started/brokers/index.html
"""


ZABBIX_SERVER_URL = 'http://localhost/zabbix'
"""
The URL for the Zabbix server. The URL must include the scheme (eg, ``http`` or
``https``) and can be either a fully-qualified domain name or an IP address.
Examples::

    http://zabbix.your.domain/zabbix
    https://198.18.100.200/zabbix
"""


ZABBIX_USERNAME = 'username'
"""
The username of an account on the Zabbix server that has access to query the
Zabbix API. This account does not need frontend access but does require
read-only access to all host groups.
"""


ZABBIX_PASSWORD = 'password'
"""
The password for the account specified by :py:attr:`ZABBIX_USERNAME`.
"""


ZPARK_SERVER_URL = None
"""
The URL where the Zpark API is reachable. The URL must include the scheme
(either ``http`` or ``https``), a fully-qualfied domain name or IP address, a
port number (if not running on port 80 or 443) and the directory structure (if
not running at the top level of the domain). Examples::

    https://zpark.your.domain/
    https://www.your.domain/zpark
    http://198.18.100.100:5555/zpark

This URL is used by Spark when a webhook callback is sent. If Spark can't
access the Zpark URL, you will not be able to issue commands to the bot.
"""


SPARK_TRUSTED_USERS = [None]
"""
This is a :py:class:`list` of Spark users that are allowed to send commands to
Zpark. This is an optional access control mechanism to limit which Spark users
are able to query your Zabbix server via Zpark.

The list must contain the email addresses associated with the Spark users
that are to be trusted or may contain a list of domains in the format of
``@domain.com`` that are to be trusted. The list may contain a mix of
email addresses and domains. Example::

    SPARK_TRUSTED_USERS = ['user@example.com', '@example.org']

If set to an empty list (``[]``), the access check is disabled.

The default setting treats *all* users as untrusted.

.. versionchanged:: 1.1.0
   Specifying domain names became supported.
"""


#
# The following settings may optionally be configured in app.cfg
#

ZPARK_CONTACT_INFO = None
"""
Sets the contact information for you, the bot owner, which will be displayed
to any user that sends the "hello" command to the bot. This allows
someone to determine who to reach if the bot is not responding or is
encountering errors. The default setting of ``None`` will prevent any contact
information from being displayed. Example::

    ZPARK_CONTACT_INFO = 'Charlie Root (root@example.com)'

.. versionadded:: 1.1.0
"""

#
# Logging configuration. Default is to log to syslog using
# the LOCAL6 facility.
#
# The API_LOG_* options configure logging for the Zpark API; ie, the
# bits of Zpark that handle requests to the API. The logging done
# by the Celery workers is controlled by the WORKER_LOG_* options.

API_LOG_HANDLER = {
        'class': 'logging.handlers.SysLogHandler',
        'address': '/dev/log',
        'facility': 'local6',
        'level': 'INFO'
}
"""
Configures the handler (and ultimately the destination) of the Zpark API log
messages. Refer to the :py:mod:`logging.handlers` module documentation for
proper syntax and considerations.

The default log destination is syslog with facility ``LOCAL6`` and log level
``INFO``.

The format specified by :py:attr:`API_LOG_FORMAT` will automatically be applied to
this handler.
"""


API_LOG_FORMAT = ('API/%(levelname)s: %(message)s'
                  ' [in %(pathname)s:%(lineno)d]'
                  ' [client:%(client_ip)s method:"%(method)s" url:"%(url)s"'
                  ' ua:"%(user_agent)s"]')
"""
Configures the format of log messages logged via the :py:attr:`API_LOG_HANDLER`
handler.
"""


WORKER_LOG_HANDLER = {
        'class': 'logging.handlers.SysLogHandler',
        'address': '/dev/log',
        'facility': 'local6',
        'level': 'INFO'
}
"""
Configures the handler (and ultimately the destination) of the task
worker log messages. Refer to the :py:mod:`logging.handlers` module
documentation for proper syntax and considerations.

The default log destination is syslog with facility ``LOCAL6`` and log level
``INFO``.

The format specified by :py:attr:`WORKER_LOG_FORMAT` and
:py:attr:`WORKER_TASK_LOG_FORMAT` will automatically be applied to this
handler.
"""


WORKER_LOG_FORMAT = ('Worker/%(levelname)s: %(processName)s:'
                     ' %(message)s')
"""
Configures the format for messages logged by Celery workers about the
maintenance and status of task operations. Eg: a log message is emitted when
a task is received into the queue.
"""

WORKER_TASK_LOG_FORMAT = ('WorkerTask/%(levelname)s: %(processName)s:'
                          ' %(task_name)s[%(task_id)s] %(message)s')
"""
Configures the format for messages logged by tasks that Celery is executing.
Eg: a message might be emitted when a new Spark message is sent.
"""

