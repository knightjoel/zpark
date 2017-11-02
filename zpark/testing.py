from collections import namedtuple
import json
from unittest.mock import PropertyMock, patch

from celery.exceptions import Retry
from ciscosparkapi import SparkApiError
from flask import url_for
from flask_testing import TestCase
from pyzabbix import ZabbixAPIException

import zpark


class BaseTestCase(TestCase):

    def create_app(self):
        zpark.app.config.update(
            DEBUG = False,
            TESTING = True,
            ZPARK_API_TOKEN = 'token12345'
        )
        return zpark.app

    def setUp(self):
        self.sb_api_token = ('Token', zpark.app.config['ZPARK_API_TOKEN'])
        zpark.app.logger.setLevel(999)

    def tearDown(self):
        pass

    def build_fake_webhook_json(self):
        return """{
  "id":"Y2lzY29zcGFyazovL3VzL1dFQkhPT0svZjRlNjA1NjAtNjYwMi00ZmIwLWEyNWEtOTQ5ODgxNjA5NDk3",
  "name":"Guild Chat to http://requestb.in/1jw0w3x1",
  "resource":"messages",
  "event":"created",
  "filter":"roomId=Y2lzY29zcGFyazovL3VzL1JPT00vY2RlMWRkNDAtMmYwZC0xMWU1LWJhOWMtN2I2NTU2ZDIyMDdi",
  "orgId": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi8xZWI2NWZkZi05NjQzLTQxN2YtOTk3NC1hZDcyY2FlMGUxMGY",
  "createdBy": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xZjdkZTVjYi04NTYxLTQ2NzEtYmMwMy1iYzk3NDMxNDQ0MmQ",
  "appId": "Y2lzY29zcGFyazovL3VzL0FQUExJQ0FUSU9OL0MyNzljYjMwYzAyOTE4MGJiNGJkYWViYjA2MWI3OTY1Y2RhMzliNjAyOTdjODUwM2YyNjZhYmY2NmM5OTllYzFm",
  "ownedBy": "creator",
  "status": "active",
  "actorId": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xZjdkZTVjYi04NTYxLTQ2NzEtYmMwMy1iYzk3NDMxNDQ0MmQ",
  "data":{
    "id":"Y2lzY29zcGFyazovL3VzL01FU1NBR0UvMzIzZWUyZjAtOWFhZC0xMWU1LTg1YmYtMWRhZjhkNDJlZjlj",
    "roomId":"Y2lzY29zcGFyazovL3VzL1JPT00vY2RlMWRkNDAtMmYwZC0xMWU1LWJhOWMtN2I2NTU2ZDIyMDdi",
    "personId":"Y2lzY29zcGFyazovL3VzL1BFT1BMRS9lM2EyNjA4OC1hNmRiLTQxZjgtOTliMC1hNTEyMzkyYzAwOTg",
    "personEmail":"person@example.com",
    "created":"2015-12-04T17:33:56.767Z"
  }
}"""


class ApiTestCase(BaseTestCase):

    def setUp(self):
        self.mock_sendmsg_patcher = \
                patch('zpark.tasks.task_send_spark_message.apply_async',
                      autospec=True)
        self.mock_sendmsg = self.mock_sendmsg_patcher.start()
        super(ApiTestCase, self).setUp()

    def tearDown(self):
        self.mock_sendmsg_patcher.stop()
        super(ApiTestCase, self).tearDown()


