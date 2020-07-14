#tm task=priorityfilter

from controller import SDNApplication

# Basic imports for Ryuuu
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6
from netaddr import IPAddress, IPNetwork

# port1 = N1 11.0.0.0/8
# port2 = N2 22.0.0.0/8
# port3 = N3 33.0.0.0/8

class ppsdn20_uelmt_task13(SDNApplication):

    # initial sdn
    def __init__(self, *args, **kwargs):
        super(ppsdn20_uelmt_task13, self).__init__(*args, **kwargs)
        self.info("Task 1.3")
        self.datapaths = {}
        
        # by proactive flow rules
        self.proactive_flows = [
            (1, ('11.0.0.0', '255.0.0.0'), 100, 'ipv4_src'),
            (2, ('22.0.0.0', '255.0.0.0'), 100, 'ipv4_src'),
            (3, ('33.0.0.0', '255.0.0.0'), 100, 'ipv4_src'),
        ]

    # There is a switch features handler
    # install flow and match infomations
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        # identifies the switch
        dp = ev.msg.datapath

        print("Installing the flow rule for N1 -> N2")
        # from the SDNApplication base class in controller.py
        # set_flow(
        #   self, datapath, match, actions, 
        #   priority=0, hard_timeout=600, idle_timeout=60)
        
        # 1.flow rule
        # create the match
        match = parser.OFPMatch(**{
            'eth_type' : ether_types.ETH_TYPE_IP, # required for all ip matches
            'ipv4_src' : ('11.0.0.0', '255.0.0.0'), # src=N1
            'ipv4_dst' : ('22.0.0.0', '255.0.0.0'), # dst=N2
        })
        # create output port
        action = [parser.OFPActionOutput(2)]
        self.set_flow(dp, match, action, priority=100)
        print("rule 1 installed")
        
        print("Installing the flow rule for N1 -> N3")
        # 2.flow,rule
        match = parser.OFPMatch(**{
                   'eth_type' : ether_types.ETH_TYPE_IP, # required for all ip matches
                   'ipv4_src' : ('11.0.0.0', '255.0.0.0'), # src=N1
                   'ipv4_dst' : ('33.0.0.0', '255.0.0.0'), # dst=N2
               })
        # create output port
        action = [parser.OFPActionOutput(3)]
        self.set_flow(dp, match, action, priority=100)
        print("rule 2 installed")
        
        print("Installing the flow rule for drop")
        # 3.flow,rule
        match = parser.OFPMatch(**{
                   'eth_type' : ether_types.ETH_TYPE_IP, # required for all ip matches
                   'ipv4_src' : ('10.0.0.0', '255.0.0.0'), # src = 10.0.0.0/8
               })
        # create output port
        action = [] # change to empty array [] to drop packets
        self.set_flow(dp, match, action, priority=0)
        print("rule 3/4 installed")

    # There is packet-in handler
    # when we use proactive flow rules, we don't need this
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        return

