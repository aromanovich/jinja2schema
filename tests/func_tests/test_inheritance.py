# coding: utf-8
import pytest
from jinja2 import PackageLoader, Environment

from jinja2schema.config import Config
from jinja2schema.core import infer
from jinja2schema.model import Dictionary, Scalar


@pytest.fixture
def env():
    loader = PackageLoader('tests', 'templates')
    return Environment(loader=loader)


@pytest.fixture
def config():
    return Config(PACKAGE_NAME='tests')


def test_include_1(env, config):
    struct = infer(env.loader.get_source(env, 'inner_include_1.html')[0], config)
    expected_struct = Dictionary({
        'var': Dictionary(
            {
                'x': Scalar(label='x', linenos=[1]),
                'y': Scalar(label='y', linenos=[1]),
            },
            label='var',
            linenos=[1]
        ),
        'more': Scalar(label='more', linenos=[2]),
    })
    assert struct == expected_struct


def test_include_override_1(env, config):
    struct = infer(env.loader.get_source(env, 'inner_include_override_1.html')[0], config)
    expected_struct = Dictionary({
        'default_name': Scalar(label='default_name', linenos=[2]),
        'name': Scalar(label='name', linenos=[3]),
    })
    assert struct == expected_struct


def test_extend_1(env, config):
    struct = infer(env.loader.get_source(env, 'inner_extend.html')[0], config)
    expected_struct = Dictionary({
        'var': Dictionary(
            {'a': Scalar(label='a', linenos=[1])},
            label='var',
            linenos=[1]
        ),
        'some': Scalar(label='some', linenos=[2]),
        'extended': Scalar(label='extended', linenos=[2]),
    })
    assert struct == expected_struct


def test_include_extend_1(env, config):
    struct = infer(env.loader.get_source(env, 'include_extend.html')[0], config)
    expected_struct = Dictionary({
        'var': Dictionary(
            {
                'x': Scalar(label='x', linenos=[1]),
                'y': Scalar(label='y', linenos=[1]),
                'a': Scalar(label='a', linenos=[1]),
            },
            label='var',
            linenos=[1]
        ),
        'also': Scalar(label='also', linenos=[3]),
        'extended': Scalar(label='extended', linenos=[2]),
    })
    assert struct == expected_struct


def test_extend_with_block_override_1(env, config):
    struct = infer(env.loader.get_source(env, 'inner_extend_override_1.html')[0], config)
    expected_struct = Dictionary({
        'name': Scalar(label='name', linenos=[3]),
    })
    assert struct == expected_struct


def test_extend_with_block_override_2(env, config):
    struct = infer(env.loader.get_source(env, 'inner_extend_override_2.html')[0], config)
    expected_struct = Dictionary({
        'name': Scalar(label='name', linenos=[3]),
        'location': Scalar(label='location', linenos=[6]),
        'default_mood': Scalar(label='default_mood', linenos=[8]),
    })
    assert struct == expected_struct


def test_extend_with_block_override_3(env, config):
    struct = infer(env.loader.get_source(env, 'inner_extend_override_3.html')[0], config)
    expected_struct = Dictionary({
        'location': Scalar(label='location', linenos=[6]),
        'mood': Scalar(label='mood', linenos=[9]),
        'name': Scalar(label='name', linenos=[3]),
    })
    assert struct == expected_struct


def test_extend_with_block_override_4(env, config):
    struct = infer(env.loader.get_source(env, 'inner_extend_override_4.html')[0], config)
    expected_struct = Dictionary({
        'noblock': Scalar(label='noblock', linenos=[1]),
        'brake': Scalar(label='brake', linenos=[3]),
        'location': Scalar(label='location', linenos=[6]),
        'mood': Scalar(label='mood', linenos=[9]),
        'name': Scalar(label='name', linenos=[3]),
    })
    assert struct == expected_struct