class ApiV1TestCase(ApiTestCase):

    ### GET /alert endpoint
    def test_alert_get_w_token(self):
        r = self.client.get(url_for('api_v1.alert'),
                            headers=[self.sb_api_token])

        self.assert_405(r)

    def test_alert_get_wo_token(self):
        r = self.client.get(url_for('api_v1.alert'))

        self.assert_405(r)

    ### POST /alert endpoint
    def test_alert_post_valid_alert_direct(self):
        to = u'joel@zpark.packetmischief'
        subject = u'This might ruin your day...'
        message = u'Your data center is on fire'

        type(self.mock_sendmsg.return_value).id = PropertyMock(
                                               return_value='id123abc')

        r = self.client.post(url_for('api_v1.alert'),
                             headers=[self.sb_api_token],
                             data=json.dumps({
                                'to': to,
                                'subject': subject,
                                'message': message
                             }),
                             content_type='application/json')
        self.assert_200(r)
        self.mock_sendmsg.assert_called_once()
        rjson = json.loads(r.data)
        self.assertEqual(rjson['message'], '{}\n\n{}'.format(subject, message))
        self.assertEqual(rjson['to'], to)
        self.assertEqual(rjson['taskid'], 'id123abc')

    def test_alert_post_valid_alert_group(self):
        to = u'roomid1234567'
        subject = u'This might ruin your day...'
        message = u'Your data center is on fire'

        type(self.mock_sendmsg.return_value).id = PropertyMock(
                                            return_value='id123abc')

        r = self.client.post(url_for('api_v1.alert'),
                             headers=[self.sb_api_token],
                             data=json.dumps({
                                'to': to,
                                'subject': subject,
                                'message': message
                             }),
                             content_type='application/json')
        self.assert_200(r)
        self.mock_sendmsg.assert_called_once()
        rjson = json.loads(r.data)
        self.assertEqual(rjson['message'], '{}\n\n{}'.format(subject, message))
        self.assertEqual(rjson['to'], to)
        self.assertEqual(rjson['taskid'], 'id123abc')

    def test_alert_post_valid_alert_wo_token(self):
        to = u'joel@zpark.packetmischief'
        subject = u'This might ruin your day...'
        message = u'Your data center is on fire'

        r = self.client.post(url_for('api_v1.alert'),
                             # no auth token here...
                             data=json.dumps({
                                'to': to,
                                'subject': subject,
                                'message': message
                             }),
                             content_type='application/json')
        self.assert_401(r)

    def _alert_post_missing_input(self, input_):
        r = self.client.post(url_for('api_v1.alert'),
                             headers=[self.sb_api_token],
                             data=json.dumps(input_),
                             content_type='application/json')
        self.assert_status(r, 400)
        self.assertIn(b'Required', r.data)

    def test_alert_post_missing_to(self):
        input_ = {
            # missing 'to'
            'subject': 'subj',
            'message': 'mess'
        }

        self._alert_post_missing_input(input_)

    def test_alert_post_missing_subject(self):
        input_ = {
            # missing 'subject'
            'to': 'joel',
            'message': 'mess'
        }

        self._alert_post_missing_input(input_)

    def test_alert_post_missing_message(self):
        """
        'message' is allowed to be absent so the result of this test should be
        an HTTP 200 and a good status message returned from the API.
        """
        input_ = {
            # missing 'message'
            'to': 'joel',
            'subject': 'subj',
        }

        type(self.mock_sendmsg.return_value).id = PropertyMock(
                                            return_value='id123abc')
        r = self.client.post(url_for('api_v1.alert'),
                             headers=[self.sb_api_token],
                             data=json.dumps(input_),
                             content_type='application/json')
        self.assert_200(r)
        rjson = json.loads(r.data)
        self.assertEqual(rjson['message'], input_['subject'])

    ### /ping endpoint
    def test_ping_get_wo_token(self):
        r = self.client.get(url_for('api_v1.ping'))

        self.assert_401(r)

    def test_ping_get_w_token(self):
        r = self.client.get(url_for('api_v1.ping'),
                            headers=[self.sb_api_token])

        self.assert_200(r)
        self.assertEqual(json.loads(r.data)['apiversion'], zpark.v1.API_VERSION)

    def test_ping_post_verb(self):
        r = self.client.post(url_for('api_v1.ping'))

        self.assert_405(r)


