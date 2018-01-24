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

