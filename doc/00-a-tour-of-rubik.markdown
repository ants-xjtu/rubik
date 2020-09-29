> Author: Sun Guangda \
> Date: 2020.9.23

In this article, I will go through the main concepts and features of Rubik. Some of them are overlapped to the content of the paper, but in a programmer's perspective rather than a designer.

Rubik is a parser generator, which means it takes a python module (normally a single file) as input (which is allowed to import reusable components provided by Rubik and others) and generates a huge C source file. The source file can further be compiled by GCC or Clang, and linked against the runtime library provided by Rubik and code contains custom middlebox functionalities provided by the user. As a user of Rubik, you still need to write some code in C to specify how you would like to treat payload data of e.g. TCP; Rubik does not have a super cow power to guess it out. However, you are free from extracting that payload data out of raw packets, since this task is taken care of by Rubik perfectly.

As the first view, I will introduce the executing model and order of Rubik, which is essential to learn how you can configure Rubik's behavior, where to put custom middleboxes, and what input those middleboxes are fed.

*TODO: executing diagram*

The parsing process of each packet is divided into several **layers**. One processing layer takes the responsibility of parsing one protocol layer of the packet. Since the input packets may belong to different protocols/protocol stacks, different layer sequences must be used for parsing different packets. To achieve that, all available layers are organized into a parsing tree, and one layer (usually Ethernet) is chosen as an entry point which handles all packets. After the parsing process of one layer, one successor layer of it must be selected to continue parsing the packet or if there's no successor than the packet is fully parsed. In the input Python module of Rubik (aka stack configure), three things mention above must be specified:
* which layers are involved
* how these layers are connected into a parsing tree
* what is the entry condition of each layer except the global entry point

It will be shown in detail how to write this configure in the following examples. Notes that Rubik allows many instances of the same parsing layer coexist in a stack configure, for example, to parse a network traffic mixing TCP and GTP streams, you may want to use two TCP layer instances: one for vanilla TCP packets which connect as `eth -> ip -> tcp`, and the other one for GTP-wrapped TCP streams which connects as `eth -> ip -> udp -> gtp -> ip2 -> tcp2` (the IP layer also initializes two instances in this example). The supporting to multiple initializations means that it must be between layer **prototype** and **instance**. The user should define the behavior of a layer as a layer prototype, and initialize as many instances as she wants modeling from that prototype. From now on the word "prototype" will be used to reference layer prototype and the "layer" is for layer instance.

Let's look more deeply into a layer. The parsing process inside a layer is divided into six stages (which is not pipelined in executing). The stages are linearly executed and there's no loop so every layer spends a fixed time to process a packet. The stages are named:
* header: parse the content of the packet and read from necessary header fields
* instance: find stream instance that the current packet belongs to in a layer-owned hashtable
* preparation: assign to variables which would be used in the following stages
* sequence: maintain a reorder buffer for the current stream
* PSM (protocol state machine): maintain a state machine for the current stream
* event: user-defined custom code

The first thing to notice is that most of the stages are optional. For the simplest layer only the header stage is required (which will be shown in the demo later). The instance stage must exist if you want to use sequence and PSM stages, or declare instance variables (which is covered later), and PSM stage must exist if you want to use instance stage. Some stages also provide useful built-in variables, and you must include those stages if you want to use the variables.

The second thing is about implementation details. Rubik introduces an IR (immediate representation) and an optimizer works on it, which helps Rubik to output high-performance C code which may reorder stages and operations and remove unnecessary ones. As a result, the 6-stage model is only logically ensured for providing a stable programming interface to the user, for example, knowing that the event stage is always after the PSM stage lets the user infers that custom code in the event stage will always access to state machine's current state which is already modified by current packet, and for the similar reason configure in the preparation stage will always access to the "previous" state of the state machine which is still not modified by the current packet. While gaining an easier-to-use programming model thanks to the logical executing model, the user also should not worry about performance and keep all logic in the stage that most suitable to it and let the optimizer to handle the rest.

In a word, when a packet is incoming, Rubik runtime puts it into a parsing layer, executes some of the six stages, then selects another proper parsing layer according to some conditions and executes the stages of it, and does this again and again until the last layer is finished. Normally user could execute arbitrary custom code at the end of each layer that the packet goes through, which means the user has multiple chances to insert their code, one time for one layer (and for one protocol layer). Each layer can access all variables of all previous-executed layers, for example, you could still get the IP pair of a packet even in the event stage of the TCP layer.

In the rest part of this article, I will show you how to write a layer prototype, starts from the simplest nop prototype, and ends in a fully-functional one that generally involved every feature of Rubik. And finally, I will initialize an instance in a TCP/IP stack configure.

