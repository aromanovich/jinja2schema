python
from random import randint

y = [1, '2', 3, '4']
a = []
z = [lambda x: randint(0,9) if isinstance(x, int) else x for x in y]
# z = list(map(lambda x: x if isinstance(x, (str)) else a.append(x), y))
print(z)
print(a)
