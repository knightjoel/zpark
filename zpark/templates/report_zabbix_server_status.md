{% if room.type == 'group' %}
Hey there <@personEmail:{{ caller.emails[0] }}|{{ caller.nickName }}>,
{% endif %}

Zabbix server status:
- Number of hosts (enabled/disabled/templates): {{ stats.enabled_hosts_cnt }} / {{ stats.disabled_hosts_cnt }} / {{ stats.templates_cnt }} ({{ stats.enabled_hosts_cnt + stats.disabled_hosts_cnt + stats.templates_cnt }})
- Number of items (enabled/disabled/not supported): {{ stats.enabled_items_cnt }} / {{ stats.disabled_items_cnt }} / {{ stats.notsupported_items_cnt }} ({{ stats.enabled_items_cnt + stats.disabled_items_cnt + stats.notsupported_items_cnt }})
- Number of triggers (enabled/disabled/problem/ok): {{ stats.enabled_triggers_cnt }} / {{ stats.disabled_triggers_cnt }} / {{ stats.problem_triggers_cnt }} / {{ stats.ok_triggers_cnt }} ({{ stats.enabled_triggers_cnt + stats.disabled_triggers_cnt }})
- Number of web monitoring scenarios (enabled/disabled): {{ stats.enabled_httptest_cnt }} / {{ stats.disabled_httptest_cnt }}
