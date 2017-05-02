from __future__ import absolute_import, division, print_function

from collections import namedtuple

import gdb

from langkit.gdb.debug_info import DSLLocation, ExprDone, ExprStart, Scope


class BaseCommand(gdb.Command):
    """
    Factorize common code for our commands.
    """

    def __init__(self, context, basename, command_class,
                 completer_class=gdb.COMPLETE_NONE):
        super(BaseCommand, self).__init__(
            '{}{}'.format(context.prefix, basename),
            command_class, completer_class
        )
        self.context = context


class StateCommand(BaseCommand):
    """Display the state of the currently running property.

This command may be followed by a "/X" flag, where X is one or several of:

    * f: display the full image of values (no ellipsis);
    * s: to print the name of the Ada variables that hold DSL values.
"""

    def __init__(self, context):
        super(StateCommand, self).__init__(context, 'state', gdb.COMMAND_DATA)

    def invoke(self, arg, from_tty):
        printer = StatePrinter(self.context)

        if arg:
            if not arg.startswith('/'):
                print('Invalid argument')
                return

            for c in arg[1:]:
                if c == 'f':
                    printer.with_ellipsis = False
                elif c == 's':
                    printer.with_locs = True
                else:
                    print('Invalid flag: {}'.format(repr(c)))
                    return

        printer.run()


class StatePrinter(object):
    """
    Helper class to embed code to display the state of the currently running
    property.
    """

    ellipsis_limit = 50

    def __init__(self, context):
        self.context = context

        self.frame = gdb.selected_frame()
        self.state = self.context.decode_state(self.frame)

        self.with_ellipsis = True
        self.with_locs = False

    def run(self):
        if self.state is None:
            print('Selected frame is not in a property.')
            return

        print('Running {}'.format(self.state.property.name))
        print('from {}'.format(self.state.property.dsl_sloc))

        for scope_state in self.state.scopes:
            is_first = [True]

            def print_info(*args, **kwargs):
                if is_first[0]:
                    print('')
                    is_first[0] = False
                print(*args, **kwargs)

            for b in scope_state.bindings:
                print_info('{}{} = {}'.format(
                    b.dsl_name,
                    self.loc_image(b.gen_name),
                    self.value_image(b.gen_name)
                ))

            last_started = None
            for e in scope_state.expressions.values():
                if e.is_started:
                    last_started = e
                elif e.is_done:
                    print_info('{}{} -> {}'.format(
                        e.expr_repr,
                        self.loc_image(e.result_var),
                        self.value_image(e.result_var)
                    ))
            if last_started:
                print_info('Currently evaluating {}'.format(
                    last_started.expr_repr
                ))
                if last_started.dsl_sloc:
                    print_info('from {}'.format(last_started.dsl_sloc))

    def loc_image(self, var_name):
        """
        If `self.with_locs`, return the name of the Ada variable that holds the
        DSL value.

        :rtype: str
        """
        return ' ({})'.format(var_name) if self.with_locs else ''

    def value_image(self, var_name):
        """
        Return the image of the value contained in the `var_name` variable.

        :rtype: str
        """
        # Switching to lower-case is required since GDB ignores case
        # insentivity for Ada from the Python API.
        value = str(self.frame.read_var(var_name.lower()))
        if self.with_ellipsis and len(value) > self.ellipsis_limit:
            value = '{}...'.format(value[:self.ellipsis_limit])
        return value


