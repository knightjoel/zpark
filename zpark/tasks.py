import datetime as dt
import os
import re

from celery import Celery
import celery.signals
from celery.utils.log import get_task_logger
from ciscosparkapi import SparkApiError
from pyzabbix import ZabbixAPIException

from zpark import app, basedir, jinja2, spark_api, zabbix_api
from zpark import celery as celery_app
from zpark.utils import obj_to_dict


__all__ = [
    'task_dispatch_spark_command',
    'task_send_spark_message'
]

logger = get_task_logger(__name__)


@celery_app.task(bind=True, default_retry_delay=20, max_retries=3)
def task_dispatch_spark_command(self, webhook_data):
    """
    Parse the incoming webhook data and run the appropriate task to handle
    the request.

    There is an assumption here that the API layer has checked that the
    webhook data is for a message creation and not for any other
    resource/event combination.

    Commands are case in-sensitive (makes it easier on mobile devices that
    want to capitalize the first word of sentences).

    Args:
        webhook_data (dict): The JSON data that the Spark webhook provided.

    Returns:
        False: When the command could not be dispatched.
        True: When the command was successfully dispatched.

    Raises:
        SparkApiError: The Spark API returned an error and
            despite retrying the API call some number of times, the error
            persisted. SparkApiError is re-raised to bubble the error
            down the stack.
    """

    payload = webhook_data['data']
    logger.debug('Dispatching webhook request: id:{} name:"{}" actorId:{}'
            ' [id:{} roomId:{} personEmail:{}]'
            .format(webhook_data['id'],
                    webhook_data['name'],
                    webhook_data['actorId'],
                    payload['id'],
                    payload['roomId'],
                    payload['personEmail']))
    try:
        logger.debug('Querying Spark for message id {}'.format(payload['id']))
        msg = spark_api.messages.get(payload['id'])
    except SparkApiError as e:
        msg = "The Spark API returned an error: {}".format(e)
        logger.error(msg)
        self.retry(exc=e)

    cmd = msg.text
    ellipsis = ' (...)' if len(cmd) > 79 else ''

    # validate the command looks sane and safe
    if not re.fullmatch('^[a-zA-Z0-9 ]+$', msg.text):
        logger.warning('Received a command with invalid characters in it:'
                ' "{}{}"'.format(cmd[:79], ellipsis))
        return False

    try:
        logger.debug('Querying Spark for room id {}'.format(msg.roomId))
        room = spark_api.rooms.get(msg.roomId)
    except SparkApiError as e:
        msg = "The Spark API returned an error: {}".format(e)
        logger.error(msg)
        self.retry(exc=e)

    try:
        logger.debug('Querying Spark for person id {}'
                .format(webhook_data['actorId']))
        caller = spark_api.people.get(webhook_data['actorId'])
    except SparkApiError as e:
        msg = "The Spark API returned an error: {}".format(e)
        logger.error(msg)
        self.retry(exc=e)

    # strip bot's name from the start of the command
    if room.type == 'group':
        cmd = re.split('[^a-zA-Z0-9]+', cmd, 1)[1]

    room_dict = obj_to_dict(room)
    caller_dict = obj_to_dict(caller)

    dispatch_map = {
        'show issues': (
            task_report_zabbix_active_issues,
            (room_dict, caller_dict)
        ),
        'show status': (
            task_report_zabbix_server_status,
            (room_dict, caller_dict)
        ),
    }

    task = dispatch_map.get(cmd.lower(), None)
    if not task:
        logger.debug('Received an unknown command:"{}{}" from:{}'
                .format(cmd[:79], ellipsis, msg.personEmail))
        return False

    asynctask = task[0].apply_async(args=(*task[1],))
    logger.info('Dispatched command "{}{}" to task {} with taskid {}'
            .format(cmd[:79], ellipsis, task[0], asynctask.id))
    return True


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
def task_report_zabbix_active_issues(self, room, caller, limit=10):
    """
    Output a list of active Zabbix issues to a Spark space.

    Args:
        room: A dict that identifies the Spark space (room) where the output
            should be sent. Note the identified room can be either a group
            room (> 2 people) or a 1-on-1 room.
        caller: A dict that identifies the Spark user that requested this
            report.
        limit: The maximum number of issues to include in the output.

    Returns:
        None

    Raises:
        SparkApiError: The Spark API returned an error and
            despite retrying the API call some number of times, the error
            persisted. SparkApiError is re-raised to bubble the error
            down the stack.
        ZabbixAPIException: The Zabbix server API returned an error and
            despite retrying the API call some number of times, the error
            persisted. ZabbixAPIException is re-raised to bubble the error
            down the stack.
    """

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
        notify_of_failed_command(room, caller,
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
            room=room)
    markdown = jinja2.get_template('report_zabbix_active_issues.md').render(
            issues=issues,
            caller=caller,
            limit=limit,
            room=room)
    try:
        task_send_spark_message(room, text, markdown)
        logger.info('Reported active Zabbix issues to room {} (type: {})'
                .format(room['id'], room['type']))
    except SparkApiError as e:
        msg = "The Spark API returned an error: {}".format(e)
        logger.error(msg)
        self.retry(exc=e)


