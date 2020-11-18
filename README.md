# configdot

configdot provides a config object and INI file parser for configuration of Python programs. It has two main benefits:

* The INI file entries are parsed by `ast.literal_eval()`, so several Python types (such as tuples, lists, and dicts) can be directly defined in the INI file.
* Instead of the dict syntax `config['section']['item']`, configdot supports attribute access, so you can write `config.section.item` instead.

Quick example:

Given the `demo.ini` file below:
```
# The food section
[food]
fruits = ['Apple', 'Banana', 'Kiwi']
calories = {'Apple': 50, 'Banana': 100}
recipes = 'Fruit salad'
cost = 10
```

One can do:

```
import configparser
config = configparser.parse_config('demo.ini')

config.food
```

