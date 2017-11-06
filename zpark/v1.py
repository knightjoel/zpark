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

        app.logger.info("API: create alert: to:{} subject:<hidden>"
                " message:<hidden>"
                .format(args['to']))

        return api_common.send_spark_alert_message(args['to'],
                                                   args['subject'],
                                                   args['message'])


class Ping(Resource):

    @api_common.requires_api_token
    def get(self):
        app.logger.info("API: ping")
        return api_common.ping(api_version=API_VERSION)

class Webhook(Resource):

    def post(self):
        reqjson = request.get_json()
        app.logger.info("API: webhook callback received: id:{} name:\"{}\""
                .format(reqjson.get('id', '<Unknown>'),
                        reqjson.get('name', '<Unknown>')))

        return api_common.handle_spark_webhook(reqjson)

api_v1.add_resource(Ping, '/ping')
api_v1.add_resource(Alert, '/alert')
api_v1.add_resource(Webhook, '/webhook')

