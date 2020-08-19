In this article I will show basic way to write highly customizable logic in Rubik. Normally it should go into user-defined events like example in previous article, but event has some limitations:
* event only triggers after everything else in the same layer (with exception)
* code in event cannot affect parsing logic

To address these problems, Rubik provides a property called `prep`, anything assigned to it will be executed before core stages, so it is suitable for preparation.

> The pipeline of a parsing layer consists following stages: header, instance, preparation, sequence, PSM, event. The detail will be introduced later.

The code assigned to `prep` can be easily mapped to C code (with some extendablity). There are two kinds of statement: use `Assign` to update variable's value, and use `If` to make conditional execution. Before we writing actual code we need to define the variables we need.

There are two kinds of variable: temporary variables cannot keep its content during processing of multiple packets, while permanent variables can. Internally permanent variables are kept in a hash table called instance table, and instance references to a group of permanent variables for a packet stream. To determine which instance is for current packet, Rubik extracts some header fields as key and searchs matched instance in instance table in the instance stage. Variables are defined in `layout` subclasses like header; use two separate classes for temporary and permanent variables:

```python
# temp variables
class tcp_temp(layout):
    wnd = Bit(32)
    wnd_size = Bit(32)
    data_len = Bit(32)


# perm variables
class tcp_data(layout):
    active_lwnd = Bit(32, init=0)
    passive_lwnd = Bit(32, init=0)
    active_wscale = Bit(32, init=0)
    passive_wscale = Bit(32, init=0)
    active_wsize = Bit(32, init=(1 << 32) - 1)
    passive_wsize = Bit(32, init=(1 << 32) - 1)
    fin_seq1 = Bit(32, init=0)
    fin_seq2 = Bit(32, init=0)
```

The `init` argument is required for permanent variables. If instance is missing in the table, a new instance will be created with specified initial values. After variables' defination you should assign the layouts to parser's properties and define instance key:

```python
def tcp_parser(ip):
    tcp = ConnectionOriented()  # to be introduced later
    # ...
    # key is assigned to `selector` property
    tcp.selector = (
        [ip.header.saddr, tcp.header.sport],
        [ip.header.daddr, tcp.header.dport],
    )
    tcp.perm = tcp_data
    tcp.temp = tcp_temp
```

Then you could reference variables in `prep` as `tcp.perm.<name>` or `tcp.temp.<name>`.

```python
    # Pythonic abstraction like assignment and function is helpful for complex statement
    tcp.prep = Assign(tcp.temp.data_len, tcp.payload_len)
    tcp.prep = (
        If(tcp.header.syn == 1) >> Assign(tcp.temp.data_len, 1) >> Else() >> tcp.prep
    )
    # ...
```

You can use variables in every place that expects expressions, like event and more.

There are some built-in variables mantaining by runtime, which contain useful values and should not be assigned. These variables are direct properties of parser like `tcp.payload`. Temporary built-in variables are:
* `payload`: the unparsed part of packet
* `cursor`: the length of part parsed by current layer
* `sdu`: the part of content assembled by sequence (*)
* `to_active`/`to_passive`: the direction of current packet (*)

Permanent built-in variables are:
* `current_state`: current state of PSM (*)

Variables labeled (*) will be revised later.

Our last topic in this article is about variable types (and header field types as well). Variables and header fields are either number or byte slice. Number types are fixed width and defined like `<name> = Bit(<bit width>)`, while slice is dynimical width. Slice variables are defined like `<name> = Bit()` and could be assigned to any other slice, while slice header fields are defined like `<name> = Bit(<length expression>)` and their length must be determined by other earlier-parsed fields' contents. Variables of different types has different operators. Basic arithmetic operators like `+` `-` and `<<` are overloaded for number types, while slice operator `[:]` and `.length` property are overloaded for slice type. At last, you could always use de-sugared operator objects from `lang` module directly.