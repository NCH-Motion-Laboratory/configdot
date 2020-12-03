# configdot

configdot is a minimalistic library providing a config object and INI file parser for configuration of Python programs. Compared to modules such as `ConfigParser` and `ConfigObj`, the benefits are:

* The INI file entries are evaluated as Python expressions by `ast.literal_eval()`, so several Python types (such as tuples, lists, and dicts) can be directly used in the INI file.
* Instead of the dict syntax `config['section']['item']`, configdot supports attribute access, so you can write `config.section.item` instead.

## Installation

    pip install configdot

## Basic usage

Given the silly `demo.ini` file below:
```
# The food section
[food]
fruits = ['Apple', 'Banana', 'Kiwi']
calories = {'Apple': 50, 'Banana': 100}
recipe = 'Fruit salad'
# this is the cost of the recipe in euros
cost = 10

# The drinks section
[drinks]
favorite = 'Coke'
```

You can load it by:

    import configdot
    config = configdot.parse_config('demo.ini')

To get a section:

    config.food

Output:

    <ConfigContainer| items: ['recipes', 'cost', 'calories', 'fruits']>

You can directly get the items under a section by attribute access:

    config.food.calories

The output is a Python dict:

    {'Apple': 50, 'Banana': 100}

You can also modify items directly by the attribute syntax:

    config.food.cost = 20

## There's more

You can get INI file comments for a section: 

    config.food._comment

Output:

    'The food section'

You can also get comments for the items. In the INI file, they should be placed on the line preceding the item definition. To get a comment for an item, you need to use the dict-like syntax:

    config.food['cost']._comment

Output:
    
    'this is the cost of the recipe in euros'
    
To update values in a config instance using another instance:

    configdot.update_config(config, config_new)

This can be useful e.g. to update a global config with some user-defined values.
  
Finally, you can dump the config item as text:

    print(configdot.dump_config(config))

Output:

    # The food section
    [food]
    # 
    calories = {'Apple': 50, 'Banana': 100}
    # this is the cost of the recipe in euros
    cost = 10
    # 
    fruits = ['Apple', 'Banana', 'Kiwi']
    # 
    recipe = 'Fruit salad'

## Miscellaneous notes

The INI parser supports multiline definitions, i.e. you can write something like:

    [foo]
    bar = [[1, 0, 0],
           [0, 1, 0],
           [0, 0, 1]]

configdot supports nested configuration objects (sections inside sections), but this is not yet implemented in the INI file parser.

configdot should work for both Python 2 and Python 3. If using Python 2, extended characters in the configuration will likely cause problems, since `ast.literal_eval()` does not produce Unicode.











    
    
    
