> Author: Sun Guangda \
> Date: 2020.9.30

This is the catch-up document for expressions and variables in Rubik. Expressions could appear in:
* length expression of variable-length field
* condition in header stage
* preparation statement
* sequence property
* prediction and action statement in PSM stage
* condition and action statement in event stage
* layer entry condition

The "statement" above only includes two types: `If`-`Else` block and `Assign` statement, and the latter one make an assignment of the value of an expression to a variable. Notice that there's one place which suprisingly do not allowed expression: instance selector definition. It must be a list or a tuple of two lists which only contains plain header fields.

#### Expression and variable type

There are two variable types in Rubik: number type and byte slice type. Number type includes fixed fields of all full-byte length and also bit fields. Byte slice type is implemented as a tuple composed by a pointer to the head byte of buffer and a length field, which is the same as Rust's built-in `&[u8]` slice type. Byte slice is technically a "byte slice view", which does not own any data by itself. All byte slices created in a layer configure are either a part of packet or empty slice. As a result, all slices share the same underlaying buffer and there's no modifying opertor defined for them.

Each expression also has a type. Constant number has number type and constant empty slice has slice type. Expressions that simply read a variable have the same type as read variable. The type of expression decides which set of operators are defined on it. For a number expression, you can:
* operate `+`, `-`, `<<`, `>>` with another number-typed expression as the right-hand operand, and the result expression has number type
* operate `==`, `!=` with another number-typed expression as the right-hand operand, or use `NotOp(expr)` which is an unary operator, and the result expression has number type (`0` for false and `1` for true)
* operate `&`, `|` with anumber number-typed expression as the right-head operand, which has two cases:
    * if the left-hand expression is a variable, these are bitwise operators
    * if the left-hand expression is compound expression, these are logical operators

    Both cases result an number-typed expression.

For a slice expression, you can:
* operate `[a:b]` where `a` and `b` are number-typed expressions to shorten the slice from two sides, and the result is a slice
* operate `[i]` where `i` is number-typed expression to extract a byte from slice, and the result is a number
* access read-only property `.length` to get the length of the slice, and the result is a number

Adding custom operators to number and slice types are quite easy. The corresponding document will be released once the related interface is stable.

#### Built-in variables

There are a few variables provided by Rubik runtime which is useful on centain stages and cases.
* `payload` is the *unparsed* part of the packet, which may keep changing in header stage
* `cursor` is the length of parsed part by current layer of the packet
* `sdu` equals to `payload` if `Assemble` statement is not executed, and stores the result of `Assemble` statement
* `current_state` is the index of current state in PSM, the state corresponds to current packet in event stage and corresoponds to previous packet (or start state if no previous packet) before event stage
* `to_active` and `to_passive` indicate the direction of current packet, currently they are implemented as expression

You should never assign to these variables.

#### Virtual expression

The concept of virtual expression is shown in the tour. Internally Rubik create a permanent variable for each virtual expression to record that if the expression "has been" true for any past packet (including current one), and virtual expression will be true if both and permanent variable is set and sequence has no unsorted fragment (there no "hole" in recived buffer). Thus you must define instance and sequence stage if you want to use virtual expression.

A simple virtual expression is easy to understand, for example, `sp.v.header.x == 1` means "a packet with x field set to 1 has been seen and sequence is sorted". However, things get complicated when virtual expressions are compounded with boolean operators. With negating operator, `NotOp(sp.v.header.x == 1)` means "the expected packet has not been seen or the sequence is still unsorted", which has a different meaning with `sp.v.header.x != 1`. With logical and expression, `sp.v.header.x == 1 & sp.v.header.y == 1` means "both flags has been seen to be set **in the same packet**, and the sequence is sorted now". The internal permanent variable is actually tracking expression `sp.header.x == 1 & sp.header.y == 1`, which means virtual expressions *extend* across logical and operators. So the expression is equivalent to `sp.v.header.x == 1 & sp.header.y == 1`, but it's less obvious to write in this way. In one word, virtual expressions extend across logical and, but not extend across logical or and logical not operators. If you really need the semantic different from virtual expression's behaviour, try to desugar the code and use permanent variable directly.