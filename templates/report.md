# NetworkInformation statistics
Hits count: {{hits_count}}

User agents with API support: {{supported_count}}

And without that: {{unsupported_count}}

## Logged devices
{% for item in all_devices %}
  * {{item}}
{% endfor %}

## User agents stats
User agents with support:
{% for item in supported_items %}
  * {{item}}
{% endfor %}

User agents without support:
{% for item in unsupported_items %}
  * {{item}}
{% endfor %}

## Connections stats
Collected connection_type values:
{% for item in connection_types %}
  * {{item}}
{% endfor %}

Collected downlink_max values:
{% for item in downlink_max_values %}
  * {{item}}
{% endfor %}

## Detailed stats for UAs that support API
```
{{detailed_stats}}
```
