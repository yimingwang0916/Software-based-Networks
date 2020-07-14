from cockpit import CockpitApp
from netaddr import IPAddress, IPNetwork

# Import dependencies for Ryu
from ryu.base import app_manager
from ryu.lib import hub
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

#tm task=loadbalancer2

class ppsdn20_uelmt_loadbalancing_adaptive(CockpitApp):

    # initial sdn
    def __init__(self, *args, **kwargs):
        super(ppsdn20_uelmt_loadbalancing_adaptive, self).__init__(*args, **kwargs)
        self.info('Task 3.3')
        self.counter = 0
        self.datapaths = {}
        self.statistics = [0,0,0,0] # [p2_init, p3_init, p2_count, p3_count]
        self.monitor_thread = hub.spawn(self._monitor)

    # There is switch features handler
    # proactive flow rules
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath
        self.statistics.append({})

        # All packets with a destination address in the IP address range 22.0.0.0/8 are expected to arrive at host H2
        match = parser.OFPMatch(
            eth_type = ether_types.ETH_TYPE_IP,
            ipv4_src = ('11.0.0.0', '255.0.0.0'),
            ipv4_dst = ('22.0.0.0', '255.0.0.0')
        )
        actions = [parser.OFPActionOutput(2)]
        self.program_flow(datapath, match, actions, priority=20, hard_timeout=0, idle_timeout=0)

        # All packets with a destination address in the IP address range 33.0.0.0/8 are expected to arrive at host H3
        match = parser.OFPMatch(
            eth_type = ether_types.ETH_TYPE_IP,
            ipv4_src = ('11.0.0.0', '255.0.0.0'),
            ipv4_dst = ('33.0.0.0', '255.0.0.0')
        )
        actions = [parser.OFPActionOutput(3)]
        self.program_flow(datapath, match, actions, priority=20, hard_timeout=0, idle_timeout=0)

        # traffic destined to 44.0.0.0/8 should be forwarded in such a way that the overall traffic is evenly distributed among the two hosts H2 and H3
        # set group table
        self.send_group_mod(datapath)
        match = parser.OFPMatch(
            eth_type = ether_types.ETH_TYPE_IP,
            ipv4_src = ('11.0.0.0', '255.0.0.0'),
            ipv4_dst = ('44.0.0.0', '255.0.0.0')
        )
        actions = [parser.OFPActionGroup(group_id=1)]
        self.program_flow(datapath, match, actions, priority=10, hard_timeout=0, idle_timeout=0)

    def _monitor(self):
        while True:
            for datapath in self.datapaths.values():
                self._request_stats(datapath)
            # Issue statistical information every 1 second
            hub.sleep(1)

    def _request_stats(self, datapath):
        # req = parser.OFPFlowStatsRequest(datapath)
        req = parser.OFPPortStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        for stat in body:
            port_no = stat.port_no
            if port_no == 2:
                if self.statistics[0] == 0:
                    self.statistics[0] = stat.tx_packets
                    self.statistics[2] = stat.tx_packets
                else:
                    self.statistics[2] = stat.tx_packets
            if port_no == 3:
                if self.statistics[1] == 0:
                    self.statistics[1] = stat.tx_packets
                    self.statistics[3] = stat.tx_packets
                else:
                    self.statistics[3] = stat.tx_packets

        p2_tx = self.statistics[2] - self.statistics[0]
        p3_tx = self.statistics[3] - self.statistics[1]

        f = max(p2_tx+1, p3_tx+1)/float(min(p2_tx+1, p3_tx+1)) * 2.35 # magic number, yeah!
        w1, w2 = 100, int(100*f)
        if p2_tx - p3_tx > 400: # 400 diff is good enough
            self.send_group_mod_with_weight(self.datapaths[1], w1, w2)
            print p2_tx, p3_tx, w1, w2
        elif p3_tx - p2_tx > 400:
            self.send_group_mod_with_weight(self.datapaths[1], w2, w1)
            print p2_tx, p3_tx, w2, w1
        else:
            self.send_group_mod_with_weight(self.datapaths[1], w1, w1)
            print p2_tx, p3_tx, w1, w1

    # install group table
    def send_group_mod(self, datapath):
        fproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # H1 sends packets with IP destination addresses in the range 44.0.0.0/8 to either one of host H2 or H3
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

    def send_group_mod_with_weight(self, datapath, weight1, weight2):
        actions1 = [parser.OFPActionOutput(2)]
        actions2 = [parser.OFPActionOutput(3)]
        buckets = [parser.OFPBucket(weight1, actions=actions1),
                   parser.OFPBucket(weight2, actions=actions2)]
        group_id = 1
        req = parser.OFPGroupMod(datapath, ofproto.OFPGC_MODIFY,
                                 ofproto.OFPGT_SELECT, group_id, buckets)
        datapath.send_msg(req)
