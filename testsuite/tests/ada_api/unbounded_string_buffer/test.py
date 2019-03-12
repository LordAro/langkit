"""
Test that the $.Analysis.Get_From_Buffer overload that reads an unbounded
string works as expected.
"""

from __future__ import absolute_import, division, print_function

from langkit.dsl import ASTNode
from langkit.parsers import Grammar

from utils import build_and_run


class FooNode(ASTNode):
    pass


class Example(FooNode):
    token_node = True


g = Grammar('main_rule')
g.add_rules(main_rule=Example('example'))
build_and_run(g, ada_main=['main.adb'])
print('Done')