"""
This module documents the default settings for the Zpark app.

To override a default setting with your own:

    cp default_settings.py ../app.cfg
    $EDITOR ../app.cfg

Settings in app.cfg will override the defaults. If you modify this file
instead of creating app.cfg, you will lose all of your settings when you
upgrade Zpark to a new version.

There are some settings that MUST be overridden. Eg, usernames and passwords.

This file (and app.cfg) are interpreted by Python and must be valid
Python syntax.
"""

#
# The following settings MUST be configured in app.cfg
#

"""
ZPARK_API_TOKEN

This token is used by consumers of the Zpark bot's API to authenticate
themselves. If consumers don't provide the correct token, their API
requests will be ignored. Most notably, this token value is used in
the zpark_alert.sh script on the Zabbix server.

A value of None will disable the token and allow anyone to call the
Zpark API. This is almost certainly not what you want.

You can securely generate this token with the command:

    openssl rand 16 -hex
"""
#ZPARK_API_TOKEN = <generate this with "openssl rand 16 -hex">


"""
SPARK_ACCESS_TOKEN

This token is used by Zpark to authenticate itself to the Spark API. You
will receive this token when you register a new bot account at
https://developer.ciscospark.com/apps.html. This token is *required* in
order for Zpark to function.
"""
SPARK_ACCESS_TOKEN = None


"""
SPARK_WEBHOOK_SECRET

This secret is used by Spark to authenticate itself to the Zpark API. The
Spark webhook callback will use this secret to generate a SHA1 HMAC of the
callback payload. Zpark will ignore the callback unless the HMAC is present
and correct. This is a form of access control to ensure that only webhook
callbacks received from Spark will be processed. More info on this
mechanism can be seen here:
https://developer.ciscospark.com/webhooks-explained.html#auth

You can securely generate this token with the command:

    openssl rand 16 -hex
"""
#SPARK_WEBHOOK_SECRET = <generate this with "openssl rand 16 -hex">


"""
CELERY_BROKER_URL

The URL by which Celery will access the message broker service. The example
given is appropriate for a RabbitMQ broker. More information on brokers
and how to configure them is here:
http://docs.celeryproject.org/en/latest/getting-started/brokers/index.html
"""
CELERY_BROKER_URL = 'ampq://user:pass@hostname/vhost'


"""
ZABBIX_SERVER_URL

The URL for the Zabbix server. The URL must include 'http://' or 'https://'
and can be either a fully-qualified domain name or an IP address.
"""
ZABBIX_SERVER_URL = 'http://zabbix.your.domain/zabbix'


"""
ZABBIX_USERNAME
ZABBIX_PASSWORD

The username and password of an account on the Zabbix server that has
access to query the Zabbix API. This account does not need frontend access
but does require read-only access to all host groups.
"""
ZABBIX_USERNAME = 'username'
ZABBIX_PASSWORD = 'password'


"""
ZPARK_SERVER_URL

The URL where the Zpark API is reachable. The URL must include 'http://' or
'https://', a fully-qualfied domain name or IP address, a port number (if
not running on port 80 or 443) and the directory structure (if not running
at the top level of the domain). Examples:

    https://zpark.your.domain/
    https://www.your.domain/zpark
    http://198.18.100.100:5555/zpark

This URL is used by Spark when a webhook callback is sent. If Spark can't
access the Zpark URL, you will not be able to issue commands to the bot.
"""
#ZPARK_SERVER_URL = 'https://your.spark.bot.url'


#
# Logging configuration. Default is to log to syslog using
# the LOCAL6 facility.
#
# The API_LOG_* options configure logging for the Zpark API; ie, the
# bits of Zpark that handle requests to the API. The logging done
# by the Celery workers is controlled by the WORKER_LOG_* options.

"""
API_LOG_HANDLER

Configures the handler (and ultimately the destination) of the Zpark API log
messages. Refer to the logging.handlers module documentation for
proper syntax and considerations.

The format specified by API_LOG_FORMAT will automatically be applied to this
handler by Zpark.
"""
API_LOG_HANDLER = {
        'class': 'logging.handlers.SysLogHandler',
        'address': '/dev/log',
        'facility': 'local6',
        'level': 'INFO'
}

API_LOG_FORMAT = ('API/%(levelname)s: %(message)s'
                  ' [in %(pathname)s:%(lineno)d]'
                  ' [client:%(client_ip)s method:"%(method)s" url:"%(url)s"'
                  ' ua:"%(user_agent)s"]')

"""
WORKER_LOG_HANDLER

Configures the handler (and ultimately the destination) of the Zpark task
worker log messages. Refer to the logging.handlers module documentation for
proper syntax and considerations.

The format specified by WORKER_LOG_FORMAT and WORKER_TASK_LOG_FORMAT will
automatically be applied to this handler by Zpark.

    - WORKER_LOG_FORMAT: used for messages logged by Celery workers about the
        maintenance and status of task operations.
    - WORKER_TASK_LOG_FORMAT: used for messages logged by tasks that Celery
        is executing.
"""
WORKER_LOG_HANDLER = {
        'class': 'logging.handlers.SysLogHandler',
        'address': '/dev/log',
        'facility': 'local6',
        'level': 'INFO'
}

WORKER_LOG_FORMAT = ('Worker/%(levelname)s: %(processName)s:'
                     ' %(message)s')
WORKER_TASK_LOG_FORMAT = ('WorkerTask/%(levelname)s: %(processName)s:'
                          ' %(task_name)s[%(task_id)s] %(message)s')

