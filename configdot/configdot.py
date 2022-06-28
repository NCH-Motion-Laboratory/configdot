# -*- coding: utf-8 -*-
"""
Parse INI files into nested config objects.


WIP:

-update func is outdated
-rewrite examples on GitHub

@author: Jussi (jnu@iki.fi)
"""
import ast
import re
import pprint
import logging
import sys

logger = logging.getLogger(__name__)


# regexes for parsing
RE_WHITESPACE = r'\s*$'  # empty or whitespace
# match line comment; group 1 will be the comment
RE_COMMENT = r'\s*[#;]\s*(.*)'
# whitespace, alphanumeric item name (at least 1 char), whitespace, equals sign,
# item value (may be anything at this point) is matched non-greedily so it doesn't
# match the trailing whitespace, trailing whitespace
RE_ITEM_DEF = r'\s*(\w+)\s*=\s*(.*?)\s*$'
# whitespace, 1 or more ['s, section name, 1 or more ]'s, whitespace, end of line
# the regex doesn't check that the opening and closing brackets match, it's
# done by the Python code instead
RE_SECTION_HEADER = r'\s*(\[+)([\w-]+)(\]+)\s*$'


def _simple_match(r, s):
    """Match regex r against string s"""
    return bool(re.match(r, s))


def _parse_item_def(s):
    """Match (possibly partial) config item definition.

    Return varname, val tuple if successful"""
    if m := re.match(RE_ITEM_DEF, s):
        varname, val = m.group(1), m.group(2)
        return varname, val


def _parse_section_header(s):
    """Match section or subsection (or subsubsection etc.) header.

    Headers are written e.g. [header] or [[header]] etc. where the number of
    brackets indicates the level of nesting (here 1 and 2, respectively)
    Returns a tuple of (sec_name, sec_level).
    """
    if m := re.match(RE_SECTION_HEADER, s):
        opening, closing = m.group(1), m.group(3)
        if (sec_level := len(opening)) == len(closing):
            return m.group(2), sec_level


def get_description(item_or_section):
    """Returns a description based on section or item comment.

    Parameters
    ----------
    item_or_section : ConfigContainer | ConfigItem
        Item or section.

    Returns
    -------
    str
        The description.

    Note: not implemented as an instance method to avoid polluting the class
    namespace.
    """
    desc = item_or_section._comment
    # currently just capitalizes first letter of comment string
    return desc[:1].upper() + desc[1:]


class ConfigItem:
    """Holds data for a config item"""

    def __init__(self, name=None, value=None, comment=None):
        if comment is None:
            comment = ''
        self._comment = comment
        self.name = name
        self.value = value

    def __repr__(self):
        return f'<ConfigItem| {self.name} = {self.value!r}>'

    def __eq__(self, other):
        return self.value == other.value and self._comment == other._comment

    @property
    def literal_value(self):
        """Returns a string that is supposed to evaluate to the value"""
        return repr(self.value)

    @property
    def item_def(self):
        """Prettyprint item definition"""
        return f'{self.name} = {pprint.pformat(self.value)}'


class ConfigContainer:
    """Holds config items (ConfigContainer or ConfigItem instances)"""

    def __init__(self, items=None, comment=None):
        # need to modify __dict__ directly to avoid infinite __setattr__ loop
        if items is None:
            items = dict()
        if comment is None:
            comment = ''
        self.__dict__['_items'] = items
        self.__dict__['_comment'] = comment

    def __contains__(self, item):
        """Checks items by name"""
        return item in self._items

    def __iter__(self):
        """Yields tuples of (item_name, item)"""
        for val in self._items.items():
            yield val

    def __eq__(self, other):
        return self._items == other._items and self._comment == other._comment

    def __getattr__(self, attr):
        """Returns an item by the syntax container.item.

        If the item is a ConfigItem instance, return the item value instead.
        This allows getting values directly by the syntax section.item.
        """
        try:
            item = self._items[attr]
        except KeyError:
            raise AttributeError(f"no such item or section: '{attr}'")
        return item.value if isinstance(item, ConfigItem) else item

    def __getitem__(self, item):
        """Returns an item"""
        return self._items[item]

    def __setattr__(self, attr, value):
        """Set attribute"""
        if isinstance(value, ConfigItem) or isinstance(value, ConfigContainer):
            # replace an existing section/item
            self.__dict__['_items'][attr] = value
        elif attr == '_comment':
            self.__dict__['_comment'] = value
        elif attr in self._items:
            # update value of existing item (syntax sec.item = value)
            self.__dict__['_items'][attr].value = value
        else:
            # implicitly create a new ConfigItem (syntax sec.item = value)
            self.__dict__['_items'][attr] = ConfigItem(name=attr, value=value)

    def __repr__(self):
        s = '<ConfigContainer |'
        items = [name for name, it in self._items.items() if isinstance(it, ConfigItem)]
        if items:
            s += ' items: '
            s += ', '.join(f"'{key}'" for key in items)
        sections = [
            name for name, it in self._items.items() if isinstance(it, ConfigContainer)
        ]
        if sections:
            if items:
                s += ','
            s += ' sections: '
            s += ', '.join(f"'{key}'" for key in sections)
        s += '>'
        return s