@celery_app.task(bind=True, default_retry_delay=15, max_retries=3)
def task_report_zabbix_server_status(self, room, caller):
    """
    Output the Zabbix server status as seen in the web ui dashboard.

    Args:
        room: A dict that identifies the Spark space (room) where the output
            should be sent. Note the identified room can be either a group
            room (> 2 people) or a 1-on-1 room.
        caller: A dict that identifies the Spark user that requested this
            report.

    Returns:
        None

    Raises:
        SparkApiError: The Spark API returned an error and
            despite retrying the API call some number of times, the error
            persisted. SparkApiError is re-raised to bubble the error
            down the stack.
        ZabbixAPIException: The Zabbix server API returned an error and
            despite retrying the API call some number of times, the error
            persisted. ZabbixAPIException is re-raised to bubble the error
            down the stack.
    """

    stats = {}
    try:
        logger.debug('Querying Zabbix server at {} for server status'
                .format(app.config['ZABBIX_SERVER_URL']))

        stats['enabled_hosts_cnt'] = int(zabbix_api.host.get(
                countOutput=1,
                filter={'status':0}))
        stats['disabled_hosts_cnt'] = int(zabbix_api.host.get(
                countOutput=1,
                filter={'status':1}))
        stats['templates_cnt'] = int(zabbix_api.template.get(countOutput=1))
        # The dashboard actually shows items that are enabled, supported and
        # associated with monitored hosts.
        stats['enabled_items_cnt'] = int(zabbix_api.item.get(
                countOutput=1,
                monitored=1,
                filter={'status':0, 'state':0}))
        # The dashboard actually shows items that are disabled, supported
        # or not supported, and that are not associated to templates.
        stats['disabled_items_cnt'] = int(zabbix_api.item.get(
                countOutput=1,
                templated=0,
                filter={'status':1}))
        # The dashboard actually shows items that are enabled and associated
        # with monitored hosts.
        stats['notsupported_items_cnt'] = int(zabbix_api.item.get(
                countOutput=1,
                monitored=1,
                filter={'state':1}))
        # The dashboard actually shows triggers that are enabled and
        # associated with monitored hosts.
        stats['enabled_triggers_cnt'] = int(zabbix_api.trigger.get(
                countOutput=1,
                monitored=1,
                filter={'status':0}))
        # The dashboard actually shows triggers that are disabled and
        # are "plain" (non discovered) triggers.
        stats['disabled_triggers_cnt'] = int(zabbix_api.trigger.get(
                countOutput=1,
                filter={'status':1, 'flags':0}))
        # The dashboard actually shows triggers that are enabled and
        # associated with monitored hosts.
        stats['ok_triggers_cnt'] = int(zabbix_api.trigger.get(
                countOutput=1,
                monitored=1,
                filter={'status':0, 'value':0}))
        # The dashboard actually shows triggers that are enabled and
        # associated with monitored hosts.
        stats['problem_triggers_cnt'] = int(zabbix_api.trigger.get(
                countOutput=1,
                monitored=1,
                filter={'status':0, 'value':1}))
        stats['enabled_httptest_cnt'] = int(zabbix_api.httptest.get(
                countOutput=1,
                monitored=1))
        stats['disabled_httptest_cnt'] = int(zabbix_api.httptest.get(
                countOutput=1,
                filter={'status':1}))

        logger.debug('Retrieved server stats from Zabbix')
    except ZabbixAPIException as e:
        notify_of_failed_command(room, caller,
                                 self.request.retries, self.max_retries, e)
        self.retry(exc=e)

    text = jinja2.get_template('report_zabbix_server_status.txt').render(
            stats=stats,
            caller=caller,
            room=room)
    markdown = jinja2.get_template('report_zabbix_server_status.md').render(
            stats=stats,
            caller=caller,
            room=room)
    try:
        task_send_spark_message(room, text, markdown)
        logger.info('Reported Zabbix server stats to room {} (type: {})'
                .format(room['id'], room['type']))
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


def notify_of_failed_command(room, caller, retries, max_retries,
                             exc):
    """
    Notify a Spark space of a failure to respond to a command request.

    This is a utility function called by a task when there is a failure
    to respond to a command issued by a Spark user. This function takes
    care to only notify the Spark user an appropriate number of times and
    not on each retry attempt of the calling task.

    Args:
        room: A dict that identifies the Spark space (room) where the output
            should be sent. Note the identified room can be either a group
            room (> 2 people) or a 1-on-1 room.
        caller: A dict that identifies the Spark user that requested this
            report.
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
                room=room,
                retries=retries)
        markdown = jinja2.get_template('zpark_command_error.md').render(
                caller=caller,
                room=room,
                retries=retries)
        try:
            task_send_spark_message.apply(args=(room['id'], text, markdown))
            logger.info('Notified room {} (type: {}) that a command'
                        ' could not be answered'
                    .format(room['id'], room['type']))
        except SparkApiError as e:
            logger.error('Unable to notify room {} (type: {}) that a'
                         ' command could not be answered:'
                         ' Spark API Error: {}'
                    .format(room['id'], room['type'], e))
            raise
    elif retries > max_retries:
        # Since this is an unintuitively valid condition in which this
        # function may be called, code it and make it explicitly clear that
        # while it's a valid condition, no actions are taken.
        pass