class BreakCommand(BaseCommand):
    """Put a breakpoint on a property. One of the following forms is allowed:

    * A case-insensitive property qualified name; for instance::
          break MyNode.p_property

    * A DSL source location; for instance, in spec.py, line 128::
          break spec.py:128
"""

    def __init__(self, context):
        super(BreakCommand, self).__init__(context, 'break',
                                           gdb.COMMAND_BREAKPOINTS)

    def invoke(self, arg, from_tty):
        spec = arg.strip()

        if ':' in spec:
            self.break_on_dsl_sloc(spec)
        else:
            self.break_on_property(spec)

    def break_on_property(self, qualname):
        """
        Try to put a breakpoint on a property whose qualified name is
        `qualname`. Display a message for the user if that is not possible.
        """
        lower_prop = qualname.lower()
        if not lower_prop:
            print('Missing breakpoint specification')
            return

        for prop in self.context.debug_info.properties:
            if prop.name.lower() == lower_prop:
                break
        else:
            print('No such property: {}'.format(qualname))
            return

        scopes = prop.subscopes
        if not scopes:
            print('{} has no code'.format(prop.name))
            return

        # Break on the first line of the property's first inner scope so that
        # we skip the prologue (all variable declarations).
        gdb.Breakpoint('{}:{}'.format(
            self.context.debug_info.filename,
            scopes[0].line_range.first_line
        ))

    def break_on_dsl_sloc(self, dsl_sloc):
        """
        Try to put a breakpoint on code that maps to the given DSL source
        location. Display a message for the user if that is not possible.
        """
        dsl_sloc = DSLLocation.parse(dsl_sloc)

        Match = namedtuple('Match', 'prop dsl_sloc line_no')
        matches = []

        def process_scope(prop, scope):
            for e in scope.events:
                if isinstance(e, Scope):
                    process_scope(prop, e)
                elif (isinstance(e, ExprStart)
                      and e.dsl_sloc
                      and e.dsl_sloc.matches(dsl_sloc)):
                    matches.append(Match(prop, e.dsl_sloc, e.line_no))

        for prop in self.context.debug_info.properties:
            process_scope(prop, prop)

        if not matches:
            print('No match for {}'.format(dsl_sloc))
        elif len(matches) > 1:
            print('Multiple matches for {}:'.format(dsl_sloc))
            for m in matches:
                print('  In {}, {}'.format(m.prop.name, m.dsl_sloc))
        else:
            m, = matches
            gdb.Breakpoint('{}:{}'.format(self.context.debug_info.filename,
                                          m.line_no))


class OutCommand(BaseCommand):
    """Continue execution until the end of the evaluation of the current
sub-expression.
    """

    def __init__(self, context):
        super(OutCommand, self).__init__(context, 'out', gdb.COMMAND_RUNNING)

    def invoke(self, arg, from_tty):
        if arg:
            print('This command takes no argument')
            return

        # Look for the expression that is being evaluated currently
        state = self.context.decode_state()
        scope_state, current_expr = self.lookup_current_expr(state)
        if not current_expr:
            print('Not evaluating any expression currently')
            return

        # Look for the point in the generated library where its evaluation will
        # be done.
        until_line_no = None
        for e in scope_state.scope.events:
            if isinstance(e, ExprDone) and e.expr_id == current_expr.expr_id:
                until_line_no = e.line_no
        if until_line_no is None:
            print('ERROR: cannot find the end of evaluation for expression {}.'
                  ' Code generation may have a bug.'.format(current_expr))
            return

        # Now go there! When we land in the expected place, also be useful and
        # display the value we got.
        gdb.execute('until {}'.format(until_line_no))
        frame = gdb.selected_frame()
        new_state = self.context.decode_state(frame)
        new_expr = self.lookup_expr(new_state, current_expr.expr_id)

        # Do some sanity checks first...

        def error(msg):
            print('ERROR: {}: something went wrong...'.format(msg))

        if new_state.property != state.property:
            return error('we landed in another property')
        if new_expr is None:
            return error('cannot find back the same expression')
        if not new_expr.is_done:
            return error('the expression is not evaluated yet')

        print('{} evaluated to: {}'.format(
            current_expr.expr_repr, frame.read_var(new_expr.result_var.lower())
        ))

    def lookup_current_expr(self, state):
        """
        If `state` represents the current evaluation of an expression, return
        this expression and its scope state. Return (None, None) otherwise.

        :param State state: State to look into.
        :rtype: (None, None)|(langkit.gdb.state.ScopeState,
                              langkit.gdb.state.ExpressionEvaluation)
        """
        for scope_state in reversed(state.scopes):
            for e in reversed(scope_state.expressions.values()):
                if e.is_started:
                    return scope_state, e
        return (None, None)

    def lookup_expr(self, state, expr_id):
        """
        Look for the ExpressionEvaluation instance in `state` whose id is
        `expr_id`.

        :rtype: langkit.gdb.state.ExpressionEvaluation|None
        """
        for scope_state in state.scopes:
            for e in scope_state.expressions.values():
                if e.expr_id == expr_id:
                    return e
