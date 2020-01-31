# pylint: disable = unused-wildcard-import
from weaver.lang import *


def gtp():
    proto = ProtoCore()

    parser = HeaderParser.parse(proto, Layout({
        #
    }))