from controller import SDNApplication

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

#tm task=forwarding

class ppsdn20_uelmt_task11_reactive(SDNApplication):

    # initial SDN
    def __init__(self, *args, **kwargs):
        super(ppsdn20_uelmt_task11_reactive, self).__init__(*args, **kwargs)
        self.info("Task 1.1")
        
    # packet that needs to be send out of the switch
    def send_pkt(self, datapath, data, port = ofproto.OFPP_FLOOD):
        actions = [parser.OFPActionOutput(port)]
        out = parser.OFPPacketOut(
            datapath = datapath,
            actions = actions,
            in_port = datapath.ofproto.OFPP_CONTROLLER,
            data = data,
            buffer_id = ofproto.OFP_NO_BUFFER)
        datapath.send_msg(out)
        
    # The packet-in handler
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packe_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        pkt = packet.Packet(ev.msg.data)
        ip = pkt.get_protocol(ipv4.ipv4)
        
        # There is not an IPV4 packet.
        if ip is None:
            return
        ourN1_address_range = IPNetwork("11.0.0.0/8")
        ourN2_address_range = IPNetwork("22.0.0.0/8")
        
        # There is a packet whose destination is N2
        if IPAddress(ip.dst) in ourN2_address_range:
            match = parser.OFPMatch(
                eth_type = ether_types.ETH_TYPE_IP,
                ipv4_dst = ('22.0.0.0', '255.0.0.0')
            )
            # new flowtable set
            self.set_flow(datapath, match, [parser.OFPActionOutput(2)],
                priority = 1, hard_timeout = 0, idle_timeout = 0)
        
        # There is a packet whose destination is N1
        elif IPAddress(ip.dst) in ourN1_address_range:
            match = parser.OFPMatch(
                eth_type = ether_types.ETH_TYPE_IP,
                ipv4_dst = ('11.0.0.0', '255.0.0.0')
            )
            # new flowtable set
            self.set_flow(datapath, match, [parser.OFPActionOutput(1)],
            priority = 1, hard_timeout = 0, idle_timeout = 0)
        
        else:
            return
        
