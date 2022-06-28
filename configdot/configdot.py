# -*- coding: utf-8 -*-
"""
Parse INI files into nested config objects.


@author: Jussi (jnu@iki.fi)
"""
import pprint


class ConfigItem:
    """Holds data for a config item"""

    def __init__(self, name=None, value=None, comment=None):
        self._comment = '' if comment is None else comment
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
