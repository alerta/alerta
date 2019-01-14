
from pyparsing import (CaselessKeyword, Forward, Group, Literal, Optional,
                       ParseException, ParserElement, QuotedString, Regex,
                       Suppress, Word, infixNotation, opAssoc, printables)

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
        return '({} AND {})'.format(self.lhs, self.rhs)


class SearchOr(BinaryOperation):

    def __repr__(self):
        return '({} OR {})'.format(self.lhs, self.rhs)


class SearchNot(UnaryOperation):

    def __repr__(self):
        return 'NOT ({})'.format(self.operands)


class SearchTerm:

    def __init__(self, tokens):
        self.tokens = tokens

    def __repr__(self):
        # print([t for t in self.tokens.items()])
        if 'singleterm' in self.tokens:
            if self.tokens.fieldname == '_exists_':
                return '"attributes"::jsonb ? \'{}\''.format(self.tokens.singleterm)
            elif self.tokens.fieldname in ['correlate', 'service', 'tags']:
                return '\'{}\'=ANY("{}")'.format(self.tokens.singleterm, self.tokens.field[0])
            else:
                return '"{}" ILIKE \'%%{}%%\''.format(self.tokens.field[0], self.tokens.singleterm)
        if 'phrase' in self.tokens:
            if self.tokens.field[0] == '__default_field__':
                return '"{}" ~* \'\\y{}\\y\''.format('__default_field__', self.tokens.phrase)
            elif self.tokens.field[0] in ['correlate', 'service', 'tags']:
                return '\'{}\'=ANY("{}")'.format(self.tokens.term, self.tokens.field[0])
            else:
                return '"{}" ~* \'\\y{}\\y\''.format(self.tokens.field[0], self.tokens.phrase)
        if 'wildcard' in self.tokens:
            return '"{}" ~* \'\\y{}\\y\''.format(self.tokens.field[0], self.tokens.wildcard)
        if 'regex' in self.tokens:
            return '"{}" ~* \'{}\''.format(self.tokens.field[0], self.tokens.regex)
        if 'range' in self.tokens:
            if self.tokens.range[0].lowerbound == '*':
                lower_term = '1=1'
            else:
                lower_term = '"{}" {} \'{}\''.format(
                    self.tokens.field[0],
                    '>=' if 'inclusive' in self.tokens.range[0] else '>',
                    self.tokens.range[0].lowerbound
                )

            if self.tokens.range[2].upperbound == '*':
                upper_term = '1=1'
            else:
                upper_term = '"{}" {} \'{}\''.format(
                    self.tokens.field[0],
                    '<=' if 'inclusive' in self.tokens.range[2] else '<',
                    self.tokens.range[2].upperbound
                )
            return '({} AND {})'.format(lower_term, upper_term)
        if 'onesidedrange' in self.tokens:
            return '("{}" {} \'{}\')'.format(
                self.tokens.field[0],
                self.tokens.onesidedrange.op,
                self.tokens.onesidedrange.bound
            )
        if 'subquery' in self.tokens:
            return '{}'.format(self.tokens.subquery[0]).replace('__default_field__', self.tokens.field[0])

        raise ParseException('Search term did not match query syntax: %s' % self.tokens)


# BNF for Lucene query syntax
#
# Query ::= ( Clause )*
# Clause ::= ["+", "-"] [<TERM> ":"] (<TERM> | "(" Query ")" )


LBRACK, RBRACK, LBRACE, RBRACE, TILDE, CARAT = map(Literal, '[]{}~^')
LPAR, RPAR, COLON = map(Suppress, '():')
and_, or_, not_, to_ = map(CaselessKeyword, 'AND OR NOT TO'.split())
keyword = and_ | or_ | not_ | to_

query_expr = Forward()

required_modifier = Literal('+')('required')
prohibit_modifier = Literal('-')('prohibit')
special_characters = '=><(){}[]^"~*?:\\/'
valid_word = Word(printables, excludeChars=special_characters).setName('word')
valid_word.setParseAction(
    lambda t: t[0].replace('\\\\', chr(127)).replace('\\', '').replace(chr(127), '\\')
)

clause = Forward()
field_name = valid_word()('fieldname')
single_term = valid_word()('singleterm')
phrase = QuotedString('"', unquoteResults=True)('phrase')
wildcard = Regex('[a-z0-9]*[\?\*][a-z0-9]*')('wildcard')
wildcard.setParseAction(
    lambda t: t[0].replace('?', '.?').replace('*', '.*')
)
regex = QuotedString('/', unquoteResults=True)('regex')

_all = Literal('*')
lower_range = Group((LBRACK('inclusive') | LBRACE('exclusive')) + (valid_word | _all)('lowerbound'))
upper_range = Group((valid_word | _all)('upperbound') + (RBRACK('inclusive') | RBRACE('esclusive')))
_range = (lower_range + to_ + upper_range)('range')

GT = Literal('>')
GTE = Literal('>=')
LT = Literal('<')
LTE = Literal('<=')
one_sided_range = Group((GTE | GT | LTE | LT)('op') + valid_word('bound'))('onesidedrange')

term = (_range | one_sided_range | regex | wildcard | phrase | single_term)

clause << (Optional(field_name + COLON, default='__default_field__')('field') +
           (term('term') | Group(LPAR + query_expr + RPAR)('subquery')))

clause.addParseAction(SearchTerm)

query_expr << infixNotation(clause,
                            [
                                (required_modifier | prohibit_modifier, 1, opAssoc.RIGHT, SearchModifier),
                                ((not_ | '!').setParseAction(lambda: 'NOT'), 1, opAssoc.RIGHT, SearchNot),
                                ((and_ | '&&').setParseAction(lambda: 'AND'), 2, opAssoc.LEFT, SearchAnd),
                                (Optional(or_ | '||').setParseAction(lambda: 'OR'), 2, opAssoc.LEFT, SearchOr),
                            ])


class QueryParser:

    DEFAULT_FIELD = 'text'

    def parse(self, query, default_field=None):
        self.default_field = default_field or QueryParser.DEFAULT_FIELD

        return repr(query_expr.parseString(query)[0]).replace('__default_field__', self.default_field)
