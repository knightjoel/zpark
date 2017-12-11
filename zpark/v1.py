import hashlib
import hmac
import json

from flask import Blueprint, request
from flask_restful import Api, Resource, reqparse

from zpark import app, api_common


API_VERSION_V1=1
API_VERSION=API_VERSION_V1

api_v1_bp = Blueprint('api_v1', __name__)
api_v1 = Api(api_v1_bp)

class Alert(Resource):

    @api_common.requires_api_token
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('to', type=str, required=True,
                            location='json',
                            help='Identifier of person or Spark space to '
                                    'send the alert to. Required.')
        parser.add_argument('subject', type=str, required=True,
                            location='json',
                            help='The subject (ie, first line) of text sent '
                                    'to the recipient. Required.')
        parser.add_argument('message', type=str, required=False,
                            location='json',
                            help='The contents of the alert message. Optional.')
        args = parser.parse_args()

        app.logger.info("create alert: to:{} subject:<hidden>"
                " message:<hidden>"
                .format(args['to']))

        return api_common.send_spark_alert_message(args['to'],
                                                   args['subject'],
                                                   args['message'])


class Ping(Resource):

    @api_common.requires_api_token
    def get(self):
        app.logger.info("ping")
        return api_common.ping(api_version=API_VERSION)

class Webhook(Resource):

    def post(self):
        """
        Process incoming webhook callbacks from the Spark service.

        Authentication of the incoming callback will be done when the
        flask 'SPARK_WEBHOOK_SECRET' config parameter is set. A callback
        is successfully authenticated under these conditions:

            - The X-Spark-Signature header is present, and
            - The value in the header matches our computed SHA1 HMAC of
                the request body.

        If the callback is successfully authenticated, the JSON in the
        callback is passed to a handler routine which takes care of the
        actual request.

        Args:
            - None

        Returns:
            - A two-element set containing:
                - A dict which provides some context about how the request
                    was processed.
                - An int which is used as the HTTP status code.
        """

        # Safety third. As recommended in the docs, prior to calling
        # request.get_data(), validate the size of the data is within
        # reason.
        cl = request.headers.get('Content-Length', None)
        try:
            cl = int(cl)
        except ValueError:
            return (
                {'error': 'Bad request'},
                400
            )
        if cl and cl > app.config['MAX_CONTENT_LENGTH']:
                return (
                    {'error': 'Too big'},
                    413
                )

        sparkhmac = request.headers.get('X-Spark-Signature', None)
        reqjson = request.get_json()

        whid = reqjson.get('id', '<Unknown>')
        whname = reqjson.get('name', '<Unknown>')

        if 'SPARK_WEBHOOK_SECRET' in app.config:
            if sparkhmac is None:
                app.logger.warning("webhook: Unauthorized webhook"
                        " callback received: no X-Spark-Signature header."
                        " Verify the callback has a configured secret."
                        " id:{} name:\"{}\""
                        .format(whid, whname))
                return (
                    {'error': 'Unauthorized'},
                    403
                )

            ourhmac = hmac.new(bytes(app.config['SPARK_WEBHOOK_SECRET'],
                                   'utf-8'),
                               msg=request.get_data(),
                               digestmod=hashlib.sha1).hexdigest()

            if hmac.compare_digest(ourhmac, sparkhmac) is False:
                app.logger.warning("webhook: Unauthorized webhook"
                        " callback received: HMACs do not match."
                        " Verify proper setting of 'SPARK_WEBHOOK_SECRET'."
                        " id:{} name:\"{}\""
                        .format(whid, whname))
                app.logger.debug("webhook: Spark's HMAC: {}"
                        " / Our computed HMAC: {}"
                        .format(sparkhmac, ourhmac))
                return (
                    {'error': 'Unauthorized'},
                    403
                )

        app.logger.info("webhook callback received: id:{} name:\"{}\""
                .format(whid, whname))

        return api_common.handle_spark_webhook(reqjson)

api_v1.add_resource(Ping, '/ping')
api_v1.add_resource(Alert, '/alert')
api_v1.add_resource(Webhook, '/webhook')

