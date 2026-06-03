import sys
import json
from router import Router
from packet import Packet

class DVrouter(Router):
    def __init__(self, addr, heartbeat_time):
        """Khởi tạo Router"""
        super().__init__(addr) # Đã fix chuẩn đét ở đây
        
        self.addr = addr
        self.heartbeat_time = heartbeat_time
        self.last_time = 0
        
        # Bảng định tuyến của chính mình: {đích_đến: chi_phí}
        self.distance_vector = {self.addr: 0}
        
        # Bảng chuyển tiếp để biết đi cổng nào: {đích_đến: port}
        self.forwarding_table = {self.addr: None}
        
        # Lưu thông tin các link trực tiếp kết nối với hàng xóm: {port: (hàng_xóm_addr, cost)}
        self.neighbors = {} 
        
        # Lưu distance vector của mấy thằng hàng xóm gửi sang: {hàng_xóm_addr: {đích_đến: cost}}
        self.neighbor_vectors = {}

    def send_dv_to_neighbors(self):
        """Gửi bảng distance vector của mình cho tất cả hàng xóm trực tiếp"""
        packet_content = json.dumps(self.distance_vector)
        for port in self.neighbors:
            pkt = Packet(Packet.ROUTING, self.addr, dst_addr=None, content=packet_content)
            self.send(port, pkt)

    def update_routing_table(self):
        """Tính toán lại đường đi ngắn nhất dựa trên thông tin từ các hàng xóm"""
        new_dv = {self.addr: 0}
        new_forwarding = {self.addr: None}
        
        for port, (neighbor_addr, link_cost) in self.neighbors.items():
            neighbor_dv = self.neighbor_vectors.get(neighbor_addr, {neighbor_addr: 0})
            for dst, dst_cost in neighbor_dv.items():
                total_cost = link_cost + dst_cost
                if total_cost >= 16:
                    total_cost = 16
                if dst not in new_dv or total_cost < new_dv[dst]:
                    new_dv[dst] = total_cost
                    new_forwarding[dst] = port

        if new_dv != self.distance_vector or new_forwarding != self.forwarding_table:
            self.distance_vector = new_dv
            self.forwarding_table = new_forwarding
            self.send_dv_to_neighbors()

    def handle_packet(self, port, packet):
        """Xử lý khi có gói tin bay vào router"""
        if packet.kind == Packet.ROUTING:
            sender = packet.src_addr
            received_dv = json.loads(packet.content)
            self.neighbor_vectors[sender] = received_dv
            self.update_routing_table()
            
        elif packet.kind == Packet.TRACEROUTE:
            dst = packet.dst_addr
            if dst in self.forwarding_table and self.forwarding_table[dst] is not None:
                out_port = self.forwarding_table[dst]
                if self.distance_vector.get(dst, 16) < 16:
                    self.send(out_port, packet)

    def handle_new_link(self, port, endpoint, cost):
        """Xử lý khi có một dây cáp mới cắm vào port của router"""
        self.neighbors[port] = (endpoint, cost)
        self.update_routing_table()

    def handle_remove_link(self, port):
        """Xử lý khi dây cáp ở port này bị rút ra hoặc bị đứt"""
        if port in self.neighbors:
            neighbor_addr, _ = self.neighbors[port]
            del self.neighbors[port]
            if neighbor_addr in self.neighbor_vectors:
                del self.neighbor_vectors[neighbor_addr]
        self.update_routing_table()

    def handle_time(self, time):
        """Hàm báo thức gửi lại bảng định kỳ"""
        if time - self.last_time >= self.heartbeat_time:
            self.last_time = time
            self.send_dv_to_neighbors()

    def __repr__(self):
        return f"DV [Addr: {self.addr}] Table: {str(self.distance_vector)}"