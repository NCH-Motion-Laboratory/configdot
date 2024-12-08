# -*- coding: utf-8 -*-
"""

Test the config interface

@author: jussi (jnu@iki.fi)
"""

from pathlib import Path
import pytest
import logging
import re
import ast

from configdot import (
    parse_config,
    update_config,
    dump_config,
    ConfigContainer,
    ConfigItem,
)
from configdot.utils import (
    RE_COMMENT,
    RE_SECTION_HEADER,
    RE_ITEM_DEF,
    _parse_config_lines,
)


logger = logging.getLogger(__name__)


def _file_path(filename):
    return Path('testdata') / filename


def test_configcontainer():
    """Tests for the ConfigContainer class"""
    cc = ConfigContainer()
    # create ConfigItems implicitly
    cc.foo = 1
    assert cc.foo == 1
    assert 'foo' in cc
    assert isinstance(cc['foo'], ConfigItem)
    # modify a ConfigItem
    cc.foo = 2
    assert cc.foo == 2
    assert isinstance(cc['foo'], ConfigItem)
    ci = ConfigItem('bar', value=3, comment='test comment')
    # assign an explicitly created ConfigItem
    cc.bar = ci
    assert cc.bar == 3
    assert cc['bar']._comment == 'test comment'
    # in such an assigment, the attribute must match the item name
    with pytest.raises(ValueError):
        cc['baz'] = ci
    # create a subcontainer
    ccsub = ConfigContainer(comment='section comment')
    cc.sub = ccsub
    assert isinstance(cc.sub, ConfigContainer)
    assert cc.sub._comment == 'section comment'
    cc.sub.baz = 'new item'
    assert cc.sub.baz == 'new item'
    assert isinstance(cc.sub['baz'], ConfigItem)
    # replace a container with another container
    ccsub2 = ConfigContainer(comment='another section')
    cc.sub = ccsub2
    assert cc.sub._comment == 'another section'
    # implicitly replace the container with an item
    cc.sub = 1
    assert isinstance(cc['sub'], ConfigItem)
    assert cc.sub == 1


def test_configitem():
    """Tests for the ConfigItem class"""
    with pytest.raises(ValueError):
        ConfigItem(1)
    ci = ConfigItem('bar', 2)
    assert ci.name == 'bar'
    assert ci.value == 2
    assert ci.literal_value == '2'
    assert ci.item_def == 'bar = 2'
    # item with a dict value
    di = {1: None, 2: 2}
    ci = ConfigItem('bar', di)
    # extract the literal value and evaluate it
    dival = ast.literal_eval(ci.literal_value)
    assert dival == di


def test_re_comment():
    """Test comment regex on various comments"""
    cmt_string = 'this is a comment'
    for leading in ['', ' ', ' ' * 5]:
        for comment_sign in '#;':
            for ws1 in ['', ' ']:
                for trailing in [' ' * 5, ' ' * 3, '']:
                    cmt = leading + comment_sign + ws1 + cmt_string + trailing
                    assert re.match(RE_COMMENT, cmt)
                    # the regex group will include trailing whitespace
                    # so test group extraction without whitespace
                    cmt = leading + comment_sign + ws1 + cmt_string
                    m = re.match(RE_COMMENT, cmt)
                    assert m.group(1) == cmt_string


def test_re_item_def():
    """Test item definition regex"""
    dli = list()
    # various whitespace
    dli = ['a=1', 'a = 1', ' a = 1 ']
    for d in dli:
        m = re.match(RE_ITEM_DEF, d)
        assert m.group(1) == 'a'
        assert m.group(2) == '1'
    # definition of string with equals
    d = 'a = "b=1"'
    m = re.match(RE_ITEM_DEF, d)
    assert m.group(1) == 'a'
    assert m.group(2) == '"b=1"'
    # no equals
    d = 'abc foo'
    assert not re.match(RE_ITEM_DEF, d)
    # no identifier
    d = '=x'
    assert not re.match(RE_ITEM_DEF, d)
    # illegal chars in varname
    d = 'a&b = c'
    assert not re.match(RE_ITEM_DEF, d)


def test_re_section_header():
    sli = ['[foo]', ' [foo] ']
    for s in sli:
        assert re.match(RE_SECTION_HEADER, s)
    s = '[ foo]'
    assert not re.match(RE_SECTION_HEADER, s)
    s = '[some/invalid/chars]'
    assert not re.match(RE_SECTION_HEADER, s)
    s = '[nice_chars_only]'
    assert re.match(RE_SECTION_HEADER, s)
    s = '[nice-chars-only]'
    assert re.match(RE_SECTION_HEADER, s)
    s = '[äöäöäöäöä]'
    assert re.match(RE_SECTION_HEADER, s)


def test_config():
    """Test reading of valid config"""
    fn = _file_path('valid.cfg')
    cfg_ = parse_config(fn)
    assert 'section1' in cfg_
    assert 'section2' in cfg_
    secs = sorted(secname for (secname, sec) in cfg_)
    assert secs == ['section1', 'section2', 'section3']
    assert cfg_.section1.var1 == 1
    assert cfg_.section1.var2 == ['list', 'continues']
    assert cfg_.section1['var1']._comment == 'this is var1'
    assert cfg_.section2.mydict['c'] == 3
    assert 'subsection3' in cfg_.section3
    assert cfg_.section3.subsection3.baz == 1


