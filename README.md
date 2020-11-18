# configdot

configdot provides a config object and INI file parser for configuration of Python programs. Compared to modules such as`ConfigParser` and `ConfigObj`, it has two main benefits:

* The INI file entries are parsed by `ast.literal_eval()`, so several Python types (such as tuples, lists, and dicts) can be directly defined in the INI file.
* Instead of the dict syntax `config['section']['item']`, configdot supports attribute access, so you can write `config.section.item` instead.

## Quick example

Given the `demo.ini` file below:
```
# The food section
[food]
fruits = ['Apple', 'Banana', 'Kiwi']
calories = {'Apple': 50, 'Banana': 100}
recipe = 'Fruit salad'
# this is the cost of the recipe in euros
cost = 10
```

You can load it by:

    import configdot
    config = configdot.parse_config('demo.ini')

To get a section (a `ConfigContainer` instance):

    config.food

Output:

    <ConfigContainer| items: ['recipes', 'cost', 'calories', 'fruits']>

You can directly get the items under a section by attribute access:

    config.food.calories

Output:

    {'Apple': 50, 'Banana': 100}

You can also modify items directly by the attribute syntax:

    config.food.cost = 20

Comments can be read from the INI file:

    configdot.get_description(config.food)