def parse_config(fname, encoding=None):
    """Parse a configuration file.

    Parameters:
    -----------
    fname : str | Path
        The filename.
    encoding : str
        The encoding to use. By default, open() uses the preferred encoding of
        the locale. On most Windows, this is still cp1252 instead of utf-8. If
        your configuration files are in utf-8 (as they probably will be), you
        need to specify encoding='utf-8' to correctly read extended characters.

    Returns:
    -------
    ConfigContainer
        The config object.
    """
    if encoding is None and sys.platform == 'win32':
        logger.warning(
            "On Windows, you need to explicitly specify encoding='utf-8' "
            "if your config file is encoded with UTF-8."
        )
    with open(fname, 'r', encoding=encoding) as f:
        lines = f.read().splitlines()
    return _parse_config_lines(lines)


def _parse_config_lines(lines):
    """Parse INI file lines into a ConfigContainer instance.

    Supports:
        -multiline variable definitions
        -multiple comment lines per item/section
    Does not support:
        -inline comments (would be too confusing with multiline defs)
    """
    current_section = None
    current_item_name = None
    comment_lines = list()  # comments for current variable
    current_def_lines = list()  # definition lines for current variable
    config = ConfigContainer()  # the 'root container'
    # mapping of section -> section level; 0 is the root, 1 is a section, 2 is a
    # subsection, etc.
    sections = [(config, 0)]

    # loop through the lines
    # every line is either: comment, section header, variable definition,
    # continuation of variable definition, or whitespace
    for lnum, li in enumerate(lines, 1):

        if (sec_def := _parse_section_header(li)) is not None:
            if current_item_name:  # did not finish previous definition
                raise ValueError(f'could not evaluate definition at line {lnum}')
            secname, sec_level = sec_def
            comment = '\n'.join(comment_lines)
            current_section = ConfigContainer(comment=comment)
            sections.append((current_section, sec_level))
            parents = [sec for sec, level in sections if level == sec_level - 1]
            if not parents:
                raise ValueError(f'subsection outside a parent section at line {lnum}')
            else:
                latest_parent = parents[-1]
            setattr(latest_parent, secname, current_section)
            comment_lines = list()

        elif _simple_match(RE_COMMENT, li):
            if current_item_name:
                raise ValueError(f'could not evaluate definition at line {lnum}')
            m = re.match(RE_COMMENT, li)
            cmnt = m.group(1)
            comment_lines.append(cmnt)

        elif _simple_match(RE_WHITESPACE, li):
            if current_item_name:
                raise ValueError(f'could not evaluate definition at line {lnum}')

        # new item definition
        elif (item_def := _parse_item_def(li)) is not None:
            item_name, val = item_def
            if current_item_name:
                raise ValueError(f'could not evaluate definition at line {lnum}')
            elif not current_section:
                raise ValueError(f'item definition outside of a section on line {lnum}')
            elif item_name in current_section:
                raise ValueError(f'duplicate definition on line {lnum}')
            try:
                val_eval = ast.literal_eval(val)
                # if eval is successful, record the variable
                comment = '\n'.join(comment_lines)
                item = ConfigItem(comment=comment, name=item_name, value=val_eval)
                setattr(current_section, item_name, item)
                comment_lines = list()
                current_def_lines = list()
                current_item_name = None
            except (ValueError, SyntaxError):  # eval failed, continued def?
                current_item_name = item_name
                current_def_lines.append(val)
                continue

        else:  # if none of the above, must be a continuation or syntax error
            if current_item_name:
                current_def_lines.append(li.strip())
            else:
                raise ValueError(f'syntax error at line {lnum}: {li}')
            # try to finish the def
            try:
                val_new = ''.join(current_def_lines)
                val_eval = ast.literal_eval(val_new)
                comment = ' '.join(comment_lines)
                item = ConfigItem(
                    comment=comment, name=current_item_name, value=val_eval
                )
                setattr(current_section, current_item_name, item)
                comment_lines = list()
                current_def_lines = list()
                current_item_name = None
            except (ValueError, SyntaxError):  # cannot finish def (yet)
                continue

    if current_item_name:  # we got to the end, but did not finish a definition
        raise ValueError(f'could not evaluate definition at line {lnum}')

    return config


