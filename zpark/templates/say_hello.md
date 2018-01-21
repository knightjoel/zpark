{% if room.type == 'group' %}
Hello <@personEmail:{{ caller.emails[0] }}|{{ caller.nickName }}>,

{% endif %}
I am a [Zpark bot](https://knightjoel.github.io/zpark). I relay alerts from a Zabbix server to Spark and I allow certain people to query information from Zabbix by sending me commands via Spark message.

You can send these commands:
- `show issues` - Show active Zabbix issues
- `show status` - Show Zabbix server stats (same as what's shown in the Zabbix UI)

Note:
- In a group space, you need to get my attention by @-mentioning me in your message.
- I only respond to commands received from a list of trusted users (and since I'm responding to you now, that means you are on the list).
{% if zpark_contact_info is not none %}

My caretaker is {{ zpark_contact_info }}.
{% endif %}