----

Suppose we want to "invent" a new protocol to replace TCP called SuperProtocol. We could start with the following boilerplate:

```python
from rubik.lang import *

class super_header(layout):
    pass

def super_protocol():
    sp = ConnectionOriented()
    sp.header = super_header
    return sp
```

The configure above defined a layer prototype which does nothing. The header stage is mandatory to a prototype, so we assigned a blank class to it to indicate that it should parse nothing from the packet. There are two more things to be noticed:
* We are creating the prototype inside a function. This warpping function is the representation for prototype, and the returned value is basically a layer instance. The function may take arguments as we will see later, and it always return an instance of `Connectionless` or `ConnectionOriented` class, which is...
* Rubik differentiates protocols into two types: connectionless protocols have no round-trip semantic, and connection-oriented ones have. This doesn't mean that connectionless protocols cannot have stream. For example, IP is a common connectionless protocol with streams assembled with fragment packets. Connectionless only means that all packets of one stream instance always send in the same direction, while a connection-oriented stream instance may send packets back and forth. We will revisit this concept later.

The `super_header` class is inherited from `layout` base class, which indicates we are declaring a layout instance. Layout is similar to struct in C, and we use layouts to declare both packet header fields and variables. Keep in mind that althrough we use Python's class syntax here, what we are doing here is not to create a type, but to create a layout instance. Actually you will never get more than one `super_header` to use. We are using underscore naming style for `super_header` (and `layout`) to reflect this fact.

For the step two we are going to fill `super_header` layout with some header fields.

```python
class super_header(layout):
    srcport = UInt(16)
    dstport = UInt(16)
    flag_hello = Bit(2)
    flag_goodbye = Bit(2)
    _flag_reserved = Bit(4)
    offset = UInt(32)
    length = UInt(16)
```

The fields are defined in class-level variable syntax. The argument for `Bit` and `UInt` is the bit length of the field. The different of `UInt` from `Bit` is that an `UInt` field will automatically converted from network endian to host endian before accessing, so it is quite handy for multi-byte number fields. You could create `Bit` field of 1, 2, 4, 8 bytes long, and sub-byte fields group as long as they are aligned to byte. You could also create variable length `Bit` field by passing an expression as argument. We will cover more usage of layout and field-declaration in other documents.

So let's take a look at the fields. The protocol contains two fields for source and destination ports, one field to indicate the offset of payload of the current packet which starts from 0 and one field to record the payload length. It also includes two 2-bit flags. To make this example familiar to user I'm going to use classical 3-packet handshaking and 4-packet handwaving for establishing and finalizing a connection, so two 2-bit indices are allocated to record which step is reached, and `flag_hello` will always be `0x11` after the handshaking phrase, while a normal data transfer packet will set all 4 bits to 1. 

For now if Rubik parses a packet with our `super_protocol` layer, it will recognize some useful fields from packet which could be used in the later stages. So let's move on to instance stage which is next to header stage. Same to TCP we would like to use the 4-tuple as instance key, however, the IP pair is not existed in `super_header` layout! So we need to acquire the fields from a previous executed layer:

```python
def super_protocol(ip):
    sp = ConnectionOriented()
    sp.header = super_header
    sp.selector = (
        [ip.header.srcaddr, sp.header.srcport],
        [ip.header.dstaddr, sp.header.dstport],
    )
```

Now you see the basic rule here: a prototype is a function, which takes layer(s) as argument(s), and return a layer upon calling. And the about-to-create layer has the same interface of any layer passed in. For the instance stage, we assigned a 2-tuple to layer's `selector` attribute. So that the instance stage will be enabled, and Rubik will use the tuple as selecting key to find the matched instance from a hashtable dedicated to SuperProtocol. If it is not found, Rubik will treat the current packet as the first packet of a new stream and create a instance for it in the hashtable.

The selector is written in a form of a symmetrical bi-tuple, and each element in the tuple is a list called a half key. To provide two half keys instead a whole key is a special requirement of connection-oriented protocols, and you can simply assign a list of header fields as key for a connectionless protocol. Logically Rubik will try to fetch the instance from hashtable twice: one time with key `[srcaddr, srcport, dstaddr, dstport]` and the other time with key `[dstaddr, dstport, srcaddr, srcport]`. If the first fetching is succeed, then current packet is sent in the same direction of the first packet of the stream, which is called active-to-passive direction; if the second fetching is succeed, then the current packet is sent in the reversed direction of the first packet called passive-to-active; in the case that both fetching is failed, the current packet does not belong to any known stream and Rubik will insert a new instance with the first key. So after the instance stage, Rubik not only activated all the variables but also determined the direction of the packet, which is provided to user through `sp.to_active` and `sp.to_passive` built-in variables. We are going to use them in the PSM.

