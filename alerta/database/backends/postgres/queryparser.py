from pyparsing import (Forward, Group, Keyword, Literal, Optional,
                       ParseException, ParserElement, QuotedString, Regex,
                       Suppress, Word, infixNotation, opAssoc, printables)

ParserElement.enablePackrat()


def _next_param(params):
    name = f'_qp_{len(params)}'
    return name


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
        return f'{self.op} {self.operands}'

    def to_sql(self, params):
        return f'{self.op} {self.operands.to_sql(params)}'


class SearchAnd(BinaryOperation):

    def __repr__(self):
        return f'({self.lhs} AND {self.rhs})'

    def to_sql(self, params):
        return f'({self.lhs.to_sql(params)} AND {self.rhs.to_sql(params)})'


class SearchOr(BinaryOperation):

    def __repr__(self):
        if getattr(self.rhs, 'op', None) == 'NOT':
            return f'({self.lhs} AND {self.rhs})'
        return f'({self.lhs} OR {self.rhs})'

    def to_sql(self, params):
        if getattr(self.rhs, 'op', None) == 'NOT':
            return f'({self.lhs.to_sql(params)} AND {self.rhs.to_sql(params)})'
        return f'({self.lhs.to_sql(params)} OR {self.rhs.to_sql(params)})'


class SearchNot(UnaryOperation):

    def __repr__(self):
        return f'NOT ({self.operands})'

    def to_sql(self, params):
        return f'NOT ({self.operands.to_sql(params)})'


