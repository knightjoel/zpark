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
from zpark.log import setup_celery_logging
from zpark.utils import obj_to_dict


__all__ = [
    'task_dispatch_spark_command',
    'task_send_spark_message'
]

logger = get_task_logger(__name__)


@celery.signals.setup_logging.connect
def setup_logging(**kwargs):
    setup_celery_logging(app, celery_app, __name__, **kwargs)


@celery_app.task(bind=True, default_retry_delay=20, max_retries=3)
def task_dispatch_spark_command(self, webhook_data):
    """
    Parse the incoming webhook data and run the appropriate task to handle
    the request.

    There is an assumption here that the API layer has checked that the
    webhook data is for ``message/create`` and not for any other
    resource/event combination.

    Commands are case in-sensitive (makes it easier on mobile devices that
    want to capitalize the first word of sentences).

    Args:
        webhook_data (dict): The JSON data that the Spark webhook provided.

    Returns:
        bool:

            - :py:obj:`False`: When the command could not be dispatched.
            - :py:obj:`True`: When the command was successfully dispatched.

    Raises:
        :py:exc:`ciscosparkapi.SparkApiError`: The
            Spark API returned an error and despite retrying the API call some
            number of times, the error persisted.

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
        err = "The Spark API returned an error: {}".format(e)
        logger.error(err)
        self.retry(exc=e)

    try:
        logger.debug('Querying Spark for room id {}'.format(msg.roomId))
        room = spark_api.rooms.get(msg.roomId)
    except SparkApiError as e:
        err = "The Spark API returned an error: {}".format(e)
        logger.error(err)
        self.retry(exc=e)

    # strip bot's name from the start of the command if the message was
    # received in a group room (this is an artifact of how Spark works).
    if room.type == 'group':
        # the marked-up version of the message wraps the bot name in
        # <spark-mention> tags which makes it easy for us to find out
        # our own name dynamically. note the limitation with this is that
        # we expect the bot to be the first and only person mentioned in
        # the message.
        m = (re.match('^<spark-mention[^>]+>([^<]+)<\/spark-mention>',
                      msg.html))
        if m is not None:
            bot_name = m.group(1)
            # strip bot name and some delimiting characters from the start
            # of the plain text version of the message. use the plain text
            # version so we don't have to worry about additional markup
            # in the message. what's left will be the bot command.
            cmd = re.split('^' + bot_name + '[,:;]*\s*', msg.text, 1)[1]
        else:
            logger.info('Received a message from {} in group room "{}"'
                        ' that did not contain the spark-mention tag.'
                        ' The command is being ignored. Possible Spark'
                        ' issue?'
                    .format(msg.personEmail, room.title))
            return False
    # in a 1-on-1 room, we'll just receive the command, no mention
    else:
        cmd = msg.text

    if len(cmd) > 79:
        logger.info('Received a command from {} that is too long:'
                ' allowed chars: 79, received chars: {}. Ignoring.'
                .format(payload['personEmail'], len(cmd)))
        return False

    # validate the command looks sane and safe
    if not re.fullmatch('^[a-zA-Z0-9 ]+$', cmd):
        logger.info('Received a command from {} with invalid characters in it:'
                ' "{}"'.format(payload['personEmail'], cmd))
        return False

    try:
        logger.debug('Querying Spark for person id {}'
                .format(webhook_data['actorId']))
        caller = spark_api.people.get(webhook_data['actorId'])
    except SparkApiError as e:
        err = "The Spark API returned an error: {}".format(e)
        logger.error(err)
        self.retry(exc=e)

    room_dict = obj_to_dict(room)
    caller_dict = obj_to_dict(caller)

    dispatch_map = {
        'hello': (
            task_say_hello,
            (room_dict, caller_dict)
        ),
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
        logger.info('Received an unknown command from {}: "{}"'
                .format(msg.personEmail, cmd))
        return False

    asynctask = task[0].apply_async(args=(*task[1],))
    logger.info('Dispatched command "{}" received from {} to task {}'
            ' with taskid {}'
            .format(cmd, msg.personEmail, task[0], asynctask.id))
    return True


@celery_app.task(bind=True, default_retry_delay=20, max_retries=3)
def task_say_hello(self, room, caller):
    """
    Send the "hello" message to a Spark space.

    Args:
        room: A :py:obj:`dict` that identifies the Spark space (room) where
            the output should be sent. Note the identified room can be either
            a group room (> 2 people) or a 1-on-1 room.
        caller: A :py:obj:`dict` that has been built from the attributes of
            a :py:obj:`ciscosparkapi.Person` object that identifies the Spark
            user that requested this report. See also :py:func:`obj_to_dict`.

    Raises:
        :py:exc:`ciscosparkapi.SparkApiError`: The
            Spark API returned an error and despite retrying the API call some
            number of times, the error persisted.

    """

    text = jinja2.get_template('say_hello.txt').render(
            caller=caller,
            room=room,
            zpark_contact_info=app.config['ZPARK_CONTACT_INFO'])
    markdown = jinja2.get_template('say_hello.md').render(
            caller=caller,
            room=room,
            zpark_contact_info=app.config['ZPARK_CONTACT_INFO'])
    try:
        task_send_spark_message(room, text, markdown)
        logger.info('Said hello to {} in room "{}"'
                .format(caller['emails'][0], room['title']))
    except SparkApiError as e:
        err = "The Spark API returned an error: {}".format(e)
        logger.error(err)
        self.retry(exc=e)


@celery_app.task(bind=True, default_retry_delay=20, max_retries=3)
def task_send_spark_message(self, to, text, md=None):
    """
    Send a message to a Spark destination: either a room or a person.

    The function does a little introspection on the ``to`` argument to
    determine if the intended recipient is a person or a room. It then
    forms the proper data structure to pass to the Spark API.

    Args:
        to (dict): Represents either the person or the room that the
            message will be sent to. Must contain keys which would normally
            be expected in a :py:obj:`ciscosparkapi.Person` or
            :py:obj:`ciscosparkapi.Room` object. See also
            :py:func:`obj_to_dict`.
        text (str): The text of the message to send.
        md (str): The message to be sent with markup formatting.

    Raises:
        :py:exc:`TypeError`: If the ``to`` argument is not a :py:obj:`dict`.
        :py:exc:`ciscosparkapi.SparkApiError`: The
            Spark API returned an error and despite retrying the API call some
            number of times, the error persisted.

    """

    if 'emails' in to:
        msg = dict(toPersonEmail=to['emails'][0])
    else:
        msg = dict(roomId=to['id'])

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
        err = "The Spark API returned an error: {}".format(e)
        logger.error(err)
        self.retry(exc=e)


@celery_app.task(bind=True, default_retry_delay=15, max_retries=3)
def task_report_zabbix_active_issues(self, room, caller, limit=10):
    """
    Output a list of active Zabbix issues to a Spark space.

    Args:
        room: A :py:obj:`dict` that identifies the Spark space (room) where
            the output should be sent. Note the identified room can be either
            a group room (> 2 people) or a 1-on-1 room.
        caller: A :py:obj:`dict` that has been built from the attributes of
            a :py:obj:`ciscosparkapi.Person` object that identifies the Spark
            user that requested this report. See also :py:func:`obj_to_dict`.
        limit: An :py:obj:`int` indicating the maximum number of issues to
            include in the output.

    Raises:
        :py:exc:`ciscosparkapi.SparkApiError`: The
            Spark API returned an error and despite retrying the API call some
            number of times, the error persisted.
        :py:exc:`pyzabbix.ZabbixAPIException`: The Zabbix server API returned
            an error and despite retrying the API call some number of times,
            the error persisted.

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
        logger.info('Reported active Zabbix issues to {} room "{}"'
                .format(room['type'], room['title']))
    except SparkApiError as e:
        err = "The Spark API returned an error: {}".format(e)
        logger.error(err)
        self.retry(exc=e)


