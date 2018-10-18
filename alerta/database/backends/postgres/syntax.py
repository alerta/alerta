
from pyparsing import (CaselessKeyword, Combine, Forward, Group, Literal,
                       OneOrMore, Optional, ParserElement, QuotedString, Regex,
                       Suppress, White, Word, printables, pyparsing_common)

ParserElement.enablePackrat()

COLON, LBRACK, RBRACK, LBRACE, RBRACE, TILDE, CARAT = map(Literal, ':[]{}~^')
LPAR, RPAR = map(Suppress, '()')
and_, or_, not_, to_ = map(CaselessKeyword, 'AND OR NOT TO'.split())
keyword = and_ | or_ | not_ | to_

expression = Forward()

valid_word = Word(printables, excludeChars='?*:"').setName('word')
valid_word.setParseAction(
    lambda t: t[0].replace('\\\\', chr(127)).replace('\\', '').replace(chr(127), '\\')
)

string = QuotedString('"', unquoteResults=False)

required_modifier = Literal('+')('required')
prohibit_modifier = Literal('-')('prohibit')
integer = Regex(r'\d+').setParseAction(lambda t: int(t[0]))
proximity_modifier = Group(TILDE + integer('proximity'))
number = pyparsing_common.fnumber()
fuzzy_modifier = TILDE + Optional(number, default=0.5)('fuzzy')

term = Forward()
field_name = valid_word().setName('fieldname')
incl_range_search = Group(LBRACK + term('lower') + to_ + term('upper') + RBRACK)
excl_range_search = Group(LBRACE + term('lower') + to_ + term('upper') + RBRACE)
range_search = incl_range_search('incl_range') | excl_range_search('excl_range')
boost = (CARAT + number('boost'))

string_expr = Group(string + proximity_modifier) | string
word_expr = Group(valid_word + fuzzy_modifier) | valid_word
wildcard_expr = Combine(OneOrMore(Regex('[a-z0-9]*[\?\*][a-z0-9]*') | White(' ', max=1) + ~White())).setName('wildcard')
regular_expr = QuotedString('/', unquoteResults=False).setName('regex')

term << (Optional(field_name('field') + COLON) +
         (regular_expr('regex') | wildcard_expr('wildcard') | word_expr('word') | string_expr('string') | range_search('range') | Group(LPAR + expression + RPAR)) +
         Optional(boost))
