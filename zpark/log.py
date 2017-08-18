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

