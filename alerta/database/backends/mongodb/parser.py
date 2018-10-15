

from pyparsing import Optional, ParseException, infixNotation, opAssoc

from alerta.database.backends.mongodb.syntax import (and_, expression, not_,
                                                     or_, prohibit_modifier,
                                                     required_modifier, term)


class UnaryOperation:
    """takes one operand,e.g. not"""

    def __init__(self, tokens):
        self.op, self.operands = tokens[0]


class BinaryOperation:
    """takes two or more operands, e.g. and, or"""

    def __init__(self, tokens):
        self.op = tokens[0][1]
        self.operands = tokens[0][0::2]


class SearchAnd(BinaryOperation):

    def __repr__(self):
        return '{{ "$and": [{0}] }}'.format(','.join(str(oper) for oper in self.operands))


class SearchOr(BinaryOperation):

    def __repr__(self):
        return '{{ "$or": [{0}] }}'.format(','.join(str(oper) for oper in self.operands))


class SearchNot(UnaryOperation):

    def __repr__(self):
        return '{{ "$not": {0} }}'.format(self.operands)


class SearchTerm:

    def __init__(self, tokens):
        self.tokens = tokens
        if 'field' in self.tokens:
            self.term = self.tokens[2]
        else:
            self.term = self.tokens[0]

    def __repr__(self):
        if 'field' in self.tokens:
            if 'word' in self.tokens:
                if self.tokens.field == '_exists_':
                    return '{{ "attributes.{}": {{ "$exists": true }} }}'.format(self.term)
                else:
                    return '{{ "{}": {{ "$regex": "{}" }} }}'.format(self.tokens.field, self.tokens.word)
            if 'string' in self.tokens:
                return '{{ "{}": "{}" }}'.format(self.tokens.field, self.tokens.string.strip('"'))
            if 'wildcard' in self.tokens:
                wildcard = self.tokens.wildcard.replace('?', '.?').replace('*', '.*')
                return '{{ "{}": {{ "$regex": "{}" }} }}'.format(self.tokens.field, wildcard)
            if 'regex' in self.tokens:
                return '{{ "{}": {{ "$regex": "{}" }} }}'.format(self.tokens.field, self.tokens.regex.strip('/'))
        else:
            if 'word' in self.tokens:
                return '{{ "$text": {{ "$search": "{}" }} }}'.format(self.tokens.word)
            if 'string' in self.tokens:
                return '{{ "$text": {{ "$search": "{}" }} }}'.format(self.tokens.string.replace('"', '\\"'))
            if 'regex' in self.tokens:
                return '{{ "$text": {{ "$search": "{}" }} }}'.format(self.tokens.regex.strip('/'))
        raise ParseException('Search term did not match query syntax: %s' % self.tokens)


term.addParseAction(SearchTerm)


expression << infixNotation(term,
                            [
                                (required_modifier | prohibit_modifier, 1, opAssoc.RIGHT),
                                ((not_ | '!').setParseAction(lambda: 'NOT'), 1, opAssoc.RIGHT, SearchNot),
                                ((and_ | '&&').setParseAction(lambda: 'AND'), 2, opAssoc.LEFT, SearchAnd),
                                (Optional(or_ | '||').setParseAction(lambda: 'OR'), 2, opAssoc.LEFT, SearchOr),
                            ])
