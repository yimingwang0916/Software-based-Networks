import networkx
from cockpit import CockpitApp

# Import dependencies for Ryu
from ryu.base import app_manager
from ryu.lib import hub
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6, tcp


from netaddr import IPAddress, IPNetwork

#tm task=routing

H1 = ('11.0.0.0', '255.0.0.0')
H2 = ('22.0.0.0', '255.0.0.0')
H3 = ('33.0.0.0', '255.0.0.0')
H4 = ('44.0.0.0', '255.0.0.0')
HOST={H1:'H1', H2:'H2', H3:'H3', H4:'H4'}
IP_SPACE={v:k for k, v in HOST.items()}

# (src, dst, in_port, sid, out_port)
ROUTING_forwards = [
    # H1->4->S1->3->1->S4->5->H2
    (H1,H2,4,1,3), (H1,H2,1,4,5),
    # H1->4->S1->2->1->S3->5->1->S6->5->2->S8->4->H2
    (H1,H3,4,1,2), (H1,H3,1,3,5), (H1,H3,1,6,5), (H1,H3,2,8,4),
    # H1->4->S1->2->1->S3->5->1->S6->4->2->S7->4->H4
    (H1,H4,4,1,2), (H1,H4,1,3,5), (H1,H4,1,6,4), (H1,H4,2,7,4),
    # H2->5->S4->4->1->S8->4->H3
    (H2,H3,5,4,4), (H2,H3,1,8,4),
    # H2->5->S4->3->2->S6->4->2->S7->4->H4
    (H2,H4,5,4,3), (H2,H4,2,6,4), (H2,H4,2,7,4),
    # H3->4->S8->3->3->S7->4->H4
    (H3,H4,4,8,3), (H3,H4,3,7,4),
]

ROUTING_backwards = [(dst, src, out_port, sid, in_port) for (src, dst, in_port, sid, out_port) in ROUTING_forwards]
ROUTING_complete = ROUTING_forwards + ROUTING_backwards

class ppsdn20_uelmt_monitoring(CockpitApp):
    
    # initial sdn
    def __init__(self, *args, **kwargs):
        super(ppsdn20_uelmt_monitoring, self).__init__(*args, **kwargs)
        self.info('Task 2.1')
        self.datapaths = {}
        # initial the statistics information of the flow tables
        self.statistics = [{}]
        self.monitor_thread = hub.spawn(self._monitor)
        
    # There is packet-in handler
       # Should never be invoked sinve we use proactive flow programming.
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        pass

    def _request_stats(self, datapath):
    # Features request message
    # The controller sends a feature request to the switch upon session establishment.
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)
    
    def _monitor(self):
        while True:
            for datapath in self.datapaths.values():
                self._request_stats(datapath)
            # This message is handled by the Ryu framework, so the Ryu application do not need to process this typically.
            # Issue statistical information every 5 seconds
            hub.sleep(5)
            
    # There is switch features handler
    # proactive flow rules
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath
        self.statistics.append({})
        rules = [r for r in ROUTING_complete if r[3] == datapath.id]
        for r in rules:
            match = parser.OFPMatch(
                in_port = r[2],
                eth_type = ether_types.ETH_TYPE_IP,
                ipv4_src = r[0],
                ipv4_dst = r[1]
            )
            actions = [parser.OFPActionOutput(r[4])]
            self.program_flow(datapath, match, actions, priority=10)
    
    # Individual flow statistics reply message
    # The switch responds with this message to an individual flow statistics request.
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        # [sid] -> dict: (src,dst):statt
        for stat in [flow for flow in body if flow.priority == 10]:
            src = stat.match['ipv4_src'] # ('xx.0.0.0', '255.0.0.0')
            dst = stat.match['ipv4_dst']
            self.statistics[ev.msg.datapath.id][(src, dst)] = stat
        for stat in [flow for flow in body if flow.priority == 0]:
            # controller processed packet_count
            self.statistics[0][ev.msg.datapath.id] = stat
            
        # clear the output of the controller window
        print('\033c')
        
        print("*packets count*")
        print("---------------")
        # copy routing table
        l = ROUTING_complete[:]
        while l:
            # set a list
            raw = []
            # remove item of list
            src, dst, _, sid, _ = l.pop(0)
            raw.append(HOST[src]) # get the human-friendly name
            raw.append('{:<10}'.format((sid, self.statistics[sid][(src, dst)].packet_count)))
            # continue with the same path: src, dst are the same
            while l and (l[0][0] == src) and (l[0][1] == dst):
                _, _, _, sid, _ = l.pop(0)
                raw.append('{:<10}'.format((sid, self.statistics[sid][(src, dst)].packet_count)))
            raw.append(HOST[dst])
            print(" --> ".join(raw))
        
        print("---------------------------------------------------------------------")



