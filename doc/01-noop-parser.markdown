The very first Rubik configuration does nothing. We use it to present basic layouts about how to use Rubik to describe a network stack, and We will extend it step by step in the following articles.

Rubik accepts a description of a network stack as configuration. A network stack is composed by several network parsing layers, and logical connections between them. Therefore, the simplest stack contains one no-op layer and no connections. Let's create the no-op layer first.

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

Rubik does not require to write the wrapper function, but this structure is helpful as we will show it later. `Connectionless` is the one of two kinds of protocol parser that Rubik supports, which Rubik does not track round-trip information from packets. The common protocols that belong to `Connectionless` include Ethernet and IP. After creating the parser, user may assign several properties to define the behaviors of it. The only mandatory property is `header`, and we will show the others later. After the assignment to `header`, our minimal layer is completed and is ready to be inserted into the stack. The syntax of `header` and `layout` will be also introduced later.

----

Create a file `stack.py` next to `layers.py` above:
```python
from rubik.lang import *
from layers import nothing_parser


stack = Stack()
stack.nothing = nothing_parser()
```

And that's it. Rubik reads stack configuration from global variable `stack`, and the first layer assigned to stack is treated as the entry layer. Now, it's time to generate our first protocol parser with Rubik:
```
$ make gen C=stack
$ make A=weaver_whitebox.template.c
```

Make sure to install libpcap and libpcre2 dev packages.