One more thing to notice is that we are using `sp.header.srcport` syntax to access fields defined in `super_header`. This is equavilent to `super_header.srcport`. The syntax is helpful for referencing header fields from other layers since we may not know which foreign layout the field is from.

The next stage called preparation is designed to give a place for user to assign their variables. Before we writing configure for preparation stage we should create the variables first. There are two kinds of variable: temporary variables only live for one packet (four last stages of a layer actually) and are dropped after the packet is parsed, while permanent variables live for all packets of the streams and are only released after the stream is end. For our simple protocol we need no variable actually; just for demonstration let's make a (in most time false) assumption that there may be some postfix padding after the payload of SuperProtocol introduced by someone, so the built-in variable `sp.payload` actually contains garbage bytes and needs to be truncated. Let's define a temporary variable for truncated payload:

```python
    # after sp.selector
    class temp_variables(layout):
        payload = Bit()

    sp.temp = temp_variables
```

We declared the variables using `Bit` with no argument, this is the way to declare a byte slice variable. Byte slice is a first-class variable type supported by Rubik along with rich operators. Let's assign proper value for it:

```python
    sp.prep = (
        If((sp.header.flag_hello == 0x11) & (sp.header.flag_goodbye == 0x11)) >> (
            Assign(sp.temp.payload, sp.payload[sp.header.length:])
        ) >> Else() >> (
            Assign(sp.temp.payload, NoData())
        )
```

This part of configure is written in a C-like but highly limited DSL. The only supported "keywords" are `If(expr)`, `Else()` and `Assign(variable, expr)`. In the expressions several operators could be used, and bitwise `&` stands for boolean and operation here. For details check other documents.

Now it's time for sequence stage. We define a `Sequence` instance with several properties:

```python
    sp.seq = Sequence(meta=sp.header.offset, data=sp.temp.payload, zero_based=True)
```

We passed payload slice and the offset of it to the sequence, and the sequence will sort the payload parts and assemble them into SDU. The `zero_based` flag indicates whether `meta` is started from 0 or a random number like TCP. Sequence supports more high-level functionalities like window controling, and you could check other documents for them.

The last useful tool is a state machine that works in the PSM stage. It is a normal state machine with one start state and several accepted states. The state machine transits one time per packet based on the content of packet and previous state, and the instance will be removed from hashtable if any of the accepted states is reached after parsing a packet. Let's first create the states and the state machine instance:

```python
    START = PSMState(start=True)
    HS1_SENT, HS2_SENT, ESTABLISHED, WV1_SENT, WV2_SENT, WV3_SENT = make_psm_state(6)
    FINISHED = PSMState(accept=True)
    sp.psm = PSM(START, HS1_SENT, HS2_SENT, ESTABLISHED, WV1_SENT, WV2_SENT, WV3_SENT, FINISHED)
```

Function `make_psm_state` is a utility to create multiple states in one line. Now let's create transitions between states:

```python
    sp.psm.hs1 = (START >> HS1_SENT) + Pred(sp.header.flag_hello == 00)
    sp.psm.hs2 = (HS1_SENT >> HS2_SENT) + Pred(sp.to_active & sp.header.flag_hello == 01)
    sp.psm.hs3 = (HS2_SENT >> ESTABLISHED) + Pred(sp.to_passive & sp.header.flag_hello == 10)
```

The transition consists three parts: source/destination states pair, triggered predication, and an optional action which is taken when transition is triggered. In the code above we defined three transitions for hankshaking, without failure handling when parsing a protocol-voilenced packet. A broken packet which fails to trigger any transition will trigger a built-in `sp.fail` event in debug mode, and it will be ignored and cause compiled C function to return `1` in production mode. More in other documents.

There should be a transtion loopback on established state for data transfering:

```python
    sp.psm.est = (ESTABLISHED >> ESTABLISHED) + Pred(sp.header.flag_hello == 11 & sp.header.flag_goodbye == 11)
```

Notice that in a connected-oriented layer two separated sequences are created for each direction while one PSM is shared by them.

The next transition is for entering hand-waving phrase. Here comes an issue: the packets may be out of order so that the first hand-waving packet may arrive earlier that the last data transfering one. We would like to delay the transition until all data-transfering packet is parsed so we could make sure that all the data is properly assembled in the next stage. How do we implement it?

