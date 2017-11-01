{% if roomtype == 'group' %}
Hey there <@personEmail:{{ caller }}>,
{% endif %}
{% if issues %}
	{% if issues|count > 1 %}
There are currently **{{ issues|count }}** active issues (the most recent is first in the list):
	{% else %}
There is currently **one** active issue:
	{% endif %}

	{% for i in issues %}
- {{ i.host }} - {{ i.description }} - {{ i.lastchangedt }}
	{% endfor %}
{% else %}
There are currently no active issues!
{% endif %}
