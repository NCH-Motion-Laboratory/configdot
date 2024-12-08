# -*- coding: utf-8 -*-
"""
Utils for parsing INI files and handling config objects.

@author: Jussi (jnu@iki.fi)
"""
import ast
import re
import logging
import sys

from .configdot import ConfigContainer, ConfigItem

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

    Yields (name, item) tuples, where name is the fully qualified attribute name
    (e.g. section.subsection.item) and item is the item.
    """
    for name, item in container:
        yield name, item
        if isinstance(item, ConfigContainer):
            yield from (
                (f'{name}.{subname}', subitem) for subname, subitem in _traverse(item)
            )


def _get_attr_by_name(cfg, name_list):
    """Get an item by from a ConfigContainer using a fully qualified attribute name.

    name_list is e.g. ['section', 'subsection', 'item'] for section.subsection.item
    """
    name_list = name_list.copy()  # don't mutate the argument
    attr0 = cfg[name_list.pop(0)]
    # recurse until the final item in the attribute chain is reached
    return _get_attr_by_name(attr0, name_list) if name_list else attr0


def update_config(
    cfg_to_update,
    cfg_new,
    create_new_sections=True,
    create_new_items=True,
    update_comments=False,
):
    """Update existing Config instance from another.

    Parameters
    ----------
    cfg_to_update : ConfigContainer
        The original config (to be updated).
    cfg_new : ConfigContainer
        The config that contains the updated data.
    create_new_sections : bool
        Whether to allow creation of config sections that don't exist in the
        original config.
    create_new_items : bool | list
        Whether to create config items that don't exist in the original config.
        If True, new items may be created under any section. If a list, must be
        a list of names for the sections where creating new items is allowed,
        e.g. ['section1.subsection1'].
    update_comments : bool
        If True, comments will be updated too.
    """
    if not (isinstance(create_new_items, bool) or isinstance(create_new_items, list)):
        raise TypeError('invalid create_new_items argument (must be list or bool)')
    for name, item_new in _traverse(cfg_new):
        name_list = name.split('.')  # e.g. 'section1.subsection1.var'
        item_name = name_list[-1]  # e.g. 'var'
        # get the parent section for this item in the orig config
        try:
            if parent_name := name_list[:-1]:
                parent = _get_attr_by_name(cfg_to_update, parent_name)
            else:
                # if parent name is empty, we're at the root container
                parent = cfg_to_update
        except KeyError:
            # item orphaned, since new sections cannot be created
            logger.warning(
                f'There is no parent section for {name}, so it was discarded.'
                'You need to enable creation of new sections to include it.'
            )
            continue
        try:
            # try to find the item in the original config
            # if unsuccessful, this will raise a KeyError
            item_to_update = _get_attr_by_name(cfg_to_update, name_list)
            # ConfigContainers don't need updating, except for the comments;
            # their contents will be updated separately
            if isinstance(item_new, ConfigContainer):
                if update_comments:
                    item_to_update._comment = item_new._comment    
            else:
                comment = item_new._comment if update_comments else item_to_update._comment
                item_updated = ConfigItem(item_new.name, item_new.value, comment)
                setattr(parent, item_name, item_updated)
        except KeyError:
            # item does not exist in the original config
            if isinstance(item_new, ConfigContainer) and create_new_sections:
                # create new empty container; reusing the container from cfg_new
                # would also copy its items, which we may not want
                section = ConfigContainer(comment=item_new._comment)
                setattr(parent, item_name, section)
            elif isinstance(item_new, ConfigItem):
                if create_new_items is True or (
                    isinstance(create_new_items, list)
                    and '.'.join(parent_name) in create_new_items
                ):
                    item_new = ConfigItem(
                        name=item_name, value=item_new.value, comment=item_new._comment
                    )
                    setattr(parent, item_name, item_new)


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
    str
        The configuration in string format.

    This function should return a string that reproduces the configuration when
    fed to _parse_config(). It can be used to e.g. write the config back into a
    file.
    """
    return '\n'.join(_dump_config(cfg))