First let's make a rule: The hand-waving packets should set their `offset` field to the total length of payload. Then we could get help from our sequence: remember that we pass the offset field field as `meta` property to the sequence for every packet including the hand-waving ones, so the sequence will insert a zero-lengthed payload at the expected end of data buffer, and wait for the payload carried by the following packets to fulfill the "hole" before it. So that our problem becomes: we want to write the prediction of the transition as, "not only the hand-waving flag is shown in a parsed packet, but also there's no 'hole' in the reorder buffer so every received payload is sorted". Since this kind of predication is so common, Rubik provides a syntax sugar for it:

```python
    sp.psm.wv1 = (ESTABLISHED >> WV1) + Pred(sp.v.header.flag_goodbye == 00 & sp.header.flag_hello == 11)
```

Notice the special `sp.v.header.flag_goodbye` syntax. It has the exactly same meaning descibed above. The rest transitons are similar to the handshaking ones so I will omit them for saving space.

> You may notice that we are not tracking the direction of each hand-waving packet. This would require a permanent variable to record that which side porposed the hand-waving. It's a simple exercise left for you!

The last stage of a layer is event. There are two reasons to write configure in event stage: either the logic doesn't fit in any other stages, or you want to execute some custom C code. For the first reason, one common usage is to assemble data in the reorder buffer:

```python
    sp.event.asm = If(sp.psm.est) >> Assemble()
```

We are using transition itself in the condition to express that the event is triggered only when the transition is trigger in the PSM stage. In this simple case it may be better to directly append `+ Assemble()` in the `sp.psm.est` transition. But for some more complicated scenario such as assemble only when both the trasition is triggered and certain flags are set in the header fields or certain number of packets are parsed according to a permanent counter, it may be better to perform assembling in event stage. The `Assemble` action squeezes out all sorted payload in reorder buffer into built-in variable `sp.sdu`, which enables high-level applications to receieve sorted data fragments without waiting for the completion of transfering.

For the second reason which is calling custom C functions, you should make a decision before proceeding: remember that you are writing a prototype, and everything inside it will be preserved in all layer instances, so we should keep the whole prototype reusable and has no relation to any specificated application, and put a debug hook into event stage is absolutely not elegant. There is one more chance to register events: you could do it on layers after intializing them in stack configure. But just for demonstration let's add a custom function that will do something with assembled payload length.

First we need to declare a layout for the name of C function and the arguments we want to pass into it:

```python
    class on_assemble(layout):
        assembled_length = Bit(32)
```

Notice you should not use `UInt` other than header layouts. Then create an event to call the function:

```python
    sp.event.on_assemble = If(so.event.asm) >> (
        Assign(on_assemble.assembled_length, sp.sdu.length) +
        Call(on_assemble)
    )
```

We are using `sp.event.asm` in the condition just like we did with transition. For the last thing, we need to make sure that our custom event must happen after the assemble event. We could specify it with:

```python
    sp.event += sp.event.asm, sp.event.on_assemble
```

Ok, we finally finish our SuperProtocol parser! Now let's drop it into a TCP/IP stack and build an executable for it!

Create a file called `stack_conf.py` in the root directory of Rubik, and this file name is the default name specified by `Makefile`. Copy the content of `stock/tcp_ip.py` into it:

```python
# omit imports
stack = Stack()
stack.eth = eth_parser()
stack.ip = ip_parser()
stack.tcp = tcp_parser(stack.ip)
stack.udp = udp_parser()

stack += (stack.eth >> stack.ip) + Predicate(1)
stack += (stack.ip >> stack.tcp) + Predicate(
    (stack.ip.psm.dump | stack.ip.psm.last) & (stack.ip.header.protocol == 6)
)
stack += (stack.ip >> stack.udp) + Predicate(
    (stack.ip.psm.dump | stack.ip.psm.last) & (stack.ip.header.protocol == 17)
)
```

The configure file contains two parts. The first part initialize all layers from their prototypes, and the layers are assign to properties of `stack` with any name you like. Notice we are passing a layer instance `stack.ip` as the argument of prototype `tcp_parser`. It's important that you must assign a layer to the stack immediately after it is returned by the prototype. Don't pass them around or Python may mess them up. The second part defines the shape of parsing tree along with entry condition of each layer. The syntax is similar to PSM. Now Let's add our layer into the tree:

```python
stack.sp = super_protocol(stack.ip)
stack += (stack.iip >> stack.sp) + Predicate(
    # let's say we fake IP packets contains SuperProtocol payload with protocol number 42
    (stack.ip.psm.dump | stack.ip.psm.last) & (stack.ip.header.protocol == 42)
)
```

Now you can build the stack according to the instructions in readme. Fill the template of `on_assemble` function with any code you like and look for result!

Please check the other documents in this folder for more details.