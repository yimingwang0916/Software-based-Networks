from cockpit import CockpitApp
from netaddr import IPAddress, IPNetwork

# Import dependencies for Ryu
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6, tcp

# Select your task by setting this variable
#tm task=loadbalancer1

class ppsdn20_uelmt_loadbalancing_static(CockpitApp):

    # initial sdn
    def __init__(self, *args, **kwargs):
        super(ppsdn20_uelmt_loadbalancing_static, self).__init__(*args, **kwargs)
        self.info('Task 3.1')
    
    # There is switch features handler
    # proactive flow rules
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        # to make sure host H2 and H3 receive an equal share of the overall traffic
        # N2_address_range = IPNetwork("22.0.0.0/9")
        # N3_address_range = IPNetwork("22.128.0.0/9")
        datapath = ev.msg.datapath

        match = parser.OFPMatch( # from N1 to N2
            eth_type = ether_types.ETH_TYPE_IP,
            ipv4_src = ('11.0.0.0', '255.0.0.0'),
            ipv4_dst = ('22.0.0.0', '255.128.0.0')
        )
        actions = [parser.OFPActionOutput(2)]
        self.program_flow(datapath, match, actions, priority = 10, hard_timeout = 0, idle_timeout = 0)

        match = parser.OFPMatch( # from N1 to N3
            eth_type = ether_types.ETH_TYPE_IP,
            ipv4_src = ('11.0.0.0', '255.0.0.0'),
            ipv4_dst = ('22.128.0.0', '255.128.0.0')
        )
        actions = [parser.OFPActionOutput(3)]
        self.program_flow(datapath, match, actions, priority = 10, hard_timeout = 0, idle_timeout = 0)

