import networkx as nx
from cockpit import CockpitApp
from netaddr import IPAddress, IPNetwork

# Import dependencies for Ryuu
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

## Import graph libraryy
#from dijkstar import Graph, find_path

#tm task=routing

G=nx.Graph()
ROUTING_forwards = []

G.add_node(1, name = 's1',to_H1 = 4,
    to_s2 = 1, to_s3 = 2, to_s4 = 3)
G.add_edge(1,11)
G.add_edge(1,2)
G.add_edge(1,3)
G.add_edge(1,4)

G.add_node(2, name = 's2',
    to_s1 = 1, to_s3 = 2, to_s5 = 3)
G.add_edge(2,3)
G.add_edge(2,5)

G.add_node(3, name = 's3',
    to_s1 = 1, to_s2 = 2, to_s4 = 3, to_s5 = 4, to_s6 = 5)
G.add_edge(3,4)
G.add_edge(3,5)
G.add_edge(3,6)

G.add_node(4, name = 's4', to_H2 = 5,
    to_s1 = 1, to_s3 = 2, to_s6 = 3, to_s8 = 4)
G.add_edge(4,12)
G.add_edge(4,6)
G.add_edge(4,8)

G.add_node(5, name = 's5',
    to_s2 = 1, to_s3 = 2, to_s6 = 3, to_s7 = 4)
G.add_edge(5,6)
G.add_edge(5,7)

G.add_node(6, name='s6',
    to_s3 = 1, to_s4 = 2, to_s5 = 3, to_s7 = 4, to_s8 = 5)
G.add_edge(6,7)
G.add_edge(6,8)

G.add_node(7, name = 's7', to_H4 = 4,
    to_s5 = 1, to_s6 = 2, to_s8 = 3)
G.add_edge(7,14)
G.add_edge(7,8)

G.add_node(8, name = 's8', to_H3 = 4,
    to_s4 = 1, to_s6 = 2, to_s7 = 3)
G.add_edge(8,13)

G.add_node(11, name = 'H1',
    to_s1 = 4)
G.add_node(12, name = 'H2',
    to_s4 = 5)
G.add_node(13, name = 'H3',
    to_s8 = 4)
G.add_node(14, name = 'H4',
    to_s7 = 4)
    
# Hosts
H1 = ('11.0.0.0', '255.0.0.0')
H2 = ('22.0.0.0', '255.0.0.0')
H3 = ('33.0.0.0', '255.0.0.0')
H4 = ('44.0.0.0', '255.0.0.0')

HOST_NAME={
    H1:11,
    H2:12,
    H3:13,
    H4:14
}

IP_SPACE={v:k for k, v in HOST_NAME.items()}

class ppsdn20_uelmt_shortest_path(CockpitApp):
    
    def __init__(self, *args, **kwargs):
        super(ppsdn20_uelmt_shortest_path, self).__init__(*args, **kwargs)
        self.info('Task 2.2')
        self.datapaths = {}
        self.statistics = [{}]
        self.paths = {}
        # for debug
        self.stop = False
        self.counter = 0
    
    # There is switch handler for a new switch connecting to the controller
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        self.statistics.append({})
        
    # There is packet-in handler
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        # self.counter += 1
        # if self.counter >= 3:
        # avoid rolling too much times
        #    self.stop = True
        if self.stop == True:
            return
        path = None
        # first parser openflow protocol, get information from ev object
        msg = ev.msg
        data = msg.data
        datapath = msg.datapath
        
        parser = datapath.ofproto_parser
        
        pkt = packet.Packet(data)
        ip = pkt.get_protocol(ipv4.ipv4)
        if ip is None:
            return

        # get addr in the form of xx.0.0.0
        ip_src = IPNetwork(ip.src,8).network.format()
        # this should always in the form of (ip, mask)
        src = (ip_src, '255.0.0.0')
        ip_dst = IPNetwork(ip.dst,8).network.format()
        dst = (ip_dst, '255.0.0.0')
        
        # actual name in the graph
        host_src = HOST_NAME[src]
        host_dst = HOST_NAME[dst]
        
        new_path = nx.shortest_path(G, host_src, host_dst)
        path_only_switches = new_path[1:]

        for idx, node_id in enumerate(path_only_switches):
            if node_id  > 10:
                break;
            next_hop = path_only_switches[idx+1]
            key_for_switch_attribute = 'to_s%d' % next_hop
            switch_name = G.nodes[node_id]['name']
            try:
                output_port =  G.nodes[node_id][key_for_switch_attribute]
            except KeyError as e:
                if next_hop > 10:
                    # we know it is a host!
                    # use to_H instead!
                    hostkey = 'to_H%d' % (next_hop-10)
                    output_port =  G.nodes[node_id][hostkey]
                    self.send_pkt(self.datapaths[node_id], data, port = output_port)
                    
                else:
                    print("ERROR, next_hop is below 10 (should not happen)")
                    self.stop = True
            match = parser.OFPMatch(
                eth_type = ether_types.ETH_TYPE_IP,
                ipv4_src = ip.src,
                ipv4_dst = ip.dst
            )
            actions = [parser.OFPActionOutput(output_port)]
            self.program_flow(self.datapaths[node_id], match, actions, priority=10, hard_timeout=0, idle_timeout=0)

    def _monitor(self):
        while True:
            for datapath in self.datapaths.values():
                self._request_stats(datapath)
        # This message is handled by the Ryu framework, so the Ryu application do not need to process this typically.
        # Issue statistical information every 5 seconds
            hub.sleep(5)

    def _request_stats(self, datapath):
    # Features request message
    # The controller sends a feature request to the switch upon session establishment.
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

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

        # pretty printing
        print '\033c\r',
        print('packets count')
        print('*************')
        for host_src, host_dst in sorted(self.paths.keys()):
            buf = []
            path = self.paths[(host_src, host_dst)]
            src = IP_SPACE[host_src]
            dst = IP_SPACE[host_dst]

            buf.append(host_src)
            for sid in path[1:-1]: # exclude hosts, leave switch id only
                if (src, dst) in self.statistics[sid]:
                    buf.append('{:<10}'.format((sid, self.statistics[sid][(src, dst)].packet_count)))
                else:
                    buf.append('{:<10}'.format((sid, 0)))
            buf.append(host_dst)
            print(' >> '.join(buf))

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
                