def test_extended_chars():
    """Test unicode parsing"""
    fn = _file_path('extended_chars.cfg')
    cfg_ = parse_config(fn, encoding='utf-8')
    # section name with extended chars
    assert 'äöäööäö' in cfg_
    assert cfg_.äöäööäö.äööä == 'ääöäöä'


def test_config_update():
    fn = _file_path('valid.cfg')
    fn_new = _file_path('updates.cfg')
    cfg_orig = parse_config(fn)
    cfg_new = parse_config(fn_new)
    # test not updating comments
    update_config(cfg_orig, cfg_new, update_comments=False)
    assert cfg_orig.section1['var1']._comment == 'this is var1'
    assert cfg_orig.section1.var1 == 2
    assert 'section4' in cfg_orig
    assert 'newvar' in cfg_orig.section2
    assert cfg_orig.section1._comment == 'section1 comment'
    cfg_orig = parse_config(fn)
    # test updating comments
    update_config(cfg_orig, cfg_new, update_comments=True)
    assert cfg_orig.section1['var1']._comment == 'this is var1 updated'
    assert cfg_orig.section1.var1 == 2
    assert 'section4' in cfg_orig
    assert 'newvar' in cfg_orig.section2
    assert cfg_orig.section1._comment == 'section1 updated comment'
    assert cfg_orig.section4.subsection4._comment == 'subsection4 new comment'
    # test not creating new sections or items (but updating existing ones)
    cfg_orig = parse_config(fn)
    update_config(
        cfg_orig,
        cfg_new,
        create_new_sections=False,
        create_new_items=False,
        update_comments=False,
    )
    assert 'section4' not in cfg_orig
    assert 'newvar' not in cfg_orig.section2
    assert cfg_orig.section1.var1 == 2  # updates must still succeed
    # test limiting creation of new items
    cfg_orig = parse_config(fn)
    update_config(
        cfg_orig,
        cfg_new,
        create_new_sections=False,
        create_new_items=['section2'],
        update_comments=False,
    )
    assert 'newvar' in cfg_orig.section2
    assert cfg_orig.section2['newvar']._comment == 'whole new variable'
    assert cfg_orig.section2.newvar == ['a', 2, 3]
    # section3 was not supposed to be updated with new variables
    assert 'var4' not in cfg_orig.section3
    # however updates to existing variables must still succeed
    assert cfg_orig.section3.var3 == 4
    # test creation of new sections
    cfg_orig = parse_config(fn)
    update_config(
        cfg_orig,
        cfg_new,
        create_new_sections=True,
        create_new_items=True,
        update_comments=False,
    )
    assert 'newvar' in cfg_orig.section2
    assert 'section4' in cfg_orig
    assert 'subsection4' in cfg_orig.section4
    assert 'li' in cfg_orig.section4.subsection4
    # test creation of new sections but not items
    cfg_orig = parse_config(fn)
    update_config(
        cfg_orig,
        cfg_new,
        create_new_sections=True,
        create_new_items=False,
        update_comments=False,
    )
    assert 'var4' not in cfg_orig.section3
    assert 'section4' in cfg_orig
    assert 'subsection4' in cfg_orig.section4
    assert 'li' not in cfg_orig.section4.subsection4


def test_orphaned_def():
    """Test cfg with def outside section"""
    fn = _file_path('orphan.cfg')
    with pytest.raises(ValueError):
        parse_config(fn)


def test_invalid_def():
    """Test cfg with invalid def"""
    fn = _file_path('invalid.cfg')
    with pytest.raises(ValueError):
        parse_config(fn)


def test_invalid_def2():
    """Test cfg with invalid def"""
    fn = _file_path('invalid2.cfg')
    with pytest.raises(ValueError):
        parse_config(fn)


def test_def_last_line():
    """Test cfg with multiline def terminating on last line"""
    fn = _file_path('def_last_line.cfg')
    cfg = parse_config(fn)
    assert 'foo' in cfg.section2


def test_invalid_subsections():
    fn = _file_path('subsections_invalid.cfg')
    with pytest.raises(ValueError):
        parse_config(fn)


def test_valid_subsections():
    fn = _file_path('subsections_valid.cfg')
    cfg = parse_config(fn)
    assert 'section1' in cfg
    assert 'subsubsection1' in cfg.section1.subsection1
    assert cfg.section1.subsection1.subsubsection1.subsubsubsection1.var1 == 2
    assert cfg.section1.subsection1.subsubsection2.var1 == 3


def test_write_read_cycle():
    for fn in [_file_path('valid.cfg'), _file_path('updates.cfg')]:
        cfg_ = parse_config(fn)
        txt = dump_config(cfg_)
        txtlines = txt.split('\n')
        cfg_back = _parse_config_lines(txtlines)
        assert cfg_ == cfg_back
