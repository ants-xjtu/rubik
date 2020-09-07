In this article we will show basic ways to write highly customizable logic in Rubik. Normally these logic should be handled in user-defined events (UDE) like example in previous article, but using UDE has some limitations:
* one UDE can only be triggered after everything else in the same layer (with exception)
* coding in UDE cannot affect parsing logic

To address these problems, Rubik provides a property called `prep`; anything assigned to it will be executed before core stages, so it is suitable for data preparation.

> The pipeline of a parsing layer consists of following stages: header parsing, instance lookup, data preparation, payload sequencing, PSM(protocol state machine) execution and event triggering. The details will be introduced later.

The code assigned to `prep` can be easily mapped to C code (with some extendability). There are two kinds of statement: `Assign` for updating variables' value, and `If` for make conditional execution. Before we write the actual code, we need to define the variables we need.

There are two kinds of variable. 1) temporary variable, whose value is not preserved across multiple packets even for a same flow. 2) permanent variable, which is maintained for every flow. Internally permanent variables are kept in a hash table called instance table, and one instance references to a group of permanent variables for a packet stream. To determine which instance belongs to the current packet, Rubik extracts some header fields as key and matches instance in instance table during the instance stage. Variables are defined in `layout` subclasses like headers; and it use two separate classes for temporary and permanent variables:

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

The `init` argument is required for permanent variables. If instance is missing in the table, a new instance will be created with specified initial values. After variables' definition, you should assign the layouts to parser's properties and define instance key(s):

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

You can use variables in every place that expects expressions, for example, events, etc.

There are some built-in variables maintained by runtime, which contain useful values and should not be modified by users. These variables are direct properties of parser like `tcp.payload`. Temporary built-in variables are:
* `payload`: the unparsed part of packet
* `cursor`: the length of part parsed by current layer
* `sdu`: the part of content assembled by sequence (*)
* `to_active`/`to_passive`: the direction of current packet (*)

Permanent built-in variables are:
* `current_state`: current state of PSM (*)

Variables labeled with `*` will be revised later.

Our last topic in this article is about variable types (and header field types as well). Variables and header fields are either number or byte slice. Number types are fixed width and defined like `<name> = Bit(<bit width>)`, while slice has variable width. Slice variables are defined like `<name> = Bit()` and can be assigned to any other slices, while slice header fields are defined like `<name> = Bit(<length expression>)` and their length must be determined by other earlier-parsed fields' value. Variables of different types have different operators. Basic arithmetic operators for example, `+`, `-` and `<<` are overloaded for number types, and slice operator `[:]` and `.length` property are overloaded for slice type. At last, you could always use de-sugared operator objects from `lang` module directly.