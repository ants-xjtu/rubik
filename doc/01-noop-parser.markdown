The very first Rubik configure does exactly nothing. I use it to present basic layout of configure, and I will extend it step by step in the following articles.

Rubik accepts description of a network stack as configure. A network stack is composed by several network parsing layers, and logical connections among them. So the simplest stack contains one no-op layer and no connection. Let's create the no-op layer first.

Create a file `layers.py` in project root, next to `Makefile`:
```python
from rubik.lang import *


class blank_header(layout):
    pass


def nothing_parser():
    nothing = Connectionless()
    nothing.header = blank_header
    return nothing
```

Rubik does not force to write the wrapper function, but as shown later this structure is helpful. `Connectionless` is the one of two kinds of protocol parser that Rubik supports, which Rubik does not track round-trip information from packets. The common protocols that belongs to `Connectionless` includes Ethernet and IP. After creating the praser, user may assign to several properties to define the behaviour of it. The only mandatory property is `header`, and I will show the others later. After assignment ot `header`, our minimal layer is completed and is ready to be inserted into the stack. The syntax of `header` and `layout` will be also introduced later.

----

Create a file `stack.py` next to `layers.py` above:
```python
from rubik.lang import *
from layers import nothing_parser


stack = Stack()
stack.nothing = nothing_parser()
```

And that's it. Rubik read stack configure from global variable `stack`, and the first layer assigned to stack is treated as entry layer. Now it's time to generate our first protocol parser with Rubik:
```
$ make gen C=stack
$ make A=weaver_whitebox.template.c
```

Make sure to install libpcap and libpcre2 dev packages.