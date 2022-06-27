# -*- coding: utf-8 -*-
"""

Test the config interface

@author: jussi (jnu@iki.fi)
"""

from pathlib import Path
import pytest
import logging
import re

from configdot.configdot import (
    parse_config,
    update_config,
    dump_config,
    RE_COMMENT,
    RE_SECTION_HEADER,
    RE_ITEM_DEF,
    _parse_config,
)


logger = logging.getLogger(__name__)


def _file_path(filename):
    return Path('testdata') / filename


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


def test_config():
    """Test reading of valid config"""
    fn = _file_path('valid.cfg')
    cfg_ = parse_config(fn)
    assert 'section1' in cfg_
    assert 'section2' in cfg_
    secs = sorted(secname for (secname, sec) in cfg_)
    assert secs == ['section1', 'section2']
    assert cfg_.section1.var1 == 1
    assert 'list' in cfg_.section1.var2
    assert cfg_.section1['var1']._comment == 'this is var1'
    assert cfg_.section2.mydict['c'] == 3


def test_config_update():
    fn = _file_path('valid.cfg')
    fn_new = _file_path('updates.cfg')
    cfg_new = parse_config(fn_new)
    cfg_ = parse_config(fn)
    update_config(cfg_, cfg_new, update_comments=False)
    assert 'section3' in cfg_
    assert 'newvar' in cfg_.section2
    assert cfg_.section1._comment == 'old section1 comment'
    cfg_ = parse_config(fn)
    update_config(cfg_, cfg_new, create_new_sections=False)
    assert 'section3' not in cfg_
    assert 'newvar' in cfg_.section2
    cfg_ = parse_config(fn)
    update_config(cfg_, cfg_new, create_new_sections=True, create_new_items=False)
    assert 'section3' in cfg_
    assert 'newvar' not in cfg_.section2
    cfg_ = parse_config(fn)
    update_config(cfg_, cfg_new, update_comments=True)
    assert cfg_.section1._comment == 'updated section1 comment'
    cfg_ = parse_config(fn)
    update_config(cfg_, cfg_new, create_new_items=['section2'])
    assert 'newvar' in cfg_.section2
    cfg_ = parse_config(fn)
    update_config(cfg_, cfg_new, create_new_items=['section1'])
    assert 'newvar' not in cfg_.section2


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


def test_subsections():
    fn = _file_path('subsections_valid.cfg')
    cfg = parse_config(fn)
    assert 'subsection1' in cfg.section1
    assert 'subsection2' in cfg.section1
    assert 'var1' in cfg.section1.subsection1
    assert 'var2' in cfg.section1.subsection2
    assert cfg.section1.subsection1.var1 == 1


def test_invalid_subsections():
    fn = _file_path('subsections_invalid.cfg')
    with pytest.raises(ValueError):
        parse_config(fn)


def test_write_read_cycle():
    fn = _file_path('valid.cfg')
    cfg_ = parse_config(fn)
    txt = dump_config(cfg_)
    txtlines = txt.split('\n')
    cfg_back = _parse_config(txtlines)
    assert cfg_ == cfg_back



