# configdot

configdot is a minimalistic INI file parser for configuration of Python programs. Compared to packages such as `ConfigParser` and `ConfigObj`, the benefits are:

* The INI file entries are safely evaluated as Python expressions, so several Python types (such as tuples, lists, and dicts) can be directly used in the INI file.
* Instead of having to write `config['section']['item']`, you can write `config.section.item` when accessing the configuration.
* The sections can be nested arbitrarily deep, so you can create subsections (and subsubsubsections if you really want to).


## Installation

    pip install configdot

## Basic usage

For an example, consider a `demo.ini` file with the following contents:

```
# The food section
[food]
fruits = ['Apple', 'Banana', 'Kiwi']
# calories for some of the fruit
calories = {'Apple': 50, 'Banana': 100}

# The drinks section
[drinks]
favorite = 'Coke'

# subsection for alcoholic drinks
[[alcoholic]]
favorite = 'beer'
```

You can load it as follows:

    import configdot
    config = configdot.parse_config('demo.ini')

You can get the items under a section by attribute access:

    config.food.calories

The output is a normal Python dict:

    {'Apple': 50, 'Banana': 100}

You can modify items by the attribute syntax:

    config.food.fruits = ['Watermelon', 'Pineapple']

Items inside nested subsections can be accessed similarly:

    print(config.drinks.alcoholic.favorite)  # prints 'beer'


## Applicable INI file syntax

The INI file consists of section headers, items and comments.

Section headers are denoted as `[section]`, `[[subsection]]`, `[[[subsubsection]]]` etc. They may be nested arbitrarily deep. Subsections must occur after a section that is exactly one level higher, e.g. a `[[subsubsection]]` must occur after a `[section]`. The following is allowed:

    [foo]
    [[bar]]
    [[[baz]]]]
    [[bar2]]

The following is not allowed:

    [foo]
    [[[bar]]]]

Item definitions must be written as `item_name = value`. For the value, the following Python types are supported: strings, bytes, numbers, tuples, lists, dicts, sets, booleans, and None. Nested types (e.g. lists of lists) are supported. Items are standalone expressions, i.e. they cannot reference other items defined in the INI file. Items can occur inside any section (and must not be outside of a section).

The expressions are parsed with `ast.literal_eval()`, with the associated limitations (e.g. no support for indexing). 

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

## Extended characters

Section headers can include any Unicode word characters. Item names follow the same rules as Python identifiers.

Note that under Windows, the default text encoding is still typically CP1252. Thus, you must supply `encoding='utf-8'` to `parse_config()` if you want to use extended characters in your INI file. 

## Getting sections and items from a config

`ConfigContainer` instances support the iteration protocol. You can get the items from a container as follows. They may be `ConfigItems` or further `ConfigContainers` (in case of subsections).

    for item_name, item in config:
        print(item_name, item)

## Getting comments

You can get the INI file comments for a section as follows:

    config.food._comment

Output:

    'The food section'

You can also get comments for the items. For this, you need to use the `getitem` syntax:

    config.food['calories']._comment
    
## Updating and dumping a config

To update values in a config instance using another instance:

    configdot.update_config(config, config_new)

This can be useful e.g. to update a global config with some user-defined values.
  
You can dump the config item as text:

    print(configdot.dump_config(config))

This should reproduce the INI file.


## Compatibility

configdot requires Python >= 3.6.

## Miscellaneous

Why not just have the config files in Python instead? First, depending on your setup, arbitrary Python code in config files may be a security risk. Second, you still need to create the section hierarchy by e.g. using empty classes, which will make your setup files less readable than with the INI syntax.

