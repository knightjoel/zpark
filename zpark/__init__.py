import os

from ciscosparkapi import CiscoSparkAPI
from flask import Flask


basedir = os.path.dirname(os.path.abspath(__file__))
basedir = os.path.abspath(basedir + '/../')

app = Flask(__name__, instance_path=basedir, instance_relative_config=True)
app.config.from_object('zpark.default_settings')
app.config.from_pyfile('app.cfg', silent=True)

spark_api = CiscoSparkAPI(access_token=app.config['SPARK_ACCESS_TOKEN'])

# API v1
from zpark.v1 import api_v1, api_v1_bp, API_VERSION_V1
app.register_blueprint(api_v1_bp, url_prefix='/api/v{}'.format(API_VERSION_V1))