@celery_app.task(bind=True, default_retry_delay=15, max_retries=3)
def task_report_zabbix_server_status(self, room, caller):
    """
    Output the Zabbix server status as seen in the web ui dashboard.

    Args:
        room: A :py:obj:`dict` that identifies the Spark space (room) where
            the output should be sent. Note the identified room can be either
            a group room (> 2 people) or a 1-on-1 room.
        caller: A :py:obj:`dict` that has been built from the attributes of
            a :py:obj:`ciscosparkapi.Person` object that identifies the Spark
            user that requested this report. See also :py:func:`obj_to_dict`.

    Raises:
        :py:exc:`ciscosparkapi.SparkApiError`: The
            Spark API returned an error and despite retrying the API call some
            number of times, the error persisted.
        :py:exc:`pyzabbix.ZabbixAPIException`: The Zabbix server API returned
            an error and despite retrying the API call some number of times,
            the error persisted.

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
        logger.info('Reported Zabbix server stats to {} room "{}"'
                .format(room['type'], room['title']))
    except SparkApiError as e:
        err = "The Spark API returned an error: {}".format(e)
        logger.error(err)
        self.retry(exc=e)


def notify_of_failed_command(room, caller, retries, max_retries,
                             exc):
    """
    Notify a Spark space of a failure to respond to a command request.

    This is a utility function called by a task when there is a failure
    to respond to a command issued by a Spark user. This function takes
    care to only notify the Spark user an appropriate number of times and
    not on each retry attempt of the calling task.

    Args:
        room: A :py:obj:`dict` that identifies the Spark space (room) where
            the output should be sent. Note the identified room can be either
            a group room (> 2 people) or a 1-on-1 room.
        caller: A :py:obj:`dict` that has been built from the attributes of
            a :py:obj:`ciscosparkapi.Person` object that identifies the Spark
            user that requested this report. See also :py:func:`obj_to_dict`.
        retries: An :py:obj:`int` indicating the number of retry attempts that
            the calling task has already attempted (ie, does not include the
            current try).
        max_retries: An :py:obj:`int` indicating the maximum number of retry
            attempts that the calling task is allowed. Unintuitively, this
            function can still be called when retries == max_retries + 1;
            the calling task uses this condition to indicate it should stop
            retrying and return, however it's likely the calling task calls
            this function prior to performing this evaluation.
        exc: The exception that was raised in the calling task which caused
            the need for a user notification in the first place.

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
            task_send_spark_message.apply(args=(room, text, markdown))
            logger.info('Notified {} room "{}" that a command'
                        ' could not be answered'
                    .format(room['type'], room['title']))
        except SparkApiError as e:
            logger.error('Unable to notify {} room "{}" that a'
                         ' command could not be answered:'
                         ' Spark API Error: {}'
                    .format(room['type'], room['title'], e))
            raise
    elif retries > max_retries:
        # Since this is an unintuitively valid condition in which this
        # function may be called, code it and make it explicitly clear that
        # while it's a valid condition, no actions are taken.
        pass

