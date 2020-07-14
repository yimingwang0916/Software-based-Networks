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
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub

from operator import attrgetter

#tm task=loadbalancer1

class ppsdn20_uelmt_loadbalancing_groups(CockpitApp):
    
    # initial sdn
    def __init__(self, *args, **kwargs):
        super(ppsdn20_uelmt_loadbalancing_groups, self).__init__(*args, **kwargs)
        self.info('Task 3.2')
        self.counter = 0
    
    # There is switch features handler
    # proactive flow rules
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):

        datapath = ev.msg.datapath
        # set group table
        self.send_group_mod(datapath)
        match = parser.OFPMatch(in_port = 1)
        actions = [parser.OFPActionGroup(group_id = 1)]
        self.program_flow(datapath, match, actions, priority = 10, hard_timeout = 0, idle_timeout = 0)

    # install group table
    def send_group_mod(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        actions_1 = [parser.OFPActionOutput(2)]
        actions_2 = [parser.OFPActionOutput(3)]
        weight1 = 100
        weight2 = 100
        
        # Add buckets
        buckets = [
                   # for network destination H2
                   parser.OFPBucket(weight1, actions = actions_1),
                   # for network destination H3
                   parser.OFPBucket(weight2, actions = actions_2)
                   ]
        
        group_id = 1
        req = parser.OFPGroupMod(datapath, ofproto.OFPGC_ADD,
                                 ofproto.OFPGT_SELECT, group_id, buckets)
        datapath.send_msg(req)
