import json

from pyparsing import (Forward, Group, Keyword, Literal, Optional,
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
        return '{{"$and": [{}, {}]}}'.format(self.lhs, self.rhs)


class SearchOr(BinaryOperation):

    def __repr__(self):
        if getattr(self.rhs, 'op', None) == 'NOT':
            return '{{"$and": [{}, {}]}}'.format(self.lhs, self.rhs)
        return '{{"$or": [{}, {}]}}'.format(self.lhs, self.rhs)


class SearchNot(UnaryOperation):

    def __repr__(self):
        # NOTE: Can't just $not the existing operands. See https://jira.mongodb.org/browse/SERVER-10708
        tokens = list(json.loads(str(self.operands)).items())
        field_name = tokens[0][0]
        self.operands = {'$not': tokens[0][1]}
        return '{{"{}": {}}}'.format(field_name, json.dumps(self.operands))


class SearchTerm:

    def __init__(self, tokens):
        self.tokens = tokens

    def __repr__(self):
        # print([t for t in self.tokens.items()])
        if 'singleterm' in self.tokens:
            tokens_fieldname = self.tokens.fieldname.replace('_.', 'attributes.')
            if self.tokens.fieldname == '_exists_':
                return '{{"attributes.{}": {{"$exists": true}}}}'.format(self.tokens.singleterm)
            else:
                if self.tokens.field[0] == '__default_field__':
                    return '{{"{}": {{"{}": "{}"}}}}'.format('__default_field__', '__default_operator__', self.tokens.singleterm)
                else:
                    return '{{"{}": {{"$regex": "{}"}}}}'.format(tokens_fieldname, self.tokens.singleterm)
        if 'phrase' in self.tokens:
            if self.tokens.field[0] == '__default_field__':
                return '{{"{}": {{"{}": "{}"}}}}'.format('__default_field__', '__default_operator__', self.tokens.phrase)
            else:
                return '{{"{}": {{"$regex": "{}"}}}}'.format(self.tokens.field[0], self.tokens.phrase)
        if 'wildcard' in self.tokens:
            return '{{"{}": {{"$regex": "\\\\b{}\\\\b"}}}}'.format(self.tokens.field[0], self.tokens.wildcard)
        if 'regex' in self.tokens:
            return '{{"{}": {{"$regex": "{}"}}}}'.format(self.tokens.field[0], self.tokens.regex)

        def range_term(field, operator, range):
            if field in ['duplicateCount', 'timeout']:
                range = int(range)
            else:
                range = '"{}"'.format(range)
            return '{{"{}": {{"{}": {}}}}}'.format(field, operator, range)

        if 'range' in self.tokens:
            if self.tokens.range[0].lowerbound == '*':
                lower_term = '{}'
            else:
                lower_term = range_term(
                    self.tokens.field[0],
                    '$gte' if 'inclusive' in self.tokens.range[0] else '$gt',
                    self.tokens.range[0].lowerbound
                )
            if self.tokens.range[2].upperbound == '*':
                upper_term = '{}'
            else:
                upper_term = range_term(
                    self.tokens.field[0],
                    '$lte' if 'inclusive' in self.tokens.range[2] else '$lt',
                    self.tokens.range[2].upperbound
                )
            return '{{"$and": [{}, {}]}}'.format(lower_term, upper_term)
        if 'onesidedrange' in self.tokens:
            return range_term(
                self.tokens.field[0],
                self.tokens.onesidedrange.op,
                self.tokens.onesidedrange.bound
            )
        if 'subquery' in self.tokens:
            tokens_field0 = self.tokens.field[0].replace('_.', 'attributes.')
            if tokens_field0 != '__default_field__':
                return '{}'.format(self.tokens.subquery[0])\
                    .replace('__default_field__', tokens_field0)\
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

AND = Keyword('AND') | Literal('&&')
OR = Keyword('OR') | Literal('||')
NOT = Keyword('NOT') | Literal('!')
TO = Keyword('TO')

query_expr = Forward()

required_modifier = Literal('+')('required')
prohibit_modifier = Literal('-')('prohibit')
special_characters = '=><(){}[]^"~*?:\\/&|'
valid_word = Word(printables, excludeChars=special_characters).setName('word')
valid_word.setParseAction(
    lambda t: t[0].replace('\\\\', chr(127)).replace('\\', '').replace(chr(127), '\\')
)

clause = Forward()
field_name = valid_word()('fieldname')
single_term = valid_word()('singleterm')
phrase = QuotedString('"', unquoteResults=True)('phrase')
wildcard = Regex(r'[a-z0-9]*[\?\*][a-z0-9]*')('wildcard')
wildcard.setParseAction(
    lambda t: t[0].replace('?', '.?').replace('*', '.*')
)
regex = QuotedString('/', unquoteResults=True)('regex')

_all = Literal('*')
lower_range = Group((LBRACK('inclusive') | LBRACE('exclusive')) + (valid_word | _all)('lowerbound'))
upper_range = Group((valid_word | _all)('upperbound') + (RBRACK('inclusive') | RBRACE('esclusive')))
_range = (lower_range + TO + upper_range)('range')

GT = Literal('>')
GTE = Literal('>=')
LT = Literal('<')
LTE = Literal('<=')

mongo_op = (GTE | GT | LTE | LT)
mongo_op.setParseAction(
    lambda t: t[0].replace('>=', '$gte').replace('>', '$gt').replace('<=', '$lte').replace('<', '$lt')
)
one_sided_range = Group(mongo_op('op') + valid_word('bound'))('onesidedrange')

term = (_range | one_sided_range | regex | wildcard | phrase | single_term)

clause << (Optional(field_name + COLON, default='__default_field__')('field')
           + (term('term') | Group(LPAR + query_expr + RPAR)('subquery')))

clause.addParseAction(SearchTerm)

query_expr << infixNotation(clause,
                            [
                                (required_modifier | prohibit_modifier, 1, opAssoc.RIGHT, SearchModifier),
                                (NOT.setParseAction(lambda: 'NOT'), 1, opAssoc.RIGHT, SearchNot),
                                (AND.setParseAction(lambda: 'AND'), 2, opAssoc.LEFT, SearchAnd),
                                (Optional(OR).setParseAction(lambda: 'OR'), 2, opAssoc.LEFT, SearchOr),
                            ])


class QueryParser:

    DEFAULT_FIELD = 'text'
    DEFAULT_OPERATOR = '$regex'

    def parse(self, query, default_field=None, default_operator=None):
        default_field = default_field or QueryParser.DEFAULT_FIELD
        default_operator = default_operator or QueryParser.DEFAULT_OPERATOR

        return repr(query_expr.parseString(query)[0])\
            .replace('__default_field__', default_field)\
            .replace('__default_operator__', default_operator)
