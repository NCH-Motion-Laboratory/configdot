# configdot

configdot is a minimalistic INI file parser for configuration of Python programs. Compared to packages such as `ConfigParser` and `ConfigObj`, the benefits are:

* The INI file entries are evaluated as Python expressions by `ast.literal_eval()`, so several Python types (such as tuples, lists, and dicts) can be directly used in the INI file.
* Instead of having to write `config['section']['item']`, configdot supports accessing items as attributes, so you can write `config.section.item` instead.
* The sections can be nested arbitrarily deep, so you can create subsections (and even subsubsubsections if you really want to).


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

The output is a normal Python dict:

    {'Apple': 50, 'Banana': 100}

You can also modify items directly by the attribute syntax:

    config.food.cost = 20

## Getting sections and items from a config

`ConfigContainer` instances support the iteration protocol. You can get the section names and sections from a config as follows:

    for section_name, section in config:
        print(section_name)

The sections are also `ConfigContainer` instances, so they can be iterated over. This will give you the config items and their names:

    for item_name, item in section:
        print(item_name)

## Getting comments

You can get INI file comments for a section as follows:

    config.food._comment

Output:

    'The food section'

You can also get comments for the items. In the INI file, they should be placed on the line preceding the item definition. For this, you need to use the dict-like syntax:

    config.food['cost']._comment

Output:
    
    'this is the cost of the recipe in euros'
    
## Updating and dumping a config

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

## INI file syntax

The INI file contains of section headers, subsection headers, items and comments.

Section headers are denoted as `[section]`. Subsection headers are written as `[[subsection]]`. Subsections must occur inside sections.

Item definitions must be written as `item_name = value`. For the value, the following Python types are supported: strings, bytes, numbers, tuples, lists, dicts, sets, booleans, and None. Nested types (e.g. lists of lists) are supported. Items are standalone expressions, i.e. they cannot reference other items defined in the INI file.

The expressions are parsed with `ast.literal_eval()`, with the associated limitations (e.g. no support for indexing). 

Items must occur inside a section or subsection.

Items and sections support multiline definitions. The following is valid:

    [foo]
    bar = [[1, 0, 0],
           [0, 1, 0],
           [0, 0, 1]]

Comments are written as 

    # comment
    
or alternatively

    ; comment
    
Comments are associated with an item, section, or a subsection, and appear before the corresponding definition. A comment may consist of multiple lines. Inline comments are not allowed:

    # following line is NOT allowed
    x = 1  # this is the variable x


## Compatibility

configdot requires Python >= 3.6. There are no operating system specific features.

## Miscellaneous

Why not just have the config files in Python instead? First, depending on your setup, arbitrary Python code in config files may be a security risk. Second, you still need to create the section hierarchy by e.g. using empty classes, which will make your setup files less readable than with the INI syntax.

