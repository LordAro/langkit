"""
Test the handling of analysis units in the properties DSL.
"""

from langkit.dsl import ASTNode, AnalysisUnit, Field, Int, T, abstract
from langkit.expressions import (AbstractProperty, ExternalProperty, No,
                                 Property, Self, langkit_property)

from utils import emit_and_print_errors


class FooNode(ASTNode):
    # This property is private and only called by unused properties, so it is
    # unused itself.
    as_expr = Property(Self.cast(T.Expression))

    # This property is unused but the user asked explicitly to not warn
    @langkit_property(warn_on_unused=False)
    def as_expr_2():
        return Self.cast(T.Expression)


@abstract
class Expression(FooNode):
    # This property and all its children are private. Only Literal.result is
    # called by a public property, so all others are unused.
    result = AbstractProperty(type=Int)

    # This property is private, but is called from "referenced_units", so
    # "names" and all its overriding properties are used.
    names = AbstractProperty(type=T.Name.array)

    referenced_units = Property(Self.names.map(lambda n: n.designated_unit),
                                public=True)


class Literal(Expression):
    token_node = True

    # This one is private, but it is called by "evaluate" so it's not usused
    result = ExternalProperty(uses_entity_info=False, uses_envs=False)

    # See Expression.name
    names = Property(No(T.Name.array))

    evaluate = Property(Self.result, public=True)


class Name(Expression):
    token_node = True

    # This one is private and called transitively from a public property
    designated_unit = ExternalProperty(type=AnalysisUnit,
                                       uses_entity_info=False, uses_envs=False)

    result = Property(Self.designated_unit.root.cast(Expression).result)

    # See Expression.name
    names = Property(Self.singleton)


class Plus(Expression):
    left = Field()
    right = Field()

    result = Property(Self.left.result + Self.right.result)

    # See Expression.name
    names = Property(Self.left.names.concat(Self.right.names))


emit_and_print_errors(lkt_file='foo.lkt')
print('Done')
