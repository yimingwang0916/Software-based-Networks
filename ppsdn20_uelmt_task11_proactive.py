from controller import SDNApplication
from cockpit import CockpitApp

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

#tm task=forwarding

# port 1 = N1 (11.0.0.0/8)
# port 2 = N2 (22.0.0.0/8)

class ppsdn20_uelmt_task11_proactive(SDNApplication):
    
    proactive_flows = [
        (2, ('11.0.0.0', '255.0.0.0'), 3, 'ipv4_src'),
        # ipv4_src = match_field
        (1, ('22.0.0.0', '255.0.0.0'), 3, 'ipv4_src'),
    ]
    
    # initial SDN
    def __init__(self, *args, **kwargs):
        super（ppsdn20_uelmt_task11_proactive, self).__init__(*args, **kwargs)
        self.info("Task1.1")
        self.counter = 0
        self.packets_by_ip = dict()

    # flowtable set beforehand
    def install_flow(self, dp, port, ip, priority, match_field):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        
        match = parser.OFPMatch(**{
            'eth_type' : ether_types.ETH_TYPE_IP,
            match_field : ip}
        )
        action = parser.OFPActionOutput(port = port, max_len = 65535)
        
        # Flow rule's encapsulation
        # The OpenFlow message we send to the switch to install a flow
        msg = parser.OFPFlowMod(
            dp,
            match = match,
            # Here we embed the action in the instruction
            instructions = [parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS,
                [action]
            )],
            priority = priority
        )
        
        # send new flow rule to the switches
        dp.send_msg(msg)
        
    # The switch features handler
    # The proper place to do stuff in advance
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch(self, ev):
        dp = ev.msg.datapath
            
        # Install some static flows to achieve our goal...
        for port, ip, priority, match_field in self.proactive_flows:
            self.install_flow(dp, port, ip, priority, match_field)

    # There is packet-in handler
    # Should never be invoked sinve we use proactive flow programming.
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        self.counter += 1
        print('.. total packet_in messages received: {}').format(self.counter)
        pkt = packet.Packet(ev.msg.data)
        self.send_pkt(ev.msg.datapath, pkt.data)
        
        
    
