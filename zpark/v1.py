from flask import Blueprint
from flask_restful import Api, Resource, reqparse

from zpark import api_common


API_VERSION_V1=1
API_VERSION=API_VERSION_V1

api_v1_bp = Blueprint('api_v1', __name__)
api_v1 = Api(api_v1_bp)

class Alert(Resource):

    @api_common.requires_api_token
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('to', type=unicode, required=True,
                            location='json',
                            help='Identifier of person or Spark space to '
                                    'send the alert to. Required.')
        parser.add_argument('subject', type=unicode, required=True,
                            location='json',
                            help='The subject (ie, first line) of text sent '
                                    'to the recipient. Required.')
        parser.add_argument('message', type=unicode, required=False,
                            location='json',
                            help='The contents of the alert message. Optional.')
        args = parser.parse_args()

        return api_common.spark_send_alert_message(args['to'],
                                                   args['subject'],
                                                   args['message'])


class Ping(Resource):

    @api_common.requires_api_token
    def get(self):
        return api_common.ping(api_version=API_VERSION)

api_v1.add_resource(Ping, '/ping')
api_v1.add_resource(Alert, '/alert')

