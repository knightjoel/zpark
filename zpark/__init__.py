import os
import sys

from celery import Celery
from ciscosparkapi import CiscoSparkAPI
from flask import Flask
from jinja2 import Environment, FileSystemLoader, select_autoescape
import pyzabbix
from werkzeug.contrib.fixers import ProxyFix


basedir = os.path.dirname(os.path.abspath(__file__))
basedir = os.path.abspath(basedir + '/../')

app = Flask(__name__, instance_path=basedir, instance_relative_config=True)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 32
app.config.from_object('zpark.default_settings')
app.config.from_pyfile('app.cfg', silent=True)

app.wsgi_app = ProxyFix(app.wsgi_app)

celery = Celery(broker=app.config['CELERY_BROKER_URL'])
celery.config_from_object(app.config)
celery.conf.worker_hijack_root_logger = False
celery.conf.task_eager_propagates = True

if not app.debug and not sys.stdout.isatty():
    import logging
    from logging import Formatter
    from logging.handlers import RotatingFileHandler
    from zpark.log import ContextualLogFilter

    app.logger.setLevel(logging.DEBUG)
    app.logger.addFilter(ContextualLogFilter())

    file_handler = RotatingFileHandler(
            os.path.join(basedir, 'logs/app.log'),
            maxBytes=app.config['APP_LOG_MAXBYTES'],
            backupCount=app.config['APP_LOG_ROTATECOUNT'])
    file_handler.setFormatter(Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
            ' [in %(pathname)s:%(lineno)d]'
            ' [client:%(client_ip)s method:"%(method)s" url:"%(url)s"'
            ' ua:"%(user_agent)s"]'
            ))
    file_handler.setLevel(app.config['APP_LOG_LOGLEVEL'])
    app.logger.addHandler(file_handler)

jinja2 = Environment(
    loader=FileSystemLoader(basedir + '/zpark/templates'),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)

spark_api = CiscoSparkAPI(access_token=app.config['SPARK_ACCESS_TOKEN'])

zabbix_api = pyzabbix.ZabbixAPI(app.config['ZABBIX_SERVER_URL'])
try:
    zabbix_api.login(app.config['ZABBIX_USERNAME'],
                     app.config['ZABBIX_PASSWORD'])
except pyzabbix.ZabbixAPIException as e:
    app.logger.critical('Unable to authenticate to the Zabbix API at {}: {}'
            .format(app.config['ZABBIX_SERVER_URL'], e))

# API v1
from zpark.v1 import api_v1, api_v1_bp, API_VERSION_V1
app.register_blueprint(api_v1_bp, url_prefix='/api/v{}'.format(API_VERSION_V1))

