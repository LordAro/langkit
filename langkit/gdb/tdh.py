from __future__ import absolute_import, division, print_function

import gdb


class TDH(object):
    """
    Helper to deal with tokens data handlers.
    """

    def __init__(self, value):
        self.value = value

    def _vector_item(self, vector, index):
        last = int(vector['size'])
        if index < 1 or last < index:
            raise gdb.error('Out of bounds index')

        array = vector['e'].dereference()
        return array[index]

    def get(self, token_no, trivia_no):
        """
        Retreive the token or trivia in this TDH corresponding to the given
        indices.

        :rtype: Token
        """
        return (self.trivia(token_no, trivia_no)
                if trivia_no else
                self.token(token_no))

    def token(self, token_no):
        """
        Retreive the token number "token_no" in this TDH.

        :rtype: Token
        """
        return Token(self, self._vector_item(self.value['tokens'], token_no),
                     token_no, 0)

    def trivia(self, token_no, trivia_no):
        """
        Retreive the trivia number "trivia" in this TDH.

        :rtype: Token
        """
        return Token(self,
                     self._vector_item(self.value['trivias'], trivia_no)['t'],
                     token_no, trivia_no)


class Token(object):
    """
    Helper to deal with tokens.
    """

    def __init__(self, tdh, value, token_no, trivia_no):
        self.tdh = tdh
        self.value = value
        self.token_no = token_no
        self.trivia_no = trivia_no

    @property
    def kind(self):
        return self.value['kind']

    @property
    def sloc_range(self):
        return SlocRange(self.value['sloc_range'])

    def __repr__(self):
        return '<Token {} {}/{} at {}>'.format(
            self.kind, self.token_no, self.trivia_no, self.sloc_range
        )


class Sloc(object):
    def __init__(self, line, column):
        self.line = line
        self.column = column

    def __repr__(self):
        return '{}:{}'.format(self.line, self.column)


class SlocRange(object):
    def __init__(self, value):
        self.start = Sloc(int(value['start_line']),
                          int(value['start_column']))
        self.end = Sloc(int(value['end_line']),
                        int(value['end_column']))

    def __repr__(self):
        return '{}-{}'.format(self.start, self.end)
