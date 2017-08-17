from collections import namedtuple
import json

try:    # python 2.x
    from mock import Mock, patch
except: # python 3.x
    from unittest.mock import Mock, patch
from ciscosparkapi import SparkApiError
from flask import url_for
from flask_testing import TestCase

import zpark


class ApiTestCase(TestCase):

    def create_app(self):
        zpark.app.config.update(
            DEBUG = False,
            TESTING = True,
            SB_API_TOKEN = 'token12345'
        )
        return zpark.app

    def setUp(self):
        self.sb_api_token = ('Token', zpark.app.config['SB_API_TOKEN'])

    def tearDown(self):
        pass


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
    def test_alert_post_valid_alert(self):
        to = u'joel@zpark.packetmischief'
        subject = u'This might ruin your day...'
        message = u'Your data center is on fire'

        mock_sparkapi = Mock(name='create')
        # simulate a ciscosparkapi.messages object
        my_spark_msg_obj = namedtuple('sparkmsg', 'toPersonEmail text id created')
        my_spark_msg = my_spark_msg_obj(
            created='2017-08-09T00:26:11.937Z',
            id='id123456',
            toPersonEmail=to,
            text='\n\n'.join([subject, message])
        )
        mock_sparkapi.return_value = my_spark_msg

        with patch.object(zpark.spark_api.messages, 'create', mock_sparkapi):
            r = self.client.post(url_for('api_v1.alert'),
                                 headers=[self.sb_api_token],
                                 data=json.dumps({
                                    'to': to,
                                    'subject': subject,
                                    'message': message
                                 }),
                                 content_type='application/json')
            self.assert_200(r)
            mock_sparkapi.assert_called_once_with(
                toPersonEmail=my_spark_msg.toPersonEmail,
                text=my_spark_msg.text
            )
            rjson = json.loads(r.data)
            self.assertEqual(rjson['created'], my_spark_msg.created)
            self.assertEqual(rjson['message'], my_spark_msg.text)
            self.assertEqual(rjson['messageId'], my_spark_msg.id)
            self.assertEqual(rjson['toPersonEmail'],
                             my_spark_msg.toPersonEmail)

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

    def test_alert_post_valid_alert_with_spark_api_error(self):
        to = u'joel@zpark.packetmischief'
        subject = u'This might ruin your day...'
        message = u'Your data center is on fire'

        mock_sparkapi = Mock(name='create', side_effect=SparkApiError(409))

        with patch.object(zpark.spark_api.messages, 'create', mock_sparkapi):
            r = self.client.post(url_for('api_v1.alert'),
                                 headers=[self.sb_api_token],
                                 data=json.dumps({
                                    'to': to,
                                    'subject': subject,
                                    'message': message
                                 }),
                                 content_type='application/json')
            self.assert_status(r, 409)
            mock_sparkapi.assert_called_once_with(
                toPersonEmail=to,
                text='\n\n'.join([subject, message])
            )

    def test_alert_post_valid_alert_to_roomid(self):
        to = 'Abc1234wxyz'
        subject = u'This might ruin your day...'
        message = u'Your data center is on fire'

        r = self.client.post(url_for('api_v1.alert'),
                             headers=[self.sb_api_token],
                             data=json.dumps({
                                'to': to,
                                'subject': subject,
                                'message': message
                             }),
                             content_type='application/json')
        self.assert_400(r)
        self.assertIn('must be an email address', r.data)

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