class SearchTerm:

    def __init__(self, tokens):
        self.tokens = tokens

    def __repr__(self):
        # print([t for t in self.tokens.items()])
        if 'singleterm' in self.tokens:
            if self.tokens.fieldname == '_exists_':
                return f'"attributes"::jsonb ? \'{self.tokens.singleterm}\''
            elif self.tokens.fieldname in ['correlate', 'service', 'tags']:
                return f'\'{self.tokens.singleterm}\'=ANY("{self.tokens.field[0]}")'
            elif self.tokens.attr:
                tokens_attr = self.tokens.attr.replace('_', 'attributes')
                return f'"{tokens_attr}"::jsonb ->>\'{self.tokens.fieldname}\' ILIKE \'%%{self.tokens.singleterm}%%\''
            else:
                return f'"{self.tokens.field[0]}" ILIKE \'%%{self.tokens.singleterm}%%\''
        if 'phrase' in self.tokens:
            if self.tokens.field[0] == '__default_field__':
                return f"\"__default_field__\" ~* '\\y{self.tokens.phrase}\\y'"
            elif self.tokens.field[0] in ['correlate', 'service', 'tags']:
                return f'\'{self.tokens.phrase}\'=ANY("{self.tokens.field[0]}")'
            elif self.tokens.attr:
                tokens_attr = self.tokens.attr.replace('_', 'attributes')
                return f'"{tokens_attr}"::jsonb ->>\'{self.tokens.fieldname}\' ~* \'\\y{self.tokens.phrase}\\y\''
            else:
                return f'"{self.tokens.field[0]}" ~* \'\\y{self.tokens.phrase}\\y\''
        if 'wildcard' in self.tokens:
            return f'"{self.tokens.field[0]}" ~* \'\\y{self.tokens.wildcard}\\y\''
        if 'regex' in self.tokens:
            return f'"{self.tokens.field[0]}" ~* \'{self.tokens.regex}\''
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
            return f'({lower_term} AND {upper_term})'
        if 'onesidedrange' in self.tokens:
            return '("{}" {} \'{}\')'.format(
                self.tokens.field[0],
                self.tokens.onesidedrange.op,
                self.tokens.onesidedrange.bound
            )
        if 'subquery' in self.tokens:
            if self.tokens.attr:
                tokens_attr = 'attributes' if self.tokens.attr == '_' else self.tokens.attr
                tokens_fieldname = f'"{tokens_attr}"::jsonb ->>\'{self.tokens.fieldname}\''
            else:
                tokens_fieldname = f'"{self.tokens.fieldname or self.tokens.field[0]}"'
            return f'{self.tokens.subquery[0]}'.replace('"__default_field__"', tokens_fieldname)

        raise ParseException(f'Search term did not match query syntax: {self.tokens}')

    def to_sql(self, params):
        if 'singleterm' in self.tokens:
            if self.tokens.fieldname == '_exists_':
                p = _next_param(params)
                params[p] = self.tokens.singleterm
                return f'"attributes"::jsonb ? %({p})s'
            elif self.tokens.fieldname in ['correlate', 'service', 'tags']:
                p = _next_param(params)
                params[p] = self.tokens.singleterm
                return f'%({p})s=ANY("{self.tokens.field[0]}")'
            elif self.tokens.attr:
                tokens_attr = self.tokens.attr.replace('_', 'attributes')
                p_key = _next_param(params)
                params[p_key] = self.tokens.fieldname
                p_val = _next_param(params)
                params[p_val] = f'%{self.tokens.singleterm}%'
                return f'"{tokens_attr}"::jsonb ->>%({p_key})s ILIKE %({p_val})s'
            else:
                p = _next_param(params)
                params[p] = f'%{self.tokens.singleterm}%'
                return f'"{self.tokens.field[0]}" ILIKE %({p})s'
        if 'phrase' in self.tokens:
            if self.tokens.field[0] == '__default_field__':
                p = _next_param(params)
                params[p] = f'\\y{self.tokens.phrase}\\y'
                return f'"__default_field__" ~* %({p})s'
            elif self.tokens.field[0] in ['correlate', 'service', 'tags']:
                p = _next_param(params)
                params[p] = self.tokens.phrase
                return f'%({p})s=ANY("{self.tokens.field[0]}")'
            elif self.tokens.attr:
                tokens_attr = self.tokens.attr.replace('_', 'attributes')
                p_key = _next_param(params)
                params[p_key] = self.tokens.fieldname
                p_val = _next_param(params)
                params[p_val] = f'\\y{self.tokens.phrase}\\y'
                return f'"{tokens_attr}"::jsonb ->>%({p_key})s ~* %({p_val})s'
            else:
                p = _next_param(params)
                params[p] = f'\\y{self.tokens.phrase}\\y'
                return f'"{self.tokens.field[0]}" ~* %({p})s'
        if 'wildcard' in self.tokens:
            p = _next_param(params)
            params[p] = f'\\y{self.tokens.wildcard}\\y'
            return f'"{self.tokens.field[0]}" ~* %({p})s'
        if 'regex' in self.tokens:
            p = _next_param(params)
            params[p] = self.tokens.regex
            return f'"{self.tokens.field[0]}" ~* %({p})s'
        if 'range' in self.tokens:
            if self.tokens.range[0].lowerbound == '*':
                lower_term = '1=1'
            else:
                p = _next_param(params)
                params[p] = self.tokens.range[0].lowerbound
                op = '>=' if 'inclusive' in self.tokens.range[0] else '>'
                lower_term = f'"{self.tokens.field[0]}" {op} %({p})s'

            if self.tokens.range[2].upperbound == '*':
                upper_term = '1=1'
            else:
                p = _next_param(params)
                params[p] = self.tokens.range[2].upperbound
                op = '<=' if 'inclusive' in self.tokens.range[2] else '<'
                upper_term = f'"{self.tokens.field[0]}" {op} %({p})s'
            return f'({lower_term} AND {upper_term})'
        if 'onesidedrange' in self.tokens:
            p = _next_param(params)
            params[p] = self.tokens.onesidedrange.bound
            return f'("{self.tokens.field[0]}" {self.tokens.onesidedrange.op} %({p})s)'
        if 'subquery' in self.tokens:
            subquery_sql = self.tokens.subquery[0].to_sql(params)
            if self.tokens.attr:
                tokens_attr = 'attributes' if self.tokens.attr == '_' else self.tokens.attr
                p = _next_param(params)
                params[p] = self.tokens.fieldname
                tokens_fieldname = f'"{tokens_attr}"::jsonb ->>%({p})s'
            else:
                tokens_fieldname = f'"{self.tokens.fieldname or self.tokens.field[0]}"'
            return subquery_sql.replace('"__default_field__"', tokens_fieldname)

        raise ParseException(f'Search term did not match query syntax: {self.tokens}')


# BNF for Lucene query syntax
#
# Query ::= ( Clause )*
# Clause ::= ["+", "-"] [<TERM> ":"] (<TERM> | "(" Query ")" )


LBRACK, RBRACK, LBRACE, RBRACE, TILDE, CARAT = map(Literal, '[]{}~^')
LPAR, RPAR, COLON, DOT = map(Suppress, '():.')

AND = Keyword('AND') | Literal('&&')
OR = Keyword('OR') | Literal('||')
NOT = Keyword('NOT') | Literal('!')
TO = Keyword('TO')

query_expr = Forward()

required_modifier = Literal('+')('required')
prohibit_modifier = Literal('-')('prohibit')
special_characters = '=><(){}[]^"~*?:\\/.&|'
valid_word = Word(printables, excludeChars=special_characters).setName('word')
valid_word.setParseAction(
    lambda t: t[0].replace('\\\\', chr(127)).replace('\\', '').replace(chr(127), '\\')
)

clause = Forward()
field_name = (Optional(valid_word()('attr') + DOT)) + valid_word()('fieldname')
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
one_sided_range = Group((GTE | GT | LTE | LT)('op') + valid_word('bound'))('onesidedrange')

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

    def parse(self, query, default_field=None):
        default_field = default_field or QueryParser.DEFAULT_FIELD
        params = {}
        parsed = query_expr.parseString(query)[0]
        sql = parsed.to_sql(params)
        return sql.replace('__default_field__', default_field), params
