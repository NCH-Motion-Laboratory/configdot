# configdot

configdot provides a config object and INI file parser for configuration of Python programs. It has two main benefits:

* The INI file entries are parsed by ast.literal_eval(), so several Python types (such as tuples, lists, and dicts) can be directly defined in the INI file.
* Instead of the dict syntax `config['section']['item']`, configdot supports attribute access, so you can write `config.section.item` instead.

Quick example:

