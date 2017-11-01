import datetime as dt
import os

from celery import Celery
import celery.signals
from celery.utils.log import get_task_logger
from ciscosparkapi import SparkApiError
from pyzabbix import ZabbixAPIException

from zpark import app, basedir, jinja2, spark_api, zabbix_api
from zpark import celery as celery_app


logger = get_task_logger(__name__)


@celery_app.task(bind=True, default_retry_delay=20, max_retries=3)
def task_send_spark_message(self, to, text, md=None):
    # crude but good enough to tell the difference between roomId and
    # toPersonEmail inputs. this logic fails if we're passed a personId.
    if '@' in to:
        msg = dict(toPersonEmail=to)
    else:
        msg = dict(roomId=to)

    msg.update(text=text)

    if md is not None:
        msg.update(markdown=md)

    try:
        msg = spark_api.messages.create(**msg)

        logger.info("New Spark message created: toPersonEmail:{} "
                    "roomId:{} messageId:{}"
                        .format(msg.toPersonEmail, msg.roomId, msg.id))
        return msg.id
    except SparkApiError as e:
        msg = "The Spark API returned an error: {}".format(e)
        logger.error(msg)
        self.retry(exc=e)


@celery_app.task(bind=True, default_retry_delay=15, max_retries=3)
def task_report_zabbix_active_issues(self, roomId, roomType, caller, limit=10):
    """
    Output a list of active Zabbix issues to a Spark space.

    Args:
        roomId: Identifies the Spark space (room) where the output should be
            sent. Note the identified room can be either a group room (> 2
            people) or a 1-on-1 room.
        roomType: Indicates whether the given roomId is a group or 1-on-1
            room.
        caller: A string in the format of an email address that identifies the
            Spark user that requested this report.
        limit: The maximum number of issues to include in the output.

    Returns:
        None

    Raises:
        ValueError: The roomType was not one of the expected values.
        SparkApiError: The Spark API returned an error and
            despite retrying the API call some number of times, the error
            persisted. SparkApiError is re-raised to bubble the error
            down the stack.
        ZabbixAPIException: The Zabbix server API returned an error and
            despite retrying the API call some number of times, the error
            persisted. ZabbixAPIException is re-raised to bubble the error
            down the stack.
    """

    if roomType not in ('direct', 'group'):
        raise ValueError('roomType must be "direct" or "group": '
                'got: "{}"'.format(roomType))

    try:
        logger.debug('Querying Zabbix server at {} for active triggers'
                .format(app.config['ZABBIX_SERVER_URL']))
        triggers = zabbix_api.trigger.get(only_true=1,
                                          skipDependent=1,
                                          monitored=1,
                                          active=1,
                                          expandDescription=1,
                                          withLastEventUnacknowledged=1,
                                          sortfield=['lastchange', 'priority',
                                                     'hostname'],
                                          sortorder=['DESC', 'DESC', 'ASC'],
                                          selectHosts=['host'],
                                          filter={'value':1},
                                          limit=limit)
        logger.debug('Retrieved {} trigger(s) from Zabbix'
                .format(len(triggers)))
    except ZabbixAPIException as e:
        notify_of_failed_command(roomId, roomType, caller,
                                 self.request.retries, self.max_retries, e)
        self.retry(exc=e)

    issues = []
    for t in triggers:
        issues.append({
            'host': t['hosts'][0]['host'],
            'description': t['description'],
            'lastchangedt': dt.datetime.fromtimestamp(int(t['lastchange']))
            })

    text = jinja2.get_template('report_zabbix_active_issues.txt').render(
            issues=issues,
            caller=caller,
            limit=limit,
            roomId=roomId,
            roomType=roomType)
    markdown = jinja2.get_template('report_zabbix_active_issues.md').render(
            issues=issues,
            caller=caller,
            limit=limit,
            roomid=roomId,
            roomtype=roomType)
    try:
        task_send_spark_message(roomId, text, markdown)
        logger.info('Reported active Zabbix issues to room {} (type: {})'
                .format(roomId, roomType))
    except SparkApiError as e:
        msg = "The Spark API returned an error: {}".format(e)
        logger.error(msg)
        self.retry(exc=e)


