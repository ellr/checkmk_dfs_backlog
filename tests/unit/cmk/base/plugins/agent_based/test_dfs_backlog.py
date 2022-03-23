#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from typing import Tuple, List

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Metric
from cmk.base.plugins.agent_based.dfs_backlog import (
    parse_dfs_backlog,
    check_dfs_backlog,
    DfsReplication,
)


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        (
            [],
            []
        ),
        (
            [
                ['FOO_DATA ( from foohost)', '0'],
            ],
            [DfsReplication(descr="FOO_DATA from foohost", backlog_count=0)]
        ),
        (
            [
                ['FOO_DATA ( from foohost)', 'NULL'],
            ],
            [DfsReplication(descr="FOO_DATA from foohost", backlog_count=0, disabled=True)]
        ),
        (
            [
                ['FOO_DATA ( from foohost)', '10'],
                ['FOO_DATA ( to foohost)', '5923'],
                ['Archive ( from foohost)', '00'],
                ['Archive ( to foohost)', '875'],
            ],
            [
                DfsReplication(descr="FOO_DATA from foohost", backlog_count=10),
                DfsReplication(descr="FOO_DATA to foohost", backlog_count=5923),
                DfsReplication(descr="Archive from foohost", backlog_count=0),
                DfsReplication(descr="Archive to foohost", backlog_count=875),
            ]
        ),
    ],
)
def test_parse_dfs_backlog(string_table: List[List[str]], expected_section: List[DfsReplication]) -> None:
    assert parse_dfs_backlog(string_table) == expected_section


TEST_SECTION_DATA: List[DfsReplication] = [
    DfsReplication(descr="FOO_DATA from foohost", backlog_count=10),
    DfsReplication(descr="FOO_DATA to foohost", backlog_count=5923),
    DfsReplication(descr="Archive from foohost", backlog_count=0),
    DfsReplication(descr="Archive to foohost", backlog_count=875),
    DfsReplication(descr="WannaCryExampleData from foohost", backlog_count=0, disabled=True)
]


@pytest.mark.parametrize(
    "item, section, expected_check_result",
    [
        (
            "IBM_UTILS from samba_on_power9",
            [],
            (
                Result(state=State.UNKNOWN, summary='item not found'),
            ),
        ),
        (
            "FOO_DATA from foohost",
            TEST_SECTION_DATA,
            (
                Result(state=State.OK, summary='Backlog count: 10'),
                Metric('count', 10.0, levels=(300.0, 1000.0)),
            ),
        ),
        (
            "FOO_DATA to foohost",
            TEST_SECTION_DATA,
            (
                Result(state=State.CRIT, summary='Backlog count: 5923'),
                Metric('count', 5923.0, levels=(300.0, 1000.0)),
            ),
        ),
        (
            "Archive from foohost",
            TEST_SECTION_DATA,
            (
                Result(state=State.OK, summary='Backlog count: 0'),
                Metric('count', 0.0, levels=(300.0, 1000.0)),
            ),
        ),
        (
            "Archive to foohost",
            TEST_SECTION_DATA,
            (
                Result(state=State.WARN, summary='Backlog count: 875'),
                Metric('count', 875.0, levels=(300.0, 1000.0)),
            ),
        ),
        (
            "WannaCryExampleData from foohost",
            TEST_SECTION_DATA,
            (
                Result(state=State.OK, summary='DFSR Disabled'),
            ),
        ),
    ],
)
def test_check_dfs_backlog(item: str, section: List[DfsReplication], expected_check_result: Tuple) -> None:
    assert tuple(check_dfs_backlog(item, section)) == expected_check_result


@pytest.mark.parametrize(
    "item, section",
    [
        (
            "TEST_REPLICA from win_nt_host",
            [
                DfsReplication(descr="TEST_REPLICA from win_nt_host", backlog_count=-7)
            ]
        ),
    ],
)
def test_invalid_check_dfs_backlog(item: str, section: List[DfsReplication]) -> None:
    with pytest.raises(ValueError) as exec_info:
        tuple(check_dfs_backlog(item, section))

    assert isinstance(exec_info.type(), ValueError)
    assert str(exec_info.value) == 'Backlog count is negative! count=-7'
