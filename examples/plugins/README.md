Plugin Examples
===============

Some example plugins that can be used as a starting point for custom development:

  * routing rules plugin that uses different notification paths for different customers.
    ie. PagerDuty for Tier 1 customers, Slack for Tier 2 and nothing for Tier 3 customers.

  * transient alert plugin based on the `is_flapping()` helper method
    will reject alerts that have repeatedly changed from an alert severity
    to `normal` within a short period of time. eg. more than twice in 2 minutes

See the [alerta contrib repo](https://github.com/alerta/alerta-contrib/tree/master/plugins) for
a comprehensive list of plugins that can be used as-is or as examples for your own environment.