@celery.signals.setup_logging.connect
def celery_setup_logging(loglevel=None, logfile=None, fmt=None,
                         colorize=None, **kwargs):
    import logging
    import logging.config
    import celery.app.log

    logconf = {
        'version': 1,
        'formatters': {
            'taskfmt': {
                '()': celery.app.log.TaskFormatter,
                'fmt': celery_app.conf.worker_task_log_format
            },
            'workerfmt': {
                'format': celery_app.conf.worker_log_format
            },
        },
        'handlers': {
            'taskh': {
                'level': loglevel or logging.INFO,
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(basedir, 'logs/task.log'),
                'maxBytes': app.config['APP_LOG_MAXBYTES'],
                'backupCount': app.config['APP_LOG_ROTATECOUNT'],
                'formatter': 'taskfmt'
            },
            'workh': {
                'level': loglevel or logging.INFO,
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(basedir, 'logs/task.log'),
                'maxBytes': app.config['APP_LOG_MAXBYTES'],
                'backupCount': app.config['APP_LOG_ROTATECOUNT'],
                'formatter': 'workerfmt'
            },
            'nullh': {
                'level': loglevel or logging.INFO,
                'class': 'logging.NullHandler',
            }
        },
        'loggers': {
            'celery': {
                'handlers': ['workh'],
                'level': loglevel or logging.INFO
            },
            'celery.task': {
                'handlers': ['taskh'],
                'level': loglevel or logging.INFO,
                'propagate': 0
            },
            # Celery will make this logger a child of 'celery.task' when
            # the get_task_logger(__name__) function is called at the top
            # of this module. Propagate logs upwards to 'celery.task' which
            # will emit the log message.
            __name__: {
                'handlers': ['nullh'],
                'level': loglevel or logging.INFO,
                'propagate': 1
            }
        },
    }

    logging.config.dictConfig(logconf)


def notify_of_failed_command(roomId, roomType, caller, retries, max_retries,
                             exc):
    """
    Notify a Spark space of a failure to respond to a command request.

    This is a utility function called by a task when there is a failure
    to respond to a command issued by a Spark user. This function takes
    care to only notify the Spark user an appropriate number of times and
    not on each retry attempt of the calling task.

    Args:
        roomId: Identifies the Spark space (room) where the output should be
            sent. Note the identified room can be either a group room (> 2
            people) or a 1-on-1 room.
        roomType: Indicates whether the given roomId is a group or 1-on-1
            room.
        caller: A string in the format of an email address that identifies the
            Spark user that requested this report.
        retries: An integer indicating the number of retry attempts that the
            calling task has already attempted (ie, does not include the
            current try).
        max_retries: An integer indicating the maximum number of retry
            attempts that the calling task is allowed. Unintuitively, this
            function can still be called when retries == max_retries + 1;
            the calling task uses this condition to indicate it should stop
            retrying and return, however it's likely the calling task calls
            this function prior to performing this evaluation.
        exc: The exception that was raised in the calling task which caused
            the need for a user notification in the first place.

    Returns:
        None
    """

    logger.error('There was an error responding to a command.'
            ' Exception: {}'.format(exc))
    if retries == 0:
        # this is the first try
        text = jinja2.get_template('zpark_command_error.txt').render(
                caller=caller,
                roomId=roomId,
                roomType=roomType,
                retries=retries)
        markdown = jinja2.get_template('zpark_command_error.md').render(
                caller=caller,
                roomid=roomId,
                roomtype=roomType,
                retries=retries)
        try:
            task_send_spark_message.apply(args=(roomId, text, markdown))
            logger.info('Notified room {} (type: {}) that a command'
                        ' could not be answered'
                    .format(roomId, roomType))
        except SparkApiError as e:
            logger.error('Unable to notify room {} (type: {}) that a'
                         ' command could not be answered:'
                         ' Spark API Error: {}'
                    .format(roomId, roomType, e))
            raise
    elif retries > max_retries:
        # Since this is an unintuitively valid condition in which this
        # function may be called, code it and make it explicitly clear that
        # while it's a valid condition, no actions are taken.
        pass

