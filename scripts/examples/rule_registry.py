import time

from openhab.osgi import get_service
from openhab.log import logging
log = logging.getLogger("registry_example")

rule_registry = get_service("org.eclipse.smarthome.automation.RuleRegistry")

# Get rules by tags
# Tags can be set in rule constructors
# Example: self.tags = ["tag1", "tag2"]
rules = rule_registry.getByTag("a")

for rule in rules:
    rule_status = rule_registry.getStatusInfo(rule.UID)
    log.info("rule_status=%s", rule_status)
    
    # disable a rule
    rule_registry.setEnabled(rule.UID, False)
    
    # later...
    time.sleep(1)
    
    # reenable the rule
    rule_registry.setEnabled(rule.UID, True)
    
    # fire the rule manually (with inputs)
    log.info("triggering rule manually")
    rule_registry.runNow(rule.UID, False, {'name': 'EXAMPLE'})
