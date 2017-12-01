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
app.config.from_object('zpark.default_settings')
app.config.from_pyfile('app.cfg', silent=True)

app.wsgi_app = ProxyFix(app.wsgi_app)

celery = Celery(broker=app.config['CELERY_BROKER_URL'])
celery.config_from_object(app.config)
celery.conf.worker_hijack_root_logger = False
celery.conf.task_eager_propagates = True

if not app.debug and not sys.stdout.isatty():
    import logging
    import logging.config
    from zpark.log import ContextualLogFilter

    # Tickle Flask to init its logger. It _appears_ as though if Flask's
    # logger is not initialized ahead of the dictConfig() call, that Flask
    # then overwrites the config that dictConfig() creates with its own
    # default config. Letting Flask init its logger ahead of the
    # dictConfig() call magically makes it work. None of this is documented
    # in the Flask 0.12 docs.
    app.logger

    logconf = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'appfmt': { 'format': app.config.get('APP_LOG_FORMAT', '') },
        },
        'handlers': {
            'apph': app.config.get('APP_LOG_HANDLER', {})
        },
        'filters': {
            'appfilt': {
                '()': ContextualLogFilter,
            },
        },
        'loggers': {
            # Flask 0.12 installs its log handler under a name which it
            # stores in an app object property.
            app.logger_name: {
                'handlers': ['apph'],
                # this can be turned down via the handler's log level
                'level': logging.DEBUG,
            },
        },
    }
    # Apply the formatter and the contextual filter to the handler. User
    # cannot override this.
    logconf['handlers']['apph'].update({
            'formatter': 'appfmt',
            'filters': ['appfilt']
    })

    logging.config.dictConfig(logconf)

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

