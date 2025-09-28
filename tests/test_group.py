import configparser

import pytest

from gitosis import group


def test_no_empty_config():
    cfg = configparser.RawConfigParser()
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_no_empty_group():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group hackers")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_no_not_listed():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group hackers")
    cfg.set("group hackers", "members", "wsmith")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_yes_simple():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group hackers")
    cfg.set("group hackers", "members", "jdoe")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "hackers"
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_yes_leading():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group hackers")
    cfg.set("group hackers", "members", "jdoe wsmith")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "hackers"
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_yes_trailing():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group hackers")
    cfg.set("group hackers", "members", "wsmith jdoe")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "hackers"
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_yes_middle():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group hackers")
    cfg.set("group hackers", "members", "wsmith jdoe danny")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "hackers"
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_yes_recurse_one():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group hackers")
    cfg.set("group hackers", "members", "wsmith @smackers")
    cfg.add_section("group smackers")
    cfg.set("group smackers", "members", "danny jdoe")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "smackers"
    assert next(gen) == "hackers"
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_yes_recurse_one_ordering():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group smackers")
    cfg.set("group smackers", "members", "danny jdoe")
    cfg.add_section("group hackers")
    cfg.set("group hackers", "members", "wsmith @smackers")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "smackers"
    assert next(gen) == "hackers"
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_yes_recurse_three():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group hackers")
    cfg.set("group hackers", "members", "wsmith @smackers")
    cfg.add_section("group smackers")
    cfg.set("group smackers", "members", "danny @snackers")
    cfg.add_section("group snackers")
    cfg.set("group snackers", "members", "@whackers foo")
    cfg.add_section("group whackers")
    cfg.set("group whackers", "members", "jdoe")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "whackers"
    assert next(gen) == "snackers"
    assert next(gen) == "smackers"
    assert next(gen) == "hackers"
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_yes_recurse_junk():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group hackers")
    cfg.set("group hackers", "members", "@notexist @smackers")
    cfg.add_section("group smackers")
    cfg.set("group smackers", "members", "jdoe")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "smackers"
    assert next(gen) == "hackers"
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_yes_recurse_loop():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group hackers")
    cfg.set("group hackers", "members", "@smackers")
    cfg.add_section("group smackers")
    cfg.set("group smackers", "members", "@hackers jdoe")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "smackers"
    assert next(gen) == "hackers"
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)


def test_no_recurse_loop():
    cfg = configparser.RawConfigParser()
    cfg.add_section("group hackers")
    cfg.set("group hackers", "members", "@smackers")
    cfg.add_section("group smackers")
    cfg.set("group smackers", "members", "@hackers")
    gen = group.get_membership(config=cfg, user="jdoe")
    assert next(gen) == "all"
    with pytest.raises(StopIteration):
        next(gen)
