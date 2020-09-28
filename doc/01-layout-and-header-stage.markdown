This is the catch-up document for layout declaration and header stage. You have learned the basic usage of them in [the tour](doc/00-a-tour-of-rubik.markdown).

#### Variable-length field

Variable-length fields are fields that cannot determine length until runtime. There must exist an expression that only depends on the values of fields **occur before this field** and whose value is the **bit length** of this field. A common case of variable-length field is an IP option, whose value field always follows a single-byte length field to record the byte length of it. It could be declared as a layout like:

```python
class ip_option(layout):
    length = Bit(8)
    value = Bit(length << 3)
```

Variable-length fields always have byte slice type.

#### Declare layout for permanent variables

Every permanent variable must have an initial value, which will be used if the instance is just created. The initial value can be any expression that only depends on header fields, and it is indicated with `init` property:

```python
class tcp_perm_vars(layout):
    window_left = Bit(32, init=0)
    window_right = Bit(32, init=(1 << 32) - 1)
```

#### Sequence parsing

You can use `+` to connect layouts to parse them sequentially:

```python
    myproto.header = mylayout1 + mylayout2
```

#### Conditional parsing

You can use `If` statement to parse a layout base on some conditions. The condition could be an expression that depends on header fields that already parsed when encountering the condition.

```python
    myproto.header = mylayout1 + If(mylayout1.has_layout2 == 1) >> mylayout2  # myproto.header.has_layout2 is also available
```

Unlike preparation stage, `Else` syntax is not impemented here. There's also a bug currently occuring if you assign `If` statement to a Python name and then reference to that name in header stage assignment, so just prevent to do it for now. 

#### Options-parsing loop

It is an idiomatic way to design protocol header with variable-number, variable-length optional fields as type-length-variable (TLV). Rubik provides a handy way to define it.

First, declare each of all types of value a layout. The type field of them must appear at the beginning of the layout and have the same length:

```python
class optional_timestamp(layout):
    type = Bit(8, const=6)  # use `const` property to declare type number
    timestamp = UInt(32)
    
class optional_flags(layout):
    type = Bit(8, const=13)
    flag_a = Bit(1)
    flag_b = Bit(4)
    _reserved = Bit(3)
    
class optional_string(layout):
    type = Bit(8, const=25)
    length = Bit(8)
    string = Bit(length << 3)
    
class optional_others(layout):
    type = Bit(8)  # fallback case
    length = Bit(8)
    remain = Bit(length << 3)
    
class end_of_options(layout):
    type = Bit(8, const=0)
```

A fallback case is useful if any of option types we don't care have the same layout. Note that the content of layout (corresponding struct in C) of the fallback case will be override multiple times, so its content is garbage, so you have to define a `optional_string` layout even it has the exact same fields as the fallback layout, since you care about its content rather than just skip it.

An `AnyUntil` statement could be used in header stage with all the option layouts:

```python
    myproto.header = AnyUntil([
        optional_timestamp,
        optional_flags,
        optional_string,
        optional_others,'
        end_of_options,
    ], myproto.header.type == 0)
```

This will generate a `while` loop with a `switch` statement inside, which fill all the layouts of the appeared options. Every option type could only present once in the packet, or the packet will be treated as malformed and the processing will be terminated.
