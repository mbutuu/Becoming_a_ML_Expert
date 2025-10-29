import socket
import threading
import json
import time

class Node:
    def __init__(self, node_id, port, peers):
        self.node_id = node_id
        self.port = port
        self.peers = peers  # [(host, port), ...]
        self.timestamp = 0
        self.requesting = False
        self.reply_count = 0
        self.deferred = []
        self.booked_seats = []
        threading.Thread(target=self.start_server, daemon=True).start()

    def start_server(self):
        s = socket.socket()
        s.bind(('localhost', self.port))
        s.listen()
        print(f"[Node {self.node_id}] Listening on port {self.port}")
        while True:
            conn, _ = s.accept()
            data = conn.recv(1024).decode()
            if data:
                msg = json.loads(data)
                threading.Thread(target=self.handle_message, args=(msg,), daemon=True).start()
            conn.close()

    def send_message(self, peer, msg):
        try:
            s = socket.socket()
            s.connect(peer)
            s.send(json.dumps(msg).encode())
            s.close()
        except Exception as e:
            print(f"[Node {self.node_id}] Failed to send to {peer}: {e}")

    def broadcast_request(self):
        self.timestamp = time.time()
        self.requesting = True
        self.reply_count = 0
        print(f"[Node {self.node_id}] Broadcasting REQUEST...")
        for peer in self.peers:
            self.send_message(peer, {
                'type': 'REQUEST',
                'timestamp': self.timestamp,
                'from': self.node_id
            })

    def handle_message(self, msg):
        msg_type = msg['type']
        if msg_type == 'REQUEST':
            their_time = msg['timestamp']
            their_id = msg['from']
            if (not self.requesting) or ((self.timestamp, self.node_id) > (their_time, their_id)):
                self.send_message(self.peers[their_id], {'type': 'REPLY'})
            else:
                self.deferred.append(their_id)
        elif msg_type == 'REPLY':
            self.reply_count += 1
            if self.reply_count == len(self.peers):
                self.enter_critical_section()

    def enter_critical_section(self):
        print(f"[Node {self.node_id}] Entered critical section!")
        seat = input("Enter seat number to book: ")
        if seat not in self.booked_seats:
            self.booked_seats.append(seat)
            print(f"[Node {self.node_id}] Booked seat {seat}")
        else:
            print(f"[Node {self.node_id}] Seat already booked.")
        self.release_critical_section()

    def release_critical_section(self):
        print(f"[Node {self.node_id}] Exiting critical section.")
        self.requesting = False
        for node_id in self.deferred:
            self.send_message(self.peers[node_id], {'type': 'REPLY'})
        self.deferred.clear()

    def request_booking(self):
        self.broadcast_request()


# --- MAIN SCRIPT ---
if __name__ == "__main__":
    nodes = {
        0: ('localhost', 5000),
        1: ('localhost', 5001),
        2: ('localhost', 5002),
    }

    current_id = int(input("Enter Node ID (0/1/2): "))
    current_port = nodes[current_id][1]
    other_peers = [nodes[i] for i in nodes if i != current_id]

    node = Node(current_id, current_port, other_peers)

    while True:
        cmd = input("Type 'book' to request a seat: ")
        if cmd.strip().lower() == "book":
            node.request_booking()
