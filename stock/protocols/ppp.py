# pylint: disable = unused-wildcard-import
from weaver.lang import *


class PPP_short_header(layout):
    short_protocol = Bit(1 * 8)


class PPP_header(layout):
    address = Bit(8)
    control = Bit(8)
    protocol = UInt(2 * 8)


class PPP_LCP_header(layout):
    LCP_code = Bit(8)
    LCP_ID = Bit(8)
    LCP_length = UInt(2 * 8)


class PPP_IPCP_header(layout):
    PPP_IPCP_code = Bit(8)
    PPP_IPCP_ID = Bit(8)
    PPP_IPCP_length = UInt(2 * 8)
    PPP_IPCP_data = Bit(PPP_IPCP_length - 4)


class PPP_CHAP_header(layout):
    CHAP_code = Bit(8)
    CHAP_ID = Bit(8)
    CHAP_length = UInt(2 * 8)
    CHAP_data = Bit(CHAP_length - 4)


class PPP_CCP_header(layout):
    CCP_code = Bit(8)
    CCP_ID = Bit(8)
    CCP_length = UInt(2 * 8)
    CCP_data = Bit(CCP_length - 4)


class PPP_IPV6CP_header(layout):
    IPV6CP_code = Bit(8)
    IPV6CP_ID = Bit(8)
    IPV6CP_length = UInt(2 * 8)
    IPV6CP_data = Bit(IPV6CP_length - 4)


class PPP_LCP_ACCM_option(layout):
    ACCM_type = Bit(8, const=2)
    ACCM_length = Bit(8)
    ACCM_value = Bit((ACCM_length - 2) * 8)


class PPP_LCP_AP_option(layout):
    AP_type = Bit(8, const=3)
    AP_length = Bit(8)
    AP_value = Bit((AP_length - 2) * 8)


class PPP_LCP_MN_option(layout):
    MN_type = Bit(8, const=5)
    MN_length = Bit(8)
    MN_value = Bit((MN_length - 2) * 8)


class PPP_LCP_PFC_option(layout):
    PFC_type = Bit(8, const=7)
    PFC_length = Bit(8)


class PPP_LCP_ACFC_option(layout):
    ACFC_type = Bit(8, const=8)
    ACFC_length = Bit(8)


class PPP_LCP_MRU_option(layout):
    MRU_type = Bit(8, const=1)
    MRU_length = Bit(8)
    MRU_value = Bit((MRU_length - 2) * 8)


class PPP_temp_data(layout):
    protocol = UInt(32)


def ppp_parser(ip, gre):
    PPP = ConnectionOriented()
    PPP.header = (
        If(gre.perm.short_PPP == 0)
        >> PPP_header
        + (If(PPP.header.protocol == 0xC223) >> PPP_CHAP_header)
        + (If(PPP.header.protocol == 0x80FD) >> PPP_CCP_header)
        + (If(PPP.header.protocol == 0x8021) >> PPP_IPCP_header)
        + (If(PPP.header.protocol == 0x8057) >> PPP_IPV6CP_header)
        + (
            If(PPP.header.protocol == 0xC021)
            >> PPP_LCP_header
            + AnyUntil(
                [
                    PPP_LCP_ACCM_option,
                    PPP_LCP_AP_option,
                    PPP_LCP_MN_option,
                    PPP_LCP_PFC_option,
                    PPP_LCP_ACFC_option,
                    PPP_LCP_MRU_option,
                ],
                PPP.cursor < PPP.header.LCP_length + 4,
            )
        )
    ) + (
        If(gre.perm.short_PPP)
        >> PPP_short_header
        + (If(PPP.header.short_protocol == 0xC223) >> PPP_CHAP_header)
        + (If(PPP.header.short_protocol == 0x80FD) >> PPP_CCP_header)
        + (If(PPP.header.short_protocol == 0x8021) >> PPP_IPCP_header)
        + (If(PPP.header.short_protocol == 0x8057) >> PPP_IPV6CP_header)
        + (If(PPP.header.short_protocol == 0xC021) >> PPP_LCP_header)
    )

    PPP.temp = PPP_temp_data

    PPP.preprocess = (
        If(gre.perm.short_PPP) >> Assign(PPP.temp.protocol, PPP.header.short_protocol)
    ) + (If(gre.perm.short_PPP == 0) >> Assign(PPP.temp.protocol, PPP.header.protocol))

    PPP.selector = ([ip.header.saddr], [ip.header.daddr])

    SESSION = PSMState(start=True, accept=True)
    (
        active_passive_sent_ACFC,
        passive_sent_ACFC_active_no,
        active_ACFC_acked_passive_no,
    ) = make_psm_state(3)

    PPP.psm = PSM(
        SESSION,
        active_passive_sent_ACFC,
        passive_sent_ACFC_active_no,
        active_ACFC_acked_passive_no,
    )

    PPP.psm.config = (SESSION >> SESSION) + Predicate(
        (PPP.temp.protocol != 0x0021) & PPP.header_contain(PPP_LCP_ACFC_option)
    )

    PPP.psm.p_sent_AFCF = (SESSION >> passive_sent_ACFC_active_no) + Predicate(
        PPP.to_passive & PPP.header_contain(PPP_LCP_ACFC_option)
    )
    PPP.psm.a_after_p_sent_AFCF = (
        passive_sent_ACFC_active_no >> active_passive_sent_ACFC
    ) + Predicate(PPP.to_active & PPP.header_contain(PPP_LCP_ACFC_option))

    PPP.psm.a_AFCF_acked = (
        active_passive_sent_ACFC >> active_ACFC_acked_passive_no
    ) + Predicate(PPP.to_passive)

    PPP.psm.a_p_AFCF_acked = (active_ACFC_acked_passive_no >> SESSION) + Predicate(
        PPP.to_active
    )

    PPP.psm.tunneling = (SESSION >> SESSION) + Predicate(PPP.temp.protocol == 0x0021)

    PPP.event.switch_to_short = If(PPP.psm.a_p_AFCF_acked) >> Assign(
        gre.perm.short_PPP, 1
    )

    return PPP
