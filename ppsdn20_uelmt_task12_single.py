from controller import SDNApplication

# Basic imports for Ryuu
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

#tm task=learning

class ppsdn_uelmt_task12(SDNApplication):

    # initial sdn
    def __init__(self, *args, **kwargs):
        super(ppsdn_uelmt_task12, self).__init__(*args, **kwargs)
        self.info("Task 1.2")
        # set a data construction to save MAC Address Table
        self.MAC_TO_PORT = {}
        self.pkt_count = {}

    # There is switch handler for a new switch connecting to the controller
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        # manage the initial link, from switch to controller
        self.MAC_TO_PORT[dp.id] = {}
        self.pkt_count[dp.id] = 0

    # There is switch handler for a new packet coming in at the controller
    # get datapath and openflow protocol
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
    
        #first parser openflow protocol, get information from ev object
        msg = ev.msg
        datapath = msg.datapath
        data = msg.data
        
        pkt = packet.Packet(ev.msg.data)
        parser = datapath.ofproto_parser

        # analysize packet, get ethernet data, get host MAC info
        pkt = packet.Packet(data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src
        
        # get switch port where host packet send in
        in_port = msg.match['in_port']
        
        # save src data into dictionary to MAC address table
        self.MAC_TO_PORT[datapath.id][src]= in_port
        
        # matches on destination address and forwards packet to destination, if learned
        if self.MAC_TO_PORT[datapath.id].has_key(dst):
            out_port =self.MAC_TO_PORT[datapath.id][dst] 
            match = parser.OFPMatch(
                eth_dst = dst
            )
            self.set_flow(datapath, match, [parser.OFPActionOutput(out_port)], priority = 1, hard_timeout = 0, idle_timeout = 0)
            self.send_pkt(datapath, data, port = out_port)
        # if no learned, floods
        else:
            self.send_pkt(datapath, data, port = ofproto.OFPP_FLOOD)

