In this article, we will read the Ethernet type field from packet. The first thing to do is defining Ethernet layout in `layers.py`:
```python
# append to layers.py

class ethernet_header(layout):
    addr1 = Bit(32)
    addr2 = Bit(32)
    addr3 = Bit(32)
    type_ = Bit(16)
```

The first three fields are placeholders for source and destination MAC address, which we do not care for now. Rubik only supports byte fields with power-of-two lengths, i.e., 1, 2, 4 and 8 bytes, and bit fields which align to byte boundary. Thus 48-bit MAC address cannot be presented by a single field. Next is Ethernet parser:
```python
def ethernet_parser():
    eth = Connectionless()
    eth.header = ethernet_header
    # to be cont.
```

Notice that `header` property is assigned to `ethernet_header` class itself but not its instance. The all-lower underscore variable naming style also implies it. In general, the subclasses of `layout` never construct. After creating header parser the header fields are accessible, for example (pseudo code):
```python
    eth.prep = If(eth.header.type_ == 0x0800) >> [[IP actions]] >> Else() >> ...
```

After assigning `ethernet_header` to `eth.header`, all fields in `ethernet_parser` become `eth.header`'s properties automatically. You may also reference the original `ethernet_header.type_` as long as there's no conflicts.

To keep things simple and make this Ethernet parser a bit more useful, this time we choose to create a user-defined callback event which prints Ethernet type to standard out. There are two places to create events: inside layer factory function and in the stack's configuration file. The event created in the former place is usually tightly bound to protocols' implementation, such as updating its parser's internal states, so we will create our printing event along with stack.

First, what we need is to create a layout to declare callback's name and the arguments' types of the callback:
```python
# stack.py
from rubik.lang import *
from layers import *


class print_ethernet_type(layout):  # callback name
    type_ = Bit(16)  # callback argument(s)


stack = Stack()
stack.eth = ethernet_parser()

```

Next, insert event into `event` property. Make sure to use `stack.eth` to reference the Ethernet parser layer after inserting it into stack:
```python
# name `print` is not important for now
stack.eth.event.print = If(1) >> (  # If(...) part is mandatory for event even it's literally true
    Assign(print_ethernet_type.type_, stack.eth.header.type_) +
    Call(print_ethernet_type)
)
```

The code above serves as a common template for user events: one assignment to `event` property, one guard for triggering the event, several `Assign` to every callback argument, and finally one `Call` to callback the function. After run `make gen C=stack`, some boilerplate code appears in `weaver_whitebox.template.c`. Part of it looks like this: (may change from time to time)
```C
typedef struct {
  WV_U16 _106;  // print_ethernet_header.type_
}__attribute__((packed)) H1;
WV_U8 print_ethernet_type(H1 *args, WV_Any *user_data) {
  return 0;
}
```

Detail about C API of Rubik will be introduced later. For now we could just read `args->_106` for type value hinted by comment. Copy the template to `weaver_whitebox.c`, add necessary headers and call `printf` in the callback, then it's time to run `make` for the final build.