class ApiCommonTestCase(ApiTestCase):

    @patch('zpark.tasks.task_dispatch_spark_command.apply_async',
           autospec=True)
    def test_handle_spark_webhook(self, mock_task):
        """
        Test a successful call to handle_spark_webhook().

        There are no contrived conditions in this test to cause a failure to
        occur.

        Expected behavior:
        - The UUT returns a sequence with two elements:
            - A dict with the correct task ID as one of its elements
            - An HTTP status code 200
        - The task_dispatch_spark_command task (mocked) is called once
        """

        type(mock_task.return_value).id = PropertyMock(return_value='id123abc')

        webhook_data = json.loads(self.build_fake_webhook_json())
        rv = zpark.api_common.handle_spark_webhook(webhook_data)

        self.assertEqual('id123abc', rv[0]['taskid'])
        self.assertEqual(200, rv[1])
        mock_task.assert_called_once_with((webhook_data,))

    @patch('zpark.tasks.task_dispatch_spark_command.apply_async',
           autospec=True)
    def test_handle_spark_webhook_fail(self, mock_task):
        """
        Test a call to handle_spark_webhook() where an exception is raised.

        The task_dispatch_spark_command function is mocked to throw an
        exception in this test.

        Expected behavior:
        - The UUT returns a sequence with two elements:
            - A dict that contains an error description
            - An HTTP status code 500
        - The task_dispatch_spark_command task (mocked) is called once
        """

        mock_task.side_effect = \
                zpark.tasks.task_dispatch_spark_command.OperationalError('error')

        webhook_data = json.loads(self.build_fake_webhook_json())
        rv = zpark.api_common.handle_spark_webhook(webhook_data)

        return_data = rv[0]
        return_code = rv[1]
        self.assertEqual('error', list(return_data.keys())[0])
        self.assertEqual(500, return_code)
        mock_task.assert_called_once_with((webhook_data,))

    @patch('zpark.tasks.task_dispatch_spark_command.apply_async',
           autospec=True)
    def test_handle_spark_webhook_bad_resource(self, mock_task):
        """
        Test a call to handle_spark_webhook() where the input data contains
        an invalid 'resource' attribute.

        Expected behavior:
        - The UUT returns a sequence with two elements:
            - A dict that contains an error description
            - An HTTP status code 400
        - The task_dispatch_spark_command task (mocked) is not called
        """

        webhook_data = json.loads(self.build_fake_webhook_json())
        webhook_data['resource'] = 'rooms'
        rv = zpark.api_common.handle_spark_webhook(webhook_data)

        return_data = rv[0]
        return_code = rv[1]
        self.assertEqual('error', list(return_data.keys())[0])
        self.assertEqual(400, return_code)
        self.assertFalse(mock_task.called)

    @patch('zpark.tasks.task_dispatch_spark_command.apply_async',
           autospec=True)
    def test_handle_spark_webhook_bad_event(self, mock_task):
        """
        Test a call to handle_spark_webhook() where the input data contains
        an invalid 'event' attribute.

        Expected behavior:
        - The UUT returns a sequence with two elements:
            - A dict that contains an error description
            - An HTTP status code 400
        - The task_dispatch_spark_command task (mocked) is not called
        """

        webhook_data = json.loads(self.build_fake_webhook_json())
        webhook_data['event'] = 'deleted'
        rv = zpark.api_common.handle_spark_webhook(webhook_data)

        return_data = rv[0]
        return_code = rv[1]
        self.assertEqual('error', list(return_data.keys())[0])
        self.assertEqual(400, return_code)
        self.assertFalse(mock_task.called)

    @patch('zpark.tasks.task_dispatch_spark_command.apply_async',
           autospec=True)
    def test_handle_spark_webhook_bad_resource_and_event(self, mock_task):
        """
        Test a call to handle_spark_webhook() where the input data contains
        an invalid 'resource' and event' attributes.

        Expected behavior:
        - The UUT returns a sequence with two elements:
            - A dict that contains an error description
            - An HTTP status code 400
        - The task_dispatch_spark_command task (mocked) is not called
        """

        webhook_data = json.loads(self.build_fake_webhook_json())
        webhook_data['resource'] = 'rooms'
        webhook_data['event'] = 'deleted'
        rv = zpark.api_common.handle_spark_webhook(webhook_data)

        return_data = rv[0]
        return_code = rv[1]
        self.assertEqual('error', list(return_data.keys())[0])
        self.assertEqual(400, return_code)
        self.assertFalse(mock_task.called)

    @patch('zpark.tasks.task_dispatch_spark_command.apply_async',
           autospec=True)
    def test_handle_spark_webhook_missing_resource_elm(self, mock_task):
        """
        Test a call to handle_spark_webhook() where the input data is missing
        the 'resource' element.

        Expected behavior:
        - The UUT returns a sequence with two elements:
            - A dict that contains an error description
            - An HTTP status code 400
        - The task_dispatch_spark_command task (mocked) is not called
        """

        webhook_data = json.loads(self.build_fake_webhook_json())
        del webhook_data['resource']
        rv = zpark.api_common.handle_spark_webhook(webhook_data)

        return_data = rv[0]
        return_code = rv[1]
        self.assertEqual('error', list(return_data.keys())[0])
        self.assertEqual(400, return_code)
        self.assertFalse(mock_task.called)

    @patch('zpark.tasks.task_dispatch_spark_command.apply_async',
           autospec=True)
    def test_handle_spark_webhook_missing_event_elm(self, mock_task):
        """
        Test a call to handle_spark_webhook() where the input data is missing
        the 'event' element.

        Expected behavior:
        - The UUT returns a sequence with two elements:
            - A dict that contains an error description
            - An HTTP status code 400
        - The task_dispatch_spark_command task (mocked) is not called
        """

        webhook_data = json.loads(self.build_fake_webhook_json())
        del webhook_data['event']
        rv = zpark.api_common.handle_spark_webhook(webhook_data)

        return_data = rv[0]
        return_code = rv[1]
        self.assertEqual('error', list(return_data.keys())[0])
        self.assertEqual(400, return_code)
        self.assertFalse(mock_task.called)

    @patch('zpark.tasks.task_dispatch_spark_command.apply_async',
           autospec=True)
    def test_handle_spark_webhook_missing_multiple_elms(self, mock_task):
        """
        Test a call to handle_spark_webhook() where the input data is missing
        multiple required elements.

        Expected behavior:
        - The UUT returns a sequence with two elements:
            - A dict that contains an error description
            - An HTTP status code 400
        - The task_dispatch_spark_command task (mocked) is not called
        """

        webhook_data = json.loads(self.build_fake_webhook_json())
        del webhook_data['resource']
        del webhook_data['event']
        rv = zpark.api_common.handle_spark_webhook(webhook_data)

        return_data = rv[0]
        return_code = rv[1]
        self.assertEqual('error', list(return_data.keys())[0])
        self.assertEqual(400, return_code)
        self.assertFalse(mock_task.called)


