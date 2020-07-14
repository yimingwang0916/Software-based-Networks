from controller import SDNApplication
from cockpit import CockpitApp

# Basic imports for Ryu
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6
from netaddr import IPAddress, IPNetwork

#tm task=learning

class ppsdn20_uelmt_task12_twotable(CockpitApp):
    
    # initial sdn
    def __init__(self, *args, **kwargs):
        super(ppsdn20_uelmt_task12_twotable, self).__init__(*args, **kwargs)
        self.info('Task 1.2')
        # set a data construction to save MAC Address Table
        self.MAC_TO_PORT = {}
        self.pkt_count = 0
        
    # programm a new flow into a switch
    def send_flow(self, datapath, match,table_id, actions, priority):
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        flowmod = parser.OFPFlowMod(datapath=datapath, 
            match = match, instructions = inst, priority = priority, table_id = table_id
            )
        datapath.send_msg(flowmod)

    # There is switch handler for a new switch connecting to the controller
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        # manage the initial link, from switch to controller
        self.MAC_TO_PORT[datapath.id] = {}
        self.pkt_count[datapath.id] = 0

        #default "all to controller" flow in table 0 learning table
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.send_flow(datapath, match, 0, actions, priority = 0, idle_timeout=0, hard_timeout=0)

        #default "Flood" flow in table 1 forwarding table
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.send_flow(datapath, match, 1, actions, priority = 0, idle_timeout=0, hard_timeout=0)
    
    # There is switch handler for a new packet coming in at the controller
    # ger datapath and openflow protocol
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
    
        # first parser openflow protocol, get information from ev object
        msg = ev.msg
        datapath = msg.datapath
        data = msg.data
        
        parser = datapath.ofproto_parser
        
        # get switch port where host packet send in
        in_port = msg.match['in_port']

        # analysize packet, get ethernet data, get host MAC info
        pkt = packet.Packet(data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src
        
        # save src data into dictionary to MAC address table
        self.MAC_TO_PORT[datapath.id][src]= in_port
        
        # match on source address and forwarding to controller
        if self.MAC_TO_PORT[datapath.id].has_key(dst):
        
            msg_src = parser.OFPPacketOut(datapath = datapath, match= parser.OFPMatch(eth_src = src), table_id = 0, instructions = [parser.OFPInstructionGotoTable(1)], priority = 3, hard_timeout=0, idle_timeout=0)
            
            msg_dst = parser.OFPPacketOut(datapath = datapath, match = parser.OFPMatch(eth_src = dst), table_id = 0, instructions = [parser.OFPInstructionGotoTable(1)], priority = 3, hard_timeout=0, idle_timeout=0)
            
            self.send_pkt(datapath, data)
        
        # maches on destination address and forwaring to destination
        if self.MAC_TO_PORT[datapath.id].has_key(dst):
        
            out_port = self.MAC_TO_PORT[datapath.id][dst]
            
            self.send_flow(datapath = datapath, table_id = 1, match = parser.OFPMatch(eth_src = src), actions = [parser.OFPActionOutput(in_port)], priority = 3,)

            self.send_flow(datapath = datapath, table_id = 1, match = parser.OFPMatch(eth_src = dst), actions = [parser.OFPActionOutput(out_port)], priority = 3,)
            
            self.send_pkt(datapath, data,port = out_port)
        # if no learned, floods
        else:
            self.send_pkt(datapath, data, port = ofproto.OFPP_FLOOD)
