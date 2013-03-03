from bunch import Bunch, bunchify, unbunchify
import json
import yaml

b = Bunch()

b = bunchify({'foo': 'bar', 'baz': ['qqr', 'abc'], 'ppp': {'a': 'b', 'c': 'd'}})

print b
print json.dumps(b)
print yaml.dump(b)
print unbunchify(b)