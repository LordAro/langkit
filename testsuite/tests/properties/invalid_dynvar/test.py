from __future__ import absolute_import, division, print_function

from langkit.diagnostics import Diagnostics
from langkit.dsl import ASTNode, Field, LexicalEnvType
from langkit.expressions import DynamicVariable, Property, Self
from langkit.parsers import Grammar, Row, Tok

from os import path
from utils import emit_and_print_errors


Env = DynamicVariable('env', LexicalEnvType)


def run(expr):
    """
    Emit and print the errors we get for the below grammar for the given
    "expr" property expression.
    """

    Diagnostics.set_lang_source_dir(path.abspath(__file__))

    print('== {} =='.format(expr))

    class FooNode(ASTNode):
        pass

    class ExampleNode(FooNode):
        tok = Field()

        implicit_prop = Property(Self, dynamic_vars=[Env])

        prop = Property(expr, public=True)
        use_implicit_prop = Property(
            Env.bind(Self.node_env, Self.implicit_prop),
            public=True
        )

    grammar = Grammar('main_rule')
    grammar.add_rules(
        main_rule=Row(Tok('example', keep=True)) ^ ExampleNode,
    )
    emit_and_print_errors(grammar)
    Env.unfreeze()
    print('')


run(Env.get(Self.tok))
run(Self.implicit_prop)
run(Env.bind(Self.node_env, Env.get(Self.tok)))
run(Env.bind(Self.node_env, Self.implicit_prop))
print('Done')
