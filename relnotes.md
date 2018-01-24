# Release Notes

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