def _traverse(container):
    """Recursively traverse a ConfigContainer.

    Yields (attr, item) tuples, where attr is the fully qualified attribute name
    (e.g. section.subsection.item) and item is the item.
    """
    for attr, item in container:
        yield attr, item
        if isinstance(item, ConfigContainer):
            yield from (
                (f'{attr}.{subname}', subitem) for subname, subitem in _traverse(item)
            )


def _get_nested_attr(cfg, attr_list):
    """Get an item by from a ConfigContainer using a nested attribute"""
    attr_list = attr_list.copy()  # don't mutate the argument
    attr0 = cfg[attr_list.pop(0)]
    # recurse until the final item in the attribute chain is reached
    return _get_nested_attr(attr0, attr_list) if attr_list else attr0


def update_config(
    cfg_orig,
    cfg_new,
    create_new_sections=True,
    create_new_items=True,
    update_comments=False,
):
    """Update existing Config instance from another.

    Parameters
    ----------
    cfg_orig : ConfigContainer
        The original config (to be updated).
    cfg_new : ConfigContainer
        The config that contains the updated data.
    create_new_sections : bool
        Whether to allow creation of config sections that don't exist in the
        original config. 
    create_new_items : bool | list
        Whether to create config items that don't exist in the original config.
        If True, new items may be created under any section. If list, must be a
        list of names for the sections where creating new items is allowed,
        e.g. ['section1.subsection1'].
    update_comments : bool
        If True, comments will be updated too.
    """
    for name, item in _traverse(cfg_new):
        name_list = name.split('.')
        item_name = name_list[-1]
        # get the parent section for this item in the orig config
        try:
            if parent_name := name_list[:-1]:
                parent = _get_nested_attr(cfg_orig, parent_name)
            else:
                parent = cfg_orig
        except KeyError:
            logger.warning(f'There is no parent section for {name}, so it was discarded.'
                            'You need to enable creation of new sections to include it.')
            continue
        try:
            item_orig = _get_nested_attr(cfg_orig, name_list)
            if update_comments:
                item_orig._comment = item._comment
            # ConfigContainers don't need updating, except for the comments
            # their contents will be updated recursively
            if isinstance(item_orig, ConfigItem):
                setattr(parent, item_name, item)
        except KeyError:  # item does not exist in the original config
            if isinstance(item, ConfigContainer) and create_new_sections:
                sec = ConfigContainer(comment=item._comment)
                setattr(parent, item_name, sec)
            elif isinstance(item, ConfigItem):
                if (
                    create_new_items is True
                    or (isinstance(create_new_items, list)
                    and '.'.join(parent_name) in create_new_items)
                ):
                    setattr(parent, item_name, item)


def _dump_config(cfg):
    """Return a config instance as text. Yields lines"""
    for attr, item_or_section in _traverse(cfg):
        name = attr.split('.')[-1]
        if comment := item_or_section._comment:
            for comment_line in comment.split('\n'):
                yield f'# {comment_line}'
        if isinstance(item_or_section, ConfigContainer):
            level = attr.count('.') + 1
            opening, closing = '[' * level, ']' * level
            yield f'{opening}{name}{closing}'
        elif isinstance(item_or_section, ConfigItem):
            yield item_or_section.item_def


def dump_config(cfg):
    """Return a config instance as text.

    Parameters
    ----------
    cfg : ConfigContainer
        The configuration.

    Returns
    -------
    string
        The configuration in string format.

    This function should return a string that reproduces the configuration when
    fed to _parse_config(). It can be used to e.g. write the config back into a
    file.
    """
    return '\n'.join(_dump_config(cfg))
