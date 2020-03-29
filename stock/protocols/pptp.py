# pylint: disable = unused-wildcard-import
from weaver.lang import *


class pptp_general(layout):
    length = UInt(16)
    pptp_message_type = UInt(16)
    magic_cookie = Bit(32)


class start_control_connection_request(layout):
    SCCRQ_type = Bit(16, const=256)
    SCCRQ_reserved0 = Bit(16)
    SCCRQ_protocol_version = Bit(16)
    SCCRQ_reserved1 = Bit(16)
    SCCRQ_framing_capabilities = Bit(32)
    SCCRQ_bearer_capabilities = Bit(32)
    SCCRQ_maximum_channels = Bit(16)
    SCCRQ_firmware_revision = Bit(16)
    SCCRQ_host_name = Bit(64)
    SCCRQ_vandor_name = Bit(64)


class start_control_connection_reply(layout):
    SCCRP_type = Bit(16, const=512)
    SCCRP_reserved0 = Bit(16)
    SCCRP_protocol_version = Bit(16)
    SCCRP_result_code = Bit(8)
    SCCRP_error_code = Bit(8)
    SCCRP_framing_capabilities = Bit(32)
    SCCRP_bearer_capabilities = Bit(32)
    SCCRP_maximum_channels = Bit(16)
    SCCRP_firmware_revision = Bit(16)
    SCCRP_host_name = Bit(64)
    SCCRP_vandor_name = Bit(64)


class outgoing_call_request(layout):
    OCRQ_type = Bit(16, const=1792)
    OCRQ_reserved0 = Bit(16)
    OCRQ_call_ID = Bit(16)
    OCRQ_call_serial_number = Bit(16)
    OCRQ_minimum_BPS = Bit(32)
    OCRQ_maximum_BPS = Bit(32)
    OCRQ_bearer_type = Bit(32)
    OCRQ_framing_type = Bit(32)
    OCRQ_packet_recv_ws = Bit(16)
    OCRQ_packet_processing_delay = Bit(16)
    OCRQ_phone_number_length = Bit(16)
    OCRQ_reserved = Bit(16)
    OCRQ_phone_number = Bit(64)
    OCRQ_subaddress = Bit(64)


class outgoing_call_reply(layout):
    OCRP_type = Bit(16, const=2048)
    OCRP_reserved0 = Bit(16)
    OCRP_call_ID = Bit(16)
    OCRP_peer_call_ID = Bit(16)
    OCRP_result_code = Bit(8)
    OCRP_error_code = Bit(8)
    OCRP_cause_code = Bit(16)
    OCRP_connect_speed = Bit(32)
    OCRP_packet_recv_ws = Bit(16)
    OCRP_packet_processing_delay = Bit(16)
    OCRP_physical_channel_ID = Bit(32)


class set_link_info(layout):
    SLI_type = Bit(16, const=3840)
    SLI_reserved0 = Bit(16)
    SLI_peer_call_ID = Bit(16)
    SLI_reserved = Bit(16)
    SLI_send_ACCM = Bit(32)
    SLI_recv_ACCM = Bit(32)


class echo_request(layout):
    ERQ_type = Bit(16, const=1280)
    ERQ_reserved0 = Bit(16)
    ERQ_identifier = Bit(32)


class echo_reply(layout):
    ERP_type = Bit(16, const=1536)
    ERP_reserved0 = Bit(16)
    ERP_identifier = Bit(32)
    ERP_result_code = Bit(8)
    ERP_error_code = Bit(8)
    ERP_reserved1 = Bit(16)


def pptp_parser(ip):
    pptp = ConnectionOriented()
    pptp.header = pptp_general + AnyUntil(
        [
            start_control_connection_request,
            start_control_connection_reply,
            outgoing_call_request,
            outgoing_call_reply,
            set_link_info,
            echo_request,
            echo_reply,
        ],
        False,
    )
    pptp.selector = ([ip.header.saddr], [ip.header.daddr])

    CLOSED = PSMState(start=True, accept=True)
    (
        REQUEST_CONNECT,
        CONNECTION_ESTABLISHED,
        REQUEST_SESSION,
        SESSION_ESTABLISHED,
        ECHO_SENT,
    ) = make_psm_state(5)

    pptp.psm = PSM(
        CLOSED,
        REQUEST_CONNECT,
        CONNECTION_ESTABLISHED,
        REQUEST_SESSION,
        SESSION_ESTABLISHED,
        ECHO_SENT,
    )

    pptp.psm.SCCRQ_sent = (CLOSED >> REQUEST_CONNECT) + Predicate(
        pptp.to_passive & pptp.header_contain(start_control_connection_request)
    )

    pptp.psm.SCCRP_sent = (REQUEST_CONNECT >> CONNECTION_ESTABLISHED) + Predicate(
        pptp.to_active & pptp.header_contain(start_control_connection_reply)
    )

    pptp.psm.OCRQ_sent = (CONNECTION_ESTABLISHED >> REQUEST_SESSION) + Predicate(
        pptp.to_passive & pptp.header_contain(outgoing_call_request)
    )

    pptp.psm.OCRP_sent = (REQUEST_SESSION >> SESSION_ESTABLISHED) + Predicate(
        pptp.to_active & pptp.header_contain(outgoing_call_reply)
    )

    pptp.psm.session_config_passive = (
        SESSION_ESTABLISHED >> SESSION_ESTABLISHED
    ) + Predicate(pptp.to_active & pptp.header_contain(set_link_info))

    pptp.psm.session_config_active = (
        SESSION_ESTABLISHED >> SESSION_ESTABLISHED
    ) + Predicate(pptp.to_passive & pptp.header_contain(set_link_info))

    pptp.psm.keep_alive = (SESSION_ESTABLISHED >> ECHO_SENT) + Predicate(
        pptp.to_passive & pptp.header_contain(echo_request)
    )

    pptp.psm.maintain_connection = (ECHO_SENT >> SESSION_ESTABLISHED) + Predicate(
        pptp.to_active & pptp.header_contain(echo_reply)
    )

    return pptp
