
from pyparsing import (CaselessKeyword, Combine, Forward, Group, Literal,
                       OneOrMore, Optional, ParseException, ParserElement,
                       QuotedString, Regex, Suppress, White, Word,
                       infixNotation, opAssoc, printables)

ParserElement.enablePackrat()


class UnaryOperation:
    """takes one operand,e.g. not"""

    def __init__(self, tokens):
        self.op, self.operands = tokens[0]


class BinaryOperation:
    """takes two or more operands, e.g. and, or"""

    def __init__(self, tokens):
        self.op = tokens[0][1]
        self.lhs = tokens[0][0]
        self.rhs = tokens[0][2]


class SearchModifier(UnaryOperation):

    def __repr__(self):
        return '{} {}'.format(self.op, self.operands)


class SearchAnd(BinaryOperation):

    def __repr__(self):
        return '{{ "$and": [{}, {}] }}'.format(self.lhs, self.rhs)


class SearchOr(BinaryOperation):

    def __repr__(self):
        return '{{ "$or": [{}, {}] }}'.format(self.lhs, self.rhs)


class SearchNot(UnaryOperation):

    def __repr__(self):
        return '{{ "$not": {} }}'.format(self.operands)


class SearchTerm:

    def __init__(self, tokens):
        self.tokens = tokens

    def __repr__(self):
        # print([t for t in self.tokens.items()])
        if 'singleterm' in self.tokens:
            if self.tokens.fieldname == '_exists_':
                return '{{ "attributes.{}": {{ "$exists": true }} }}'.format(self.tokens.term)
            else:
                if self.tokens.field[0] == '__default_field__':
                    return '{{ "{}": {{ "{}": "{}" }} }}'.format('__default_field__', '__default_operator__', self.tokens.term)
                else:
                    return '{{ "{}": {{ "$regex": "{}" }} }}'.format(self.tokens.field[0], self.tokens.term)
        if 'phrase' in self.tokens:
            if self.tokens.field[0] == '__default_field__':
                return '{{ "{}": {{ "{}": "\\\"{}\\\"" }} }}'.format('__default_field__', '__default_operator__', self.tokens.phrase)
            else:
                return '{{ "{}": "{}" }}'.format(self.tokens.field[0], self.tokens.phrase)
        if 'wildcard' in self.tokens:
            return '{{ "{}": {{ "$regex": "{}" }} }}'.format(self.tokens.field[0], self.tokens.wildcard)
        if 'regex' in self.tokens:
            return '{{ "{}": {{ "$regex": "{}" }} }}'.format(self.tokens.field[0], self.tokens.regex)
        if 'subquery' in self.tokens:
            if self.tokens.field[0] != '__default_field__':
                return '{}'.format(self.tokens.subquery[0])\
                    .replace('__default_field__', self.tokens.field[0])\
                    .replace('__default_operator__', '$regex')
            else:
                return '{}'.format(self.tokens.subquery[0])

        raise ParseException('Search term did not match query syntax: %s' % self.tokens)


# BNF for Lucene query syntax
#
# Query ::= ( Clause )*
# Clause ::= ["+", "-"] [<TERM> ":"] (<TERM> | "(" Query ")" )


LBRACK, RBRACK, LBRACE, RBRACE, TILDE, CARAT = map(Literal, '[]{}~^')
LPAR, RPAR, COLON = map(Suppress, '():')
and_, or_, not_, to_ = map(CaselessKeyword, 'AND OR NOT TO'.split())
keyword = and_ | or_ | not_ | to_

query = Forward()

required_modifier = Literal('+')('required')
prohibit_modifier = Literal('-')('prohibit')
valid_word = Word(printables, excludeChars='?*:"()').setName('word')
valid_word.setParseAction(
    lambda t: t[0].replace('\\\\', chr(127)).replace('\\', '').replace(chr(127), '\\')
)

clause = Forward()
field_name = valid_word()('fieldname')
single_term = valid_word()('singleterm')
phrase = QuotedString('"', unquoteResults=True)('phrase')
wildcard = Combine(OneOrMore(Regex('[a-z0-9]*[\?\*][a-z0-9]*') | White(' ', max=1) + ~White()))('wildcard')
wildcard.setParseAction(
    lambda t: t[0].replace('?', '.?').replace('*', '.*')
)
regex = QuotedString('/', unquoteResults=True)('regex')
term = (regex | wildcard | phrase | single_term)

clause << (Optional(field_name + COLON, default='__default_field__')('field') +
           (term('term') | Group(LPAR + query + RPAR)('subquery')))

clause.addParseAction(SearchTerm)

query << infixNotation(clause,
                       [
                           (required_modifier | prohibit_modifier, 1, opAssoc.RIGHT, SearchModifier),
                           ((not_ | '!').setParseAction(lambda: 'NOT'), 1, opAssoc.RIGHT, SearchNot),
                           ((and_ | '&&').setParseAction(lambda: 'AND'), 2, opAssoc.LEFT, SearchAnd),
                           (Optional(or_ | '||').setParseAction(lambda: 'OR'), 2, opAssoc.LEFT, SearchOr),
                       ])

DEFAULT_FIELD = 'text'
DEFAULT_OPERATOR = '$regex'


def query_parser(q):
    return repr(query.parseString(q)[0]).replace('__default_field__', DEFAULT_FIELD).replace('__default_operator__', DEFAULT_OPERATOR)
