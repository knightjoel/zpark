import logging
import logging.config
from logging import Filter

from flask import request


class ContextualLogFilter(Filter):

    def filter(self, record):
        # This code needs to be highly resilient. We don't know what state
        # the app will be in when the filter is called so we cannot depend
        # on any variables or objects being in a good or known state.
        # If this method throws an exception, then the log data is lost,
        # an ugly HTTP/500 error is shown to the user, and the exception
        # here potentially masks a prior exception which triggered the log
        # message in the first place.

        record.client_ip = request.remote_addr
        record.method = request.method
        record.url = request.base_url
        record.user_agent = request.headers.get('User-Agent', '')

        return True


def setup_api_logging(app):
    """
    Initialize the log handler(s) which handle log messages from the API
    layer.

    Args:
        - app (Flask): The Flask application object.

    Returns:
        - None
    """

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


def setup_celery_logging(app, celery_app, task_logger_name,
                         loglevel=None, logfile=None,
                         fmt=None, colorize=None, **kwargs):
    """
    Initialize the log handlers which handle log messages for the task
    worker layer.

    Args:
        - app (Flask): The Flask application object.
        - celery_app (Celery): The Celery application object.
        _ task_logger_name (str): The name of our logger. This should
            always be 'zpark.tasks' since that is the module which emits
            task log messages. This argument must match with the
            argument to the celery.utils.log.get_task_logger() call in
            zpark.tasks.

    Returns:
        - None
    """

    import celery.app.log

    logconf = {
        'version': 1,
        'formatters': {
            'taskfmt': {
                '()': celery.app.log.TaskFormatter,
                'fmt': app.config.get('WORKER_TASK_LOG_FORMAT',
                                      celery_app.conf.worker_task_log_format),
                'use_color': False,
            },
            'workerfmt': {
                'format': app.config.get('WORKER_LOG_FORMAT',
                                         celery_app.conf.worker_log_format),
            },
        },
        'handlers': {
            # Create copies of the dicts stored in the app config.
            'taskh': dict(app.config.get('WORKER_LOG_HANDLER', {})),
            'workh': dict(app.config.get('WORKER_LOG_HANDLER', {})),
            'nullh': {
                'level': 'INFO',
                'class': 'logging.NullHandler',
            }
        },
        'loggers': {
            'celery': {
                'handlers': ['workh'],
                # this can be turned down via the handler's log level
                'level': 'DEBUG'
            },
            'celery.task': {
                'handlers': ['taskh'],
                # this can be turned down via the handler's log level
                'level': 'DEBUG',
                'propagate': 0
            },
            # Celery will make this logger a child of 'celery.task' when
            # the get_task_logger(__name__) function is called at the top
            # of zpark.tasks. Propagate logs upwards to 'celery.task' which
            # will emit the log message.
            task_logger_name: {
                'handlers': ['nullh'],
                # this can be turned down via the handler's log level
                'level': 'DEBUG',
                'propagate': 1
            }
        },
    }

    # Apply the correct formatters to the handlers. User cannot override this.
    logconf['handlers']['taskh'].update({
            'formatter': 'taskfmt',
    })
    logconf['handlers']['workh'].update({
            'formatter': 'workerfmt',
    })

    logging.config.dictConfig(logconf)

