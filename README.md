# Jython scripting for openHAB 2.x

This is a repository of experimental Jython code that can be used 
with the [Eclipse SmartHome](https://www.eclipse.org/smarthome/) platform and [openHAB 2](http://docs.openhab.org/) Jython scripting. 
Also see the [openHAB 2 scripting documentation](http://docs.openhab.org/configuration/jsr223.html).

_NOTE: To use Jython for defining rules, the Experimental Rule Engine add-on must be installed in openHAB 2._

## Applications

The [JSR223 scripting extensions](https://www.jcp.org/en/jsr/detail?id=223) can be used for general scripting purposes, 
including defining rules and associated SmartHome rule "modules" (triggers, conditions, actions). 
Some possible applications include integration testing of complex rule behaviors or prototyping new OH2/ESH functionality.

(_JSR223_ refers to a Java specification request for adding scripting to the Java platform. 
That term will not be used in Java versions 9 and above. 
The previous JSR223 functionality will be provided by the Java `javax.script` package in the standard runtime libraries.)

The scripting can be used for other purposes like automated integration testing 
or to access the OSGI framework (using or creating services, for example).

## Jython Scripts and Modules

It's important to understand the distinction between Jython _scripts_ and Jython _modules_. 
In this repo, scripts are in the `scripts` directory and modules are in the `lib` directory.

A Jython script is loaded by the `javax.script` script engine manager (JSR223) integrated into openHAB 2. 
Each time the file is loaded, OH2 creates a execution context for that script.
When the file is modified, OH2 will destroy the old script context and create a new one.
This means any variables defined in the script will be lost when the script is reloaded.

A Jython module is loaded by Jython itself through the standard Python `import` directive and uses `sys.path`.
The normal Python module loading behavior applies.
This means the module is loaded once and is not reloaded when the module source code changes.

# File Locations

Scripts should be put into the `automation/jsr223` subdirectory hierarchy of your OH2 configuration directory.
For example, in a Linux apt installation this would be `/etc/openhab2/automation/jsr223`.

Some scripts should be loaded before others because of dependencies between the scripts. 
Scripts that implement OH2 components (like trigger types, item providers, etc.) are one example.
I recommend putting these scripts into a subdirectory called `000_Components`. 
The name prefix will cause the scripts in the directory to be loaded first.
I also recommend naming the component files with a "000_" prefix 
because there are currently bugs in the file loading behavior of OH2.

Example:

```text
/etc/openhab2/automation/jsr223
    /000_Components
       000_StartupTrigger.py
    myotherscript.py
```

Jython modules can be placed anywhere but the Python path must be configured to find them.
There are several ways to do this. 
You can add a `-Dpython.path=mypath1:mypath2` to the JVM command line by modifying the OH2 startup scripts.
You can also modify the `sys.path` list in a Jython script that loads early (like a component script).

I put my Jython modules in `/etc/openhab2/lib/python` (Linux apt installation).
Another option is to checkout the GitHub repo in some location and use a directory soft link (Linux) 
from `/etc/openhab2/lib/python/openhab` to the GitHub workspace `lib\openhab` directory.

## Defining Rules

One the primary use cases for the JSR223 scripting is to define rules 
for the [Eclipse SmartHome (ESH) rule engine](http://www.eclipse.org/smarthome/documentation/features/rules.html).

The ESH rule engine structures rules as _modules_ (triggers, conditions, actions). 
Jython rules can use rule modules that are already present in ESH and can define new modules that can be used outside of JSR223 scripting.

### Rules: Raw ESH API

Using the raw ESH API, the simplest rule definition would look something like:

```python
scriptExtension.importPreset("RuleSupport")
scriptExtension.importPreset("RuleSimple")

class MyRule(SimpleRule):
    def __init__(self):
        self.triggers = [
             Trigger("MyTrigger", "core.ItemStateUpdateTrigger", 
                    Configuration({ "itemName": "TestString1"}))
        ]
        
    def execute(self, module, input):
        events.postUpdate("TestString2", "some data")

automationManager.addRule(MyRule())
```

    Note: trigger names must be unique within the scope of a rule instance. 

This can be simplified with some extra Jython code, which we'll see later. 
First, let's look at what's happening with the raw functionality.

When a Jython script is loaded it is provided with a _JSR223 scope_ that predefines a number of variables. 
These include the most commonly used core types and values from ESH (e.g., State, Command, OnOffType, etc.). 
This means you don't need a Jython import statement to load them.

For defining rules, additional symbols must be defined. 
Rather than using a Jython import (remember, JSR223 support is for other languages too), 
these additional symbols are imported using:

```python
scriptExtension.importPreset("RuleSupport")
scriptExtension.importPreset("RuleSimple")
```

The `scriptExtension` instance is provided as one of the default scope variables. 
The RuleSimple preset defines the `SimpleRule` base class.  
This base class implements a rule with a single custom ESH Action associated with the `execute` function. 
The list of rule triggers are provided by the triggers attribute of the rule instance.

The trigger in this example is an instance of the `Trigger` class. 
The constructor arguments define the trigger, the trigger type string and a configuration.

The `events` variable is part of the default scope and supports access to the ESH event bus (posting updates and sending commands). 
Finally, to register the rule with the ESH rule engine it must be added to the `ruleRegistry`. 
This will cause the triggers to be activated and the rule will fire when the TestString1 item is updated.

### Rules: Using Jython extensions

To simplify rule creation even further, Jython can be used to wrap the raw ESH API. 
The current experimental wrappers include trigger-related classes so the previous example becomes:

```python
# ... preset calls

from openhab.triggers import ItemStateUpdateTrigger

class MyRule(SimpleRule):
    def __init__(self):
        self.triggers = [ ItemStateUpdateTrigger("TestString1") ]
        
    # rest of rule ...
```

This removes the need to know the internal ESH trigger type strings, 
define trigger names and to know configuration dictionary requirements.

#### Rule Trigger Decorators

To make rule creation _even simpler_, `openhab.triggers` defines function decorators. 
To define a function that will be triggered periodically, the entire script looks like:

```python
from openhab.triggers import time_triggered, EVERY_MINUTE

@time_triggered(EVERY_MINUTE)
def my_periodic_function():
 	events.postUpdate("TestString1", somefunction())
```

Notice there is no explicit preset import and the generated rule is registered automatically with the `HandlerRegistry`. 
Another example...

```python
from openhab.triggers import item_triggered

@item_triggered("TestString1", result_item_name="TestString2")
def my_item_function():
	if len(items['TestString1']) > 100:
		return "TOO BIG!"
```
The `item_triggered` decorator creates a rule that will trigger on changes to TestString1. 
The function result will be posted to TestString2. 
The `items` object is from the default scope and allows access to item state. 
If the function needs to send commands or access other items, it can be  done using the `events` scope object. 

A decorator can also be used to trigger a function invocation from an item group 
and provide the event related to the triggering item.

```python
@item_group_triggered("TestGroup", result_item_name="TestString1")
def example(event):
    return event.itemName + " triggered me!"
```

This decorated function will trigger from a change to any member of the TestGroup item.
When the function is called it is provided the event instance that triggered it.
The specific trigger data depends on the event type.
For example, the `ItemStateChangedEvent` event type has `itemName`, `itemState`, and `oldItemState` attributes.

## Component Scripts

These scripts are in the `scripts/components` subdirectory. 
They should be copied to the `automation/jsr223/components` directory of your openHAB 2 installation to use them. 
The files have a numeric prefix to cause them to be loaded before regular user scripts.

### Script: [`000_StartupTrigger.py`](scripts/components/000_StartupTrigger.py)

Defines a rule trigger that triggers immediately when a rule is activated. 
This is similar to the same type of trigger in openHAB 1.x.

### Script: [`000_OsgiEventTrigger.py`](scripts/components/000_OsgiEventTrigger.py)

This rule trigger responds to events on the OSGI EventAdmin event bus.

### Script: [`000_DirectoryTrigger.py`](scripts/components/000_DirectoryTrigger.py)

This trigger can respond to file system changes.
For example, you could watch a directory for new files and then process them.

```python
@rule
class DirectoryWatcherExampleRule(object):
    def getEventTriggers(self):
        return [ DirectoryEventTrigger("/tmp", event_kinds=[ENTRY_CREATE]) ]
    
    def execute(self, module, inputs):
        logging.info("detected new file: %s", inputs['path'])
```

### Script [`000_JythonTransform.py`](scripts/components/000_JythonTransform.py)

This script defines a transformation service (identified by "JYTHON") that will process a value using a Jython script. 
This is similar to the Javascript transformer.

### Scripts: Jython-based Providers

   * [`000_JythonThingProvider.py`](scripts/components/000_JythonThingProvider.py)
   * [`000_JythonThingTypeProvider.py`](scripts/components/000_JythonThingTypeProvider.py)
   * [`000_JythonBindingInfoProvider.py`](scripts/components/000_JythonBindingInfoProvider.py)
   * [`000_JythonItemProvider.py`](scripts/components/000_JythonItemProvider.py)
   
These components are used to support Thing handler implementations.

## Scripting Examples

These scripts show example usage of various scripting features. 
Some of the examples are intended to provide services to user scripts so they have a numeric prefix to force them to load first 
(but after the general purpose components).

### Script: [`000_ExampleExtensionProvider.py`](scripts/examples/000_ExampleExtensionProvider.py)

This component implements the openHAB extension provider interfaces and can be used to provide symbols to a script
namespace.

### Script: [`000_LogAction.py`](scripts/examples/000_LogAction.py)

This is a simple rule action that will log a message to the openHAB log file.

### Script: [`100_EchoThing.py`](scripts/examples/100_EchoThing.py)

Experimental Thing binding and handler implemented in Jython. (At the time of this writing, 
it requires a small change to the ESH source code for it to work.) 
This simple Thing will write state updates on its input channel to items states linked to the output channel.

### Script: [`000_JythonConsoleCommand.py`](scripts/examples/000_JythonConsoleCommand.py)

This script defines an command extension to the OSGI console. 
The example command prints some Jython  platform details to the console output.

### Script: [`actors.py`](scripts/examples/actors.py)

Shows an example of using the Pykka actors library. The Pykka library must be in the Java classpath.

### Script: [`esper_example.py`](scripts/examples/esper_example.py)

Shows an example of using the Esper component. The 000_Esper.py component script must be installed.

### Script: [`rule_decorators.py`](scripts/examples/rule_decorators.py)

Provides examples of using the trigger-related rule decorators on functions as an alternative to explicit rule and trigger classes.

### Script: [`testing_example.py`](scripts/examples/testing_example.py)

Examples of unit testing.

### Script: [`dirwatcher_example.py`](scripts/examples/dirwatcher_example.py)

Example of a rule that watches for files created in a specified directory.

### Script: [`rule_registry.py`](scripts/examples/rule_registry.py)

This example shows how to retrieve the RuleRegistry service and use it to query rule instances based on tags,
enable and disable rule instances dynamically, and manually fire rules with specified inputs.

## Jython Modules

One of the benefits of Jython over the openHAB Xtext scripts is that you can use the full power of Python packages 
and modules to structure your code into reusable components. 
The following are some initial experiments in that direction.

There are example scripts in the `scripts/examples` subdirectory.

### Module: [`openhab.rules`](lib/openhab/rules.py)

The rules module contains some utility functions and a decorator for converting a Jython class into a `SimpleRule`.
The following example shows how the rule decorator is used:

```python
from openhab.rules import rule, addRule
from openhab.triggers import StartupTrigger

@rule
class ExampleRule(object):
    """This doc comment will become the ESH Rule documentation value for Paper UI"""
    def getEventTriggers(self):
        return [ StartupTrigger() ]

    def execute(self, module, inputs):
        self.log.info("rule executed")

addRule(MyRule())
```

The decorator adds the SimpleRule base class and will call either `getEventTriggers` or `getEventTrigger` (the OH1 function) 
to get the triggers, if either function exists. 
Otherwise you can define a constructor and set `self.triggers` to your list of triggers.

The `addRule` function is similar to the `automationManager.addRule` function except 
that it can be safely used in Jython modules (versus scripts).
Since the `automationManager` is different for every script scope 
the `openhab.rules.addRule` function looks up the automation manager for each call.

The decorator also adds a log object based on the name of the rule (`self.log`, can be overridden in a constructor) and 
wraps the event trigger and `execute` functions in a wrapper that will print nicer stack trace information if an exception 
is thrown.

### Module: [`openhab.triggers`](lib/openhab/triggers.py)

This module includes trigger subclasses and function decorators to simplify Jython rule definitions.

Trigger classes:

* __ItemStateChangeTrigger__
* __ItemStateUpdateTrigger__
* __ItemCommandStrigger__
* __ItemEventTrigger__ (based on "core.GenericEventTrigger")
* __CronTrigger__
* __StartupTrigger__ - fires when rule is activated (implemented in Jython)
* __DirectoryEventTrigger__ - fires when directory contents change (Jython, see related component for more info).
* __ItemAddedTrigger__ - fires when rule is added to the RuleRegistry (implemented in Jython)
* __ItemRemovedTrigger__ - fires when rule is removed from the RuleRegistry (implemented in Jython)
* __ItemUpdatedTrigger__ - fires when rule is updated in the RuleRegistry (implemented in Jython, not a state update!)

Trigger function decorators:

* __time_triggered__ - run a function periodically
* __item_triggered__ - run a function based on an item event
* __item_group_triggered__ - run a function based on an item group event

### Module: [`openhab.actions`](lib/openhab/actions.py)

This module discovers action services registered from OH1 or OH2 bundles or add-ons.
The specific actions that are available will depend on which add-ons are installed.
Each action class is exposed as an attribute of the `openhab.actions` Jython module.
The action methods are static methods on those classes 
(don't try to create instances of the action classes).

```python
from openhab.actions import Astro
from openhab.log import logging
from java.util import Date

log = logging.getLogger("org.eclipse.smarthome.automation")

# Use the Astro action class to get the sunset start time.
log.info("Sunrise: %s", Astro.getAstroSunsetStart(Date(2017, 7, 25), 38.897096, -77.036545).time)
```

### Module: [`openhab.log`](lib/openhab/log.py)

This module bridges the Python standard `logging` module with ESH logging. Example usage:

```python
from openhab.log import logging

logging.info("Logging example from root logger")
logging.getLogger("myscript").info("Logging example from root logger")  
```

### Module: [`openhab.items`](lib/openhab/items.py)

This module allows runtime creation and removal of items.

```python
import openhab.items

openhab.items.add("_Test", "String")

# later...
openhab.items.remove("_Test")

```

### Module: [`openhab.testing`](lib/openhab/testing.py)

One of the challenges of ESH/openHAB rule development is verifying that rules are behaving 
correctly and have broken as the code evolves. T
his module supports running automated tests within a runtime context. 
To run tests directly from scripts:

```python
import unittest # standard Python library
from openhab.testing import run_test

class MyTest(unittest.TestCase):
	def test_something(self):
		"Some test code..."

run_test(MyTest) 
```

The module also defines a rule class, `TestRunner` that will run a testcase 
when an switch item is turned on and store the test results in a string item.

### Module: [`openhab.osgi`](lib/openhab/osgi/__init__.py)

Provides utility function for retrieving, registering and removing OSGI services.

```python
import openhab.osgi

item_registry = osgi.get_service("org.eclipse.smarthome.core.items.ItemRegistry")
```

### Module: [`openhab.osgi.events`](lib/openhab/osgi/events.py)

Provides an OSGI EventAdmin event monitor and rule trigger. 
This can trigger off any OSGI event (including ESH events). 
_Rule manager events are filtered to avoid circular loops in the rule execution._

```python
class ExampleRule(SimpleRule):
    def __init__(self):
        self.triggers = [ openhab.osgi.events.OsgiEventTrigger() ]
            
    def execute(self, module, inputs):
        event = inputs['event']
        # do something with event
```

### Module: [`openhab.jsr223`](lib/openhab/jsr223.py)

One of the challenges of JSR223 scripting with Jython is that Jython modules imported 
into scripts do not have direct access to the JSR223 scope types and objects. 
This module allows imported modules to access that data. Example usage:

```python
# In Jython module, not script...
from openhab.jsr223.scope import events

def update_data(data):
	events.postUpdate("TestString1", str(data))
```

### Module: [`openhab`](lib/openhab/__init__.py)

This module (really a Python package) patches the default scope `items` object 
so that items can be accessed as if they were attributes (rather than a dictionary).

It can also be used as a module for registering global variables that will outlive script reloads.

```python
import openhab

print items.TestString1
```

Note that this patch will be applied when any module in the `openhab` package is loaded.
