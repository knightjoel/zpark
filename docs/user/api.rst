.. _User API Doc:

User API Doc
============

zpark
.....

.. automodule:: zpark
    :members:
    :undoc-members:
    :show-inheritance:

zpark\.api\_common
..................

.. automodule:: zpark.api_common
    :members:
    :undoc-members:
    :show-inheritance:

zpark\.v1 (APIv1)
.................

.. automodule:: zpark.v1
    :members:
    :undoc-members:
    :show-inheritance:

zpark\.log
..........

.. automodule:: zpark.log
    :members:
    :show-inheritance:

zpark\.tasks
............

.. automodule doesn't work for Celery-decorated tasks, even with the
   celery.contrib.sphinx module in Celery 4.1.0. This should be fixed
   in whatever the next version of Celery is.
   See https://github.com/celery/celery/issues/4072
   For now, each task needs to be manually documented with the autotask
   directive.

.. autotask:: zpark.tasks.task_dispatch_spark_command
.. autotask:: zpark.tasks.task_send_spark_message
.. autotask:: zpark.tasks.task_report_zabbix_active_issues
.. autotask:: zpark.tasks.task_report_zabbix_server_status

.. automodule:: zpark.tasks
    :members:
    :undoc-members:
    :show-inheritance:

zpark\.utils
............

.. automodule:: zpark.utils
    :members:
    :undoc-members:
    :show-inheritance:
