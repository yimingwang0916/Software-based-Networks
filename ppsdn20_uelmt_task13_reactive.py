from controller import SDNApplication

# Basic imports for Ryu
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

#tm task=priorityfilter

# port1 = N1 11.0.0.0/8
# port2 = N2 22.0.0.0/8
# port3 = N3 33.0.0.0/8

class ppsdn20_uelmt_task13(SDNApplication):

    # initial sdn
    def __init__(self, *args, **kwargs):
        super(ppsdn20_uelmt_task13, self).__init__(*args, **kwargs)
        self.info("Task 1.3")
        self.pkt_count = {}
        
    # There is switch handler for a new switch connecting to the controller
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        # manage the initial link, from switch to controller
        self.pkt_count[datapath.id] = 0
        
    # There is packet-in handler
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        
        # first parser openflow protocol, get information from ev object
        msg = ev.msg
        data = msg.data
        datapath = msg.datapath
        
        parser = datapath.ofproto_parser
        
        pkt = packet.Packet(data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src
        
        ip = pkt.get_protocol(ipv4.ipv4)

        ourN1_address_range = IPNetwork("11.0.0.0/8")
        ourN2_address_range = IPNetwork("22.0.0.0/8")
        ourN3_address_range = IPNetwork("33.0.0.0/8")
       
        if IPAddress(ip.src) in ourN1_address_range:
            if IPAddress(ip.dst) in ourN2_address_range:
                match = parser.OFPMatch(
                    eth_type = ether_types.ETH_TYPE_IP,
                    #
                    ipv4_dst = ('22.0.0.0', '255.0.0.0'),
                    ipv4_src = ('11.0.0.0', '255.0.0.0')
                )
                self.set_flow(datapath, match, [parser.OFPActionOutput(2)], priority = 4, hard_timeout = 0, idle_timeout = 0)
                self.send_pkt(datapath, data, port = 2)
            else:
                if IPAddress(ip.dst) in ourN3_address_range:
                    match = parser.OFPMatch(
                        eth_type = ether_types.ETH_TYPE_IP,
                        ipv4_dst = ('33.0.0.0', '255.0.0.0'),
                        ipv4_src = ('11.0.0.0', '255.0.0.0')
                    )
                    self.set_flow(datapath, match, [parser.OFPActionOutput(3)], priority = 4, hard_timeout = 0, idle_timeout = 0)
                    self.send_pkt(datapath, data, port = 3)
                else:
                   return
        else:
            return
#            match = parser.OFPMatch(
#                eth_type = ether_types.ETH_TYPE_IP,
#                ipv4_src = ('10.0.0.0', '255.0.0.0')
#            )
#            self.set_flow(datapath, match, [parser.OFPActionOutput([])], priority=100, hard_timeout=600, idle_timeout=60)
#            print('from non-public IP source addresses')

