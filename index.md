# Zpark - The Cisco Spark + Zabbix Bot

This bot provides an interface between the [Cisco
Spark](https://www.ciscospark.com) messaging platform and the
[Zabbix](https://www.zabbix.com) monitoring system. Zabbix can send
messages to the bot which in turn are relayed to the specific Spark
user(s), room(s), or combination of both. And Spark users can issue commands
to the bot in order to retrieve information and reports from Zabbix.

## Features

- Relays new Zabbix alerts (which are generated from Zabbix events) to Spark
  user(s) and/or room(s).
- Relays Zabbix "all clear" alerts (which are generated when a recovery
  condition is met) to Spark user(s) and/or room(s).
        - *Requires Zabbix 3.4*
- Configure Spark message recipients based on a combination of alert
  severity, time of day, host group, or other arbitrary criteria. eg:
	- Send all alerts to the Spark room "Network Engineers" between
	  0800-2000 Mon-Fri
	- Send alerts with severity "critical" or higher to engineers
	  "Joe", "Jill", and "Mark" 24x7
- Immediate notification of alerts. As soon as the bot receives an alert
  from Zabbix, it is immediately sent to Spark; there is no queueing or
  batching of messages.
- Interrogate information from Zabbix by issuing commands to the bot
  on Spark. Eg, "@bot show status".
- Decentralized: run the bot on the Zabbix server or on a separate
  server, your choice.

## Requirements

System requirements:
- A UNIX-like operating system with a sane `/bin/sh` shell
- [Python](https://www.python.org) 3
	- *Python 2.7 is not supported*
- An HTTP daemon
	- *This document assumes [nginx](https://nginx.org)*
- A process monitor such as Gaffer/Runit/Supervisor/Upstart
	- *This document assumes
	  [Supervisor](http://supervisord.org/)*

Third-party software requirements:
- A message broker that is compatible with the [Celery library]
(http://docs.celeryproject.org/en/latest/getting-started/brokers/index.html)
	- *This document assumes [Rabbitmq](https://www.rabbitmq.com/)*
- The [curl](https://curl.haxx.se/) command line tool
- The [jo](https://github.com/jpmens/jo) command line tool for
  parsing/building JSON documents
- The Python modules listed in the `requirements.txt` file inside the
  Zpark program directory
  	- *See below for how to install these modules*

# Installation

The following sections will describe how to install Zpark and get it up
and running.

**Before beginning**, please ensure the system and software requirements
above are satisified by installing all necessary software packages as
per whatever method your UNIX-like operating system uses. Instructions
for install the Python modules are below.

## Create a Spark User Account and Bot Account

Visit [www.ciscospark.com](https://www.ciscospark.com), navigate to the
"Sign In" page and create your free account. If you already have a Spark
account, go ahead and log in.

Once you've logged into your account (using the browser, not the desktop
app), visit
[developer.ciscospark.com](https://developer.ciscospark.com), and
navigate to the "My Apps" tab. Click the "+" button and choose to create
a bot. Give your bot a display name, a username, and provide a URL to the
icon that will be used for your bot's avatar.

![Creating a new Cisco Spark bot](/img/spark_new_bot.jpg)

**Carefully copy the access token that is generated for your bot**. You
will need this token in the next step.

## Download and Configure Zpark

This is optional but highly recommended: create a dedicated,
non-privileged user account to run the bot. This account need only exist
on the server where you will be running the bot. The rest of the
documentation will assume the following user exists:

- Username: `\_zpark`
- Groups: `\_zpark`
- Home: `/home/zpark`

As the `\_zpark` user, clone the Zpark git repo into `/home/zpark`:

```
% cd /home/zpark
% git clone https://github.com/knightjoel/zpark.git
```

This is optional but highly recommended: use the Python
[virtualenv](https://virtualenv.pypa.io/en/stable/) tool to create an
isolated Python environment for Zpark. And since you're at it, you might
as well use the
[virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/)
tools to make managing your isolated Python environments a bit easier:

```
% pip install --user virtualenvwrapper
% mkdir ~/venvs
% export VIRTUALENVWRAPPER_PYTHON="/usr/local/bin/python3.6"
% export VIRTUALENVWRAPPER_VIRTUALENV=/usr/local/bin/virtualenv-3
% export WORKON_HOME="$HOME/venvs"
% source ~/.local/bin/virtualenvwrapper.sh
% mkvirtualenv zpark
```

You may need to adjust the above paths to suit your operating system.

Now install the required Python packages. If you're using an isolated
Python environment, make sure you activate the environment first.

```
% workon zpark        # activate your venvironment
% cd ~/zpark
% pip3.6 install -r requirements.txt
```

Configure Zpark by copying the default config file to `app.cfg` and then
modifying it. The `app.cfg` file must be located in the top-level `zpark`
directory.

```
% cd /home/zpark/zpark
% cp zpark/default_settings.py app.cfg
```

The `app.cfg` file is parsed as Python code so Python syntax must be
applied!

The following settings **must** be configured:

- `ZPARK_API_TOKEN`

	Zpark API token

	This token is used by consumers of the Zpark API. If a script
	attempts to use the Zpark API without passing the correct token,
	the request will be rejected with an HTTP 401 error code.
	The token should be generated as a random string:
	`% openssl rand -hex 16`

	Eg:
	`ZPARK_API_TOKEN = "e0c297f5....5l2j2"`

- `SPARK_ACCESS_TOKEN`

	Spark API access token

	This token is used by Zpark to authenticate itself to the Spark
	service. Copy and paste the access token that was automatically
	generated when you created your bot account on
	developer.ciscospark.com.

	Eg:
	`SPARK_ACCESS_TOKEN = "thisismyautogeneratedsparktoken"`

- `SPARK_WEBHOOK_SECRET`

        Spark webhook secret

        This is a secret value that is used to authenticate incoming Spark
        webhook callbacks. It's used to ensure that someone cannot impersonate
        the Spark service and cause Zpark to take some unauthorized action
        which sends information back to the unauthorized user.
	The secret should be generated as a random string:
	`% openssl rand -hex 16`

	Eg:
	`ZPARK_API_TOKEN = "40fj43l4....940l1"`

- `CELERY_BROKER_URL`

	Celery message broker URL

	This is the fully-qualified URL (including username and password)
	that Celery will use to communicate with whatever message broker
	you've chosen. Refer to the [Celery documentation]
	(http://docs.celeryproject.org/en/latest/getting-started/brokers/index.html)
	for details on the URL syntax for your broker.

	Eg for RabbitMQ:
	`CELERY_BROKER_URL = 'ampq://user:pass@hostname/vhost'`

- `ZPARK_SERVER_URL`

        Fully-qualified URL to Zabbix

        This is the full URL to the Zabbix server. Must include the scheme
	(`http` or `https`), the domain/IP address, the port (if not 80 or 443)
	and the directory if applicable.

	Eg:
	`ZPARK_SERVER_URL = http://zabbix.your.domain/zabbix`

- `ZABBIX_USERNAME`

	Zabbix Account Username

	The username for an account with access to the Zabbix API. This is
	the account that Zpark will use to communicate with Zabbix.

- `ZABBIX_PASSWORD`

	Zabbix account password

	The password for the Zabbix account.

- `ZPARK_SERVER_URL`

	Fully-qualified URL to Zpark

	This is the full URL for Zpark itself. This URL--which is a byproduct
	of how the web server (nginx) is configured--is what Spark will use
	to access the Zpark API. The URL must include the scheme (`http` or
	`https`), the domain/IP address, port (if not 80 or 443) and the
	directory if applicable.

	Eg:
	`ZPARK_SERVER_URL = https://www.your.domain/zpark`

- `SPARK_TRUSTED_USERS`

	List of trusted Spark users

	This is a (Python) list of Spark users that are allowed to send
	commands to the Zpark bot. Commands received from users not in
	this list are silently ignored. By default, the list is configured
	to *deny all users*. Users must be identified by the email address
	associated with their Cisco Spark account.

	Eg:
	SPARK_TRUSTED_USERS = ['joel@example.net', 'knight@example.com']

The Zpark bot is now configured!

## Configure RabbitMQ

RabbitMQ needs some basic configuration so that Zpark can successfully
submit and retrieve tasks. The example below is based on [the example in
the Celery
documentation](http://docs.celeryproject.org/en/latest/getting-started/brokers/rabbitmq.html#broker-rabbitmq).
Each line below is a command that must be run as a user with administrative
privilege in RabbitMQ.

Create a RabbitMQ account and assign it a password:

```
# rabbitmqctl add_user zpark *<password>*
```

Create a RabbitMQ virtual host for Zpark:

```
# rabbitmqctl add_vhost zpark
```

Grant the zpark user full permissions on the vhost:

```
# rabbitmqctl set_permissions -p zpark zpark ".*" ".*" ".*"
```

**Take note**: The username, password and vhost you choose here will become
part of the `CELERY_BROKER_URL` config parameter.


## Configure Gunicorn and nginx

The Zpark bot is implemented as a web service that provides an API and
consumes the Cisco Spark API and therefore requires an HTTP daemon in
order to run. Gunicorn is used to run the actual application code and
nginx (or your HTTP daemon of choice) is used to provide flow control,
SSL/TLS, access control, and so on. The nginx daemon will receive
incoming requests from clients and proxy them to the Gunicorn daemon
where the Zpark application is running.

Configure Gunicorn by copying the template config and modifing it as
needed. If you're following this guide as-is, the file shouldn't require
much, if any, modification:

```
% cd /home/zpark/zpark
% cp gunicorn.conf.py.template gunicorn.conf.py
% $EDITOR gunicorn.conf.py
```

Add Gunicorn to your process monitor (which this document assumes is
[Supervisor](http://supervisord.org/)). Add the following to
Supervisor's configuration making sure to modify it to suit the
filesystem paths you've been using so far:

```
[program:zpark]
command=/home/zpark/venvs/zpark/bin/gunicorn zpark:app -c /home/zpark/zpark/gunicorn.conf.py
directory=/home/zpark/zpark
user=root
autostart=true
autorestart=true
```

Reload the Supervisor config and Gunicorn/Zpark should now be running:

```
# supervisorctl reread
# ps -axo pid,command | grep zpark
68972 /home/zpark/venvs/zpark/bin/python3.6 /home/zpark/venvs/zpark/bin/gunicorn zpark:app -c /home/zpark/zpark/gunicorn.conf.py
80720 /home/zpark/venvs/zpark/bin/python3.6 /home/zpark/venvs/zpark/bin/gunicorn zpark:app -c /home/zpark/zpark/gunicorn.conf.py
```

Use the nginx config snippet below to either: build a new `server`
config block or add a new `location` block to an existing server. This
config is not enough on its own to fully configure nginx; you will need
to integrate this example into your fully built `nginx.conf`. Since
you're looking at `nginx.conf` anyways, I recommend you read the
[Pitfalls and Common
Mistakes](https://www.nginx.com/resources/wiki/start/topics/tutorials/config_pitfalls/)
guidance document in order to ensure your configuration is follow best
practice.

```
[...]
location /zpark {
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Host $host;
    proxy_redirect off;
    proxy_pass http://zpark.app;
}
[...]
upstream zpark.app {
	server unix:/tmp/gunicorn.zpark.sock fail_timeout=0;
}
[...]
```

(Re)start nginx and ensure there are no errors. You should now be able
to browse to the `/zpark/api/v1/ping` URL and receive an "access denied"
message (with an HTTP status code 401) in JSON format. If you recieve a
"Bad Gateway (502)" error, ensure that Gunicorn is running and that both
Gunicorn and nginx are using the same fully qualified path to the
`.sock` file.

## Install the Alert Script on the Zabbix Server

Zabbix cannot natively talk to the Zpark bot's API but Zabbix can be
configured to run a shell script in response to an alert and the script
can then pass information on to Zpark using its API.

Copy the `zpark_alert.sh` script to the Zabbix server and put it in the
directory that is configured as the Zabbix `AlertScriptsPath`.

```
# grep AlertScriptsPath /etc/zabbix/zabbix_server.conf
AlertScriptsPath=/etc/zabbix/scripts/
# cp /home/zpark/zpark/zpark_alert.sh /etc/zabbix/scripts
```

Make sure that the script has read and execute permissions for the user
that the Zabbix server process runs as.

```
# chown _zabbix /etc/zabbix/scripts/zpark_alert.sh
# chmod 500 /etc/zabbix/scripts/zpark_alert.sh
```

Edit the `zpark_alert.sh` file and set the following variables:

- `zpark_url`
	- The fully qualified URL to your Zpark bot. This will be highly
	  dependent on how you configured nginx. Include the scheme
	  (`http` or `https`), the FQDN (`www.domain.local`) and the URI
	  (`/zpark`).

	  Eg:
	  `zpark_url="https://www.domain.local/zpark"`

- `zpark_api_token`
	- The Zpark API token. Copy and paste the value of the
	  `ZPARK_API_TOKEN` setting from the `app.cfg` file.

	  Eg:
	  `zpark_api_token="e0c297f5....5l2j2"`

## Configure Zabbix

Now configure Zabbix to utilize the alert script in order to send alerts
to Zpark.

Create a new media type by logging into the Zabbix web UI and navigating
to Administration > Media types. Create a new media type named `Zpark`
with the following settings:

- Type: `Script`
- Script name: `zpark_alert.sh`
- Script parameters:
	- `{ALERT.SENDTO}`
	- `{ALERT.SUBJECT}`
	- `{ALERT.MESSAGE}`
- Enabled: checked

![Zabbix media types](img/zabbix_media_types.jpg)

It's important the the media settings be entered exactly as shown.

Create a Zabbix user account which will represent a Spark user and will
define things like the notification schedule for the Spark user and
severity level(s) the user should be notified about. Alternatively, if
you already have a Zabbix user account that you want to add Spark
notifications to, just skip the part about adding a new account and jump
to the part about adding new media to the user.

Create the Zabbix user by navigating to Administration > Users. Choose
to "create user" and add them to the appropriate group(s). If this
account is for notification only and not meant to be a login account to
Zabbix, add the account to the `Read Only` group and nothing more. Also
ensure `Auto-login` is off and set a password on the account.

![Zabbix new user](img/zabbix_users_newuser.jpg)

Click over to the `Media` tab and click `Add` (inside the `Media` box;
not on the button). Choose `Zpark` in the dropdown and then set the `Send
to` field to the email address that you use to sign into your Cisco
Spark account. It's important this field is correct otherwise the bot
will not me able to send you any messages. Optionally, modify the
schedule and severity information.

![Zabbix new user](img/zabbix_add_media_to_user.jpg)

When finished with the media, click `Add` and then click the `Add`
button back on the Media tab.

![Zabbix user media](img/zabbix_users_media_tab_finished.jpg)

Lastly, configure a new action by browsing to Configuration > Actions
and clicking on the "Create action" button. Fill out the action as
follows:

- Name: `Zpark Alert`
- Conditions: *Leave at default*

![Zabbix action](img/zabbix_actions_action.jpg)

On the operations tab, modify the `Default subject` and `Default
message` settings as you see fit. Most importantly though, click the
`New` link in the "Operations" box.

![Zabbix action](img/zabbix_actions_operations.jpg)

Click the `Add` link in the "Send to Users" box and select the Zabbix
user you created earlier. All of the other operational detail options
can be left at defaults. Click the `Add` link once again to add the
operation to the alert.

![Zabbix action](img/zabbix_actions_operations_new.jpg)

Click over to the "Recovery operations" tab and click the `New` link in
the "Operations" box. In the `Operation type` drop-down, select `Send
recovery message`. Click the `Add` link once again to add the operation
to the alert.

![Zabbix action](img/zabbix_actions_recovery_new.jpg)

Save the action by clicking on the `Add` button. The `Zpark Alert`
action should now be shown in the list of system actions.

![Zabbix action](img/zabbix_actions_recovery_saved.jpg)

For information on how alerts and actions can be customized, check out
the sections in the [Zabbix manual](https://www.zabbix.com/manuals)
that deal with events and notifications upon events.

## Create Spark Webhooks

A [webhook](https://developer.ciscospark.com/webhooks-explained.html) is what
Spark uses to notify Zpark that a command has been issued. A webhook is just
an HTTP POST that's sent to Zpark that contains information such as what
the command was, who sent it, etc. If a webhook is not configured, Zpark will
not be able to respond to any commands.

There is a CLI script in the Zpark directory that will create a webhook.
You can run this script as the `\_zpark` user:

```
% workon zpark        # activate your venvironment
% cd /home/zpark/zpark/cli
% python create_spark_webhook.py
```

The details of the new webhook will be displayed but that's for informational
purposes only; you needn't record or do anything with that information.

The webhook will be configured to use the URL stored in the
`ZPARK_SERVER_URL` configuration setting which is why it's important to
ensure the accuracy of this setting.

There are additional scripts in the `cli` directory to show all configured
webhooks (`show_spark_webhooks.py`) and delete a webhook
(`delete_spark_webhook.py`).

## Test Notifications

If everything has gone well up to this point, you're ready to test!
Before you start:

- Make sure that Gunicorn is running
- Make sure that nginx is running and has loaded your updated nginx.conf
  that includes the configuration for Zpark
- Log into your Cisco Spark account using either the web interface,
  desktop app or mobile app

In order to complete the test, you need to trigger an alert in Zabbix.
You can do this either
- Performing an action that will cause one of your already-configured
  triggers to fire. This could be something like stopping the
  `zabbix\_agent` process on a server for more than 5 minutes or
  filling up a disk partition.
- Importing the Zabbix template below and using it for a simple,
  non-impactful alert test.

If you chose to use an already configured trigger, go ahead and trip it.
You should shortly receive a new direct message in your Spark client
from the Zpark bot informing you of the alert.

If you wish to use the testing trigger, download the
[zbx\_zpark\_test\_alert\_template.xml](files/zbx_zpark_test_alert_template.xml)
file and import it into Zabbix on the Configuration > Templates screen.
A new template called `Template Zpark Test Alert` will be created.

![Zabbix template](img/zabbix_import_template.jpg)

Edit the template and assign a UNIX machine to the template.

![Zabbix template](img/zabbix_configure_alert_template.jpg)

In order to trigger the test alert, log into the server and create a
file named `/tmp/zparktest`. Within 30 seconds an alarm will be raised
and shortly after that you should receive a new direct message from your
Zpark bot informting you of the alarm. Delete the `/tmp/zparktest` file
and the bot will soon notify you that the alarm has cleared.

## Test Bot Commands

Test that Zpark will respond to your commands by starting a 1-on-1 Spark
conversation with the bot and issuing a command such as `show status`. Zpark
should respond rather quickly with some Zabbix status information.

Repeat the test but this time in a multi-person Spark space. Make sure you
remember to "at-mention" the bot this time: the Spark security architecture
requires that bots be "at-mentioned" otherwise the bot will not "see" the
command. Eg:

```
@zparkbot show status
```

**Wrong**:
```
show status
zparkbot show status
@zparkbot, show status
@zparkbot: show status
```

Troubleshooting:
- If the 1-on-1 room test doesn't work:
	- Verify your nginx settings are correct as per the instructions above
	- Verify that you've created a webhook with Spark and that it's
	  pointing to the correct address for your Zpark vhost in nginx (use
	  the `show_spark_webhooks.py` CLI script)
	- Verify that the Zpark vhost in nginx is reachable from the Internet;
	  verify necessary firewall policies are in place
	- Check the nginx access log: ensure you can see the Spark service
	  making requests to the Zpark vhost
	- Check the nginx error log
- If the 1-on-1 room test works but the multi-person room does not:
	- Verify you're properly "at-mentioning" the bot. See the examples
	  above
	- Check the nginx error log
	- *The problem is almost certainly in how you're communicating with the
	  bot and not something on the server*

## Zpark Commands

This is a list of commands that Zpark supports:

- `show issues`
	Show the list of active Zabbix issues, the same as what's displayed
	on the Zabbix web dashboard.
- `show status`
	Show Zabbix status, including number of hosts, items, and triggers,
	the same as what's displayed on the Zabbix web dashboard.

## About

Zpark was created by [Joel Knight](https://www.packetmischief.ca). You can
contact Joel using any of the methods on
[this page](https://www.packetmischief.ca/contact).

Copyright (c) 2017 Joel Knight

