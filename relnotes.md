# Release Notes

### v1.2.1

This is a security only release.

- Upgrade third-party modules in response to security issues:
  - urllib3 1.24.2 (CVE-2019-11324)
  - Jinja2 2.10.1 (CVE-2019-10906)

### v1.2.0

- Upgrade third-party modules in response to security issues
  - Requests 2.2.20 (CVE-2018-18074)
  - urllib 1.23 (CVE-2018-20060)
  - Flask 0.12.4 (CVE-2018-1000656)
- Improved the output of "show status" when Zpark is talking to Zabbix 3.4+.
  Stats better reflect what's shown in the Zabbix dashboard now. Note that
  the count of disabled triggers doesn't match due to some behavioral
  differences between the data returned by the Zabbix API vs the Zabbix
  client/server protocol. There's not much that Zpark can do about that.
- New setting `ZABBIX_TLS_CERT_VERIFY`. Set this to `False` if your Zabbix
  installation uses a self-signed certificate. Defaults to `True`.
- In order to aid troubleshooting, Zpark will emit a log entry when it
  receives a command from a Spark user that isn't on the trusted users list.
  This message is emitted at log level `DEBUG` which can be configured by
  modifying the `API_LOG_HANDLER` setting.

```
API_LOG_HANDLER = {
	'class': 'logging.handlers.SysLogHandler',
	'address': '/dev/log',
	'facility': 'local6',
	'level': 'DEBUG'
}
```
You shouldn't have logging set to `DEBUG` unless you're troubleshooting. It
creates an opportunity for someone to fill your log file with their arbitrary
commands.

### v1.1.0

- The `SPARK_TRUSTED_USERS` config parameter now supports specifying
  @domain.com to make it easy to whitelist users from an entire organization.
  Eg: `SPARK_TRUSTED_USERS = ['@example.com', 'root@example.com']`
- Allow [`;:,`] as a delimeter between the bot's name and the command in
  @-mention messages. Eg: `@bot, show issues`
- New command: `hello`. The bot will respond with an introduction about itself
  including a list of supported commands. Note the bot will only respond to
  `hello` if the user is on the list of trusted users.
- A much better job is done to determine the bot's own name when it receives
  a message via @-mention. This allows the bot to have a more complex name
  and to respond to @-mention commands when there is another user in the room
  with a similar name to the bot.

### v1.0.0

First release!

- Relays new Zabbix alerts (which are generated from Zabbix events) to Spark
  user(s) and/or room(s).
- Relays Zabbix "all clear" alerts (which are generated when a recovery
  condition is met) to Spark user(s) and/or room(s).
- Configure Spark message recipients based on a combination of alert
  severity, time of day, host group, or other arbitrary criteria. eg:
  - Send all alerts to the Spark room "Network Engineers" between 0800-2000 Mon-Fri
  - Send alerts with severity "critical" or higher to engineers Joe, Jill, and
    Mark 24x7, using their Spark accounts "joe@example.com", "jill@example.com"
    and "mark@example.com".
- Immediate notification of alerts. As soon as the bot receives an alert
  from Zabbix, it is immediately sent to Spark; there is no queueing or
  batching of messages.
- Interrogate information from Zabbix by issuing commands to the bot
  on Spark. Eg, "show status".
- Decentralized: run the bot on the Zabbix server or on a separate
  server, your choice.