class TaskTestCase(BaseTestCase):

    def setUp(self):
        self.mock_spark_msg_create_patcher = \
                patch('zpark.spark_api.messages.create', autospec=True)
        self.mock_spark_msg_create = self.mock_spark_msg_create_patcher.start()

        self.mock_zabbixapi_patcher = \
            patch('zpark.pyzabbix.ZabbixAPIObjectClass.__getattr__',
                  autospec=True)
        self.mock_zabbixapi = self.mock_zabbixapi_patcher.start()

        if False:
            import logging
            import sys
            fmt = '%(levelname)s [%(pathname)s:%(lineno)d] %(message)s'
            logging.basicConfig(level=logging.DEBUG, stream=sys.stderr,
                                format=fmt)

    def tearDown(self):
        self.mock_spark_msg_create_patcher.stop()
        self.mock_zabbixapi_patcher.stop()

    def build_spark_api_reply(self, toPersonEmail=None, text=None,
                              roomId=None):
        my_spark_reply_obj = namedtuple('sparkmsg',
                                         'toPersonEmail roomId text id'
                                         ' created')
        # this is only a subset of the data returned by the API
        my_spark_reply = my_spark_reply_obj(
            created='2017-08-09T00:26:11.937Z',
            id='id123456',
            roomId=roomId or 'roomId1234',
            toPersonEmail=toPersonEmail or 'joel@zpark.packetmiscief',
            text=text or 'this is the message you sent'
        )

        return my_spark_reply

    def test_task_send_spark_message(self):
        to = u'joel@zpark.packetmischief'
        message = u'Your data center is on fire'

        spark_api_reply = self.build_spark_api_reply(toPersonEmail=to,
                                                     text=message)
        self.mock_spark_msg_create.return_value = spark_api_reply

        self.assertEqual(spark_api_reply.id,
                         zpark.tasks.task_send_spark_message(to, message))

    def test_task_send_spark_message_retry(self):
        to = u'joel@zpark.packetmischief'
        message = u'Your data center is on fire'

        e = SparkApiError(409)

        self.mock_spark_msg_create.side_effect = [e, self.build_spark_api_reply()]
        mock_retry = patch('zpark.tasks.task_send_spark_message.retry',
                           autospec=True)
        mock_retry_patcher = mock_retry.start()
        mock_retry_patcher.side_effect = Retry

        with self.assertRaises(Retry):
            zpark.tasks.task_send_spark_message(to, message)

        mock_retry_patcher.assert_called_with(exc=e)

        mock_retry.stop()

    @patch('zpark.tasks.task_send_spark_message')
    def test_task_report_zabbix_active_issues_good(self, mock_sendmsg):
        """
        Report the active Zabbix issues to Spark in response to an assumed
        "show me the issues" command. This test should be successful and has
        no contrived conditions to cause a failure.
        Expected behavior:

        - Zabbix API (mock) is called once to get the list of issues
        - Spark API (mock) is called once to output the list of issues
        - Spark API (mock) was called with certain inputs that match the
        (mocked) Zabbix API output
        - task_report_zabbix_active_issues() returns None
        """
        def zabbix_api_reply(*args, **kwargs):
            return [{
                'hosts': [
                    {'host': 'host.packetmischief', 'hostid': 'host12345'}
                ],
                'description': 'This is the trigger\'s description',
                'lastchange': 1509402980
            }]

        self.mock_zabbixapi.return_value = zabbix_api_reply

        rv = zpark.tasks.task_report_zabbix_active_issues(
                'roomid123abc',
                'direct',
                'joel@zpark.packetmischief')

        self.mock_zabbixapi.assert_called_once()
        mock_sendmsg.assert_called_once()
        for call in mock_sendmsg.call_args_list:
            args, kwargs = call
            # arg0 is roomId
            self.assertEqual('roomid123abc', args[0])
            # arg1 is the text
            self.assertIn('host.packetmischief', args[1])
            # arg2 is the markdown
            self.assertIn('host.packetmischief', args[2])
        self.assertIsNone(rv)

    @patch('zpark.tasks.task_send_spark_message')
    def test_task_report_zabbix_active_issues_zero_issues(self, mock_sendmsg):
        """
        Report the active Zabbix issues to Spark in response to an assumed
        "show me the issues" command. This test gets zero issues from the
        Zabbix API (mock) but should be successful otherwise.
        Expected behavior:

        - Zabbix API (mock) is called once to get the list of issues
        - Spark API (mock) is called once to output the list of issues
        - Spark API (mock) was called with certain inputs that match the
        (mocked) Zabbix API output
        """
        def zabbix_api_reply(*args, **kwargs):
            return []

        self.mock_zabbixapi.return_value = zabbix_api_reply

        zpark.tasks.task_report_zabbix_active_issues(
                'roomid123abc',
                'direct',
                'joel@zpark.packetmischief')

        self.mock_zabbixapi.assert_called_once()
        mock_sendmsg.assert_called_once()
        for call in mock_sendmsg.call_args_list:
            args, kwargs = call
            # arg0 is roomId
            self.assertEqual('roomid123abc', args[0])
            # arg1 is the text
            self.assertIn('no active issues', args[1])
            # arg2 is the markdown
            self.assertIn('no active issues', args[2])

    @patch('zpark.tasks.notify_of_failed_command')
    @patch('zpark.tasks.task_send_spark_message')
    def test_task_report_zabbix_active_issues_zbx_error(self, mock_sendmsg,
                                                        mock_notify):
        """
        Report the active Zabbix issues to Spark in response to an assumed
        "show me the issues" command. This test mocks the Zabbix API to
        throw an exception when the test attempts to get the list of active
        issues.
        Expected behavior:

        - task_report_zabbix_active_issues() reraises the Zabbix API
        exception
        - Zabbix API (mock) is called once to get the list of issues
        - notify_of_failed_command() (mock) should be called once
        """
        self.mock_zabbixapi.side_effect = ZabbixAPIException('error')

        with self.assertRaises(ZabbixAPIException):
            zpark.tasks.task_report_zabbix_active_issues(
                    'roomid123abc',
                    'direct',
                    'joel@zpark.packetmischief')

        self.mock_zabbixapi.assert_called_once()
        mock_notify.assert_called_once()

    @patch('zpark.tasks.notify_of_failed_command')
    @patch('zpark.tasks.task_send_spark_message')
    def test_task_report_zabbix_active_issues_retry_zbx_err(self, mock_sendmsg,
                                                            mock_notify):
        """
        Report the active Zabbix issues to Spark in response to an assumed
        "show me the issues" command. This test mocks the Zabbix API to
        throw an exception on the first query and 'success' on the second.
        Expected behavior:

        - task_report_zabbix_active_issues() should retry after getting the
        exception from Zabbix
        - The retry mock should be called with the Zabbix exception as an
        argument
        - Zabbix API (mock) is called twice
        - notify_of_failed_command() (mock) should be called once
        """
        report_args = ('roomid123abc',
                       'direct',
                       'joel@zpark.packetmischief')

        e = ZabbixAPIException('error')
        self.mock_zabbixapi.side_effect = [e, None]

        mock_retry = patch('zpark.tasks.task_report_zabbix_active_issues.retry',
                           autospec=True)
        mock_retry_patcher = mock_retry.start()
        mock_retry_patcher.side_effect = Retry

        with self.assertRaises(Retry):
            zpark.tasks.task_report_zabbix_active_issues(*report_args)

        mock_retry_patcher.assert_called_with(exc=e)
        self.mock_zabbixapi.assert_called_once()
        mock_notify.assert_called_once()

        mock_retry.stop()

    @patch('zpark.tasks.task_send_spark_message')
    def test_task_report_zabbix_active_issues_retry_spark_err(self,
                                                              mock_sendmsg):
        """
        Report the active Zabbix issues to Spark in response to an assumed
        "show me the issues" command. This test mocks the Spark API to
        throw an exception on the first query and 'success' on the second.
        Expected behavior:

        - task_report_zabbix_active_issues() should retry after getting the
        exception from Zabbix
        - The retry mock should be called with the Spark exception as an
        argument
        - Zabbix API (mock) is called twice
        - Spark API (mock) is called twice
        """
        report_args = ('roomid123abc',
                       'direct',
                       'joel@zpark.packetmischief')

        e = SparkApiError(409)
        mock_sendmsg.side_effect = [e, None]

        mock_retry = patch('zpark.tasks.task_report_zabbix_active_issues.retry',
                           autospec=True)
        mock_retry_patcher = mock_retry.start()
        mock_retry_patcher.side_effect = Retry

        with self.assertRaises(Retry):
            zpark.tasks.task_report_zabbix_active_issues(*report_args)

        mock_retry_patcher.assert_called_with(exc=e)
        self.mock_zabbixapi.assert_called_once()
        mock_sendmsg.assert_called_once()

        mock_retry.stop()

    def test_task_report_zabbix_active_issues_bad_roomtype(self):
        # 2nd argument is the roomtype. valid values are 'direct' and 'group'.
        # anything else throws ValueError.
        with self.assertRaises(ValueError):
            zpark.tasks.task_report_zabbix_active_issues(
                    'id123abc',
                    'party',
                    'joel@zpark.packetmischief')

    def test_notify_of_failed_command_first_try(self):
        """
        Attempt notification that a bot command could not be answered right
        away but a retry is underway.
        Expected behavior:

        - notify_of_failed_command() should attempt to notify the caller
        via Spark message that it's retrying
        - notify_of_failed_command() returns None
        """
        self.mock_spark_msg_create.return_value = self.build_spark_api_reply()

        rv = zpark.tasks.notify_of_failed_command('roomId1234',
                                                  'direct',
                                                  'joel@zpark.packetmischief',
                                                  0, # retries
                                                  3, # max_retries
                                                  'OhShootException')

        self.mock_spark_msg_create.assert_called_once()
        self.assertIsNone(rv)

    def test_notify_of_failed_command_2nd_try(self):
        """
        Attempt notification that a bot command could not be answered but
        simulate a case where the notification had to be retried due to some
        sort of error and this is the second try (1st retry) at sending that
        notification.
        Expected behavior:

        - notify_of_failed_command() should do nothing on the 2nd, 3rd, etc
        try. No Spark message should be sent.
        - notify_of_failed_command() returns None
        """
        self.mock_spark_msg_create.return_value = self.build_spark_api_reply()

        rv = zpark.tasks.notify_of_failed_command('roomId1234',
                                                  'direct',
                                                  'joel@zpark.packetmischief',
                                                  1, # retries
                                                  3, # max_retries
                                                  'OhShootException')

        self.assertFalse(self.mock_spark_msg_create.called)
        self.assertIsNone(rv)

    def test_notify_of_failed_command_max_tries(self):
        """
        Attempt notification that a bot command could not be answered but
        simulate a case where the notification had to be retried due to some
        sort of error and this is the last retry before max_retries is
        exceeded.
        Expected behavior:

        - notify_of_failed_command() currently does nothing under these
        conditions. No Spark message should be sent.
        - notify_of_failed_command() returns None
        """
        self.mock_spark_msg_create.return_value = self.build_spark_api_reply()

        rv = zpark.tasks.notify_of_failed_command('roomId1234',
                                                  'direct',
                                                  'joel@zpark.packetmischief',
                                                  3, # retries
                                                  3, # max_retries
                                                  'OhShootException')

        self.assertFalse(self.mock_spark_msg_create.called)
        self.assertIsNone(rv)

    @patch('zpark.tasks.task_send_spark_message.apply')
    def test_notify_of_failed_command_spark_error(self, mock_sendmsg):
        """
        Attempt notification that a bot command could not be answered
        but have the Spark API throw an exception during that notification.
        Expected behavior:

        - notify_of_failed_command_spark() will re-raise the SparkApiError
        exception
        - task_send_spark_message.apply() will be called a single time
        (no retries due to the mock that's in place)
        """
        mock_sendmsg.side_effect = SparkApiError(409)

        with self.assertRaises(SparkApiError):
            zpark.tasks.notify_of_failed_command('roomId1234',
                                                 'direct',
                                                 'joel@zpark.packetmischief',
                                                 0, # retries
                                                 3, # max_retries
                                                 'OhShootException')
        mock_sendmsg.assert_called_once()

