import socket
import threading
import time

class Node:
    def __init__(self, node_id, total_nodes):
        self.node_id = node_id
        self.total_nodes = total_nodes
        self.port = 5000 + node_id
        self.peers = [5000 + i for i in range(total_nodes) if i != node_id]
        self.clock = 0
        self.request_queue = []
        self.replies_received = 0
        self.booked_seats = set()
        self.requesting = False
        self.lock = threading.Lock()

    def start(self):
        threading.Thread(target=self.listen).start()
        time.sleep(1)
        self.input_loop()

    def input_loop(self):
        while True:
            command = input("Type 'book <seat_number>': ").strip().split()
            if len(command) == 2 and command[0].lower() == "book" and command[1].isdigit():
                seat = int(command[1])
                if seat in self.booked_seats:
                    print(f"[Node {self.node_id}] ❌ Seat {seat} already booked.")
                else:
                    self.request_critical_section(seat)
            else:
                print("❌ Invalid input. Try: book 1")

    def request_critical_section(self, seat):
        with self.lock:
            self.clock += 1
            timestamp = self.clock
            self.requesting = True
            self.request_queue.append((timestamp, self.node_id))
            self.replies_received = 0

        print(f"\n[Node {self.node_id}] 📢 Broadcasting REQUEST (timestamp={timestamp}) to all peers...")
        for peer_port in self.peers:
            self.send_message(peer_port, f"REQUEST:{timestamp}:{self.node_id}")

        # Wait for all replies
        while True:
            with self.lock:
                if self.replies_received == self.total_nodes - 1 and self.is_own_request_first():
                    break
            time.sleep(0.1)

        self.enter_critical_section(seat)

    def enter_critical_section(self, seat):
        print(f"\n[Node {self.node_id}] 🔒 Entered critical section!")
        time.sleep(1)

        with self.lock:
            if seat in self.booked_seats:
                print(f"[Node {self.node_id}] ❌ Seat {seat} already booked.")
            else:
                self.booked_seats.add(seat)
                print(f"[Node {self.node_id}] 🎟️ Successfully booked seat {seat}.")
                # Broadcast booking info
                for peer_port in self.peers:
                    self.send_message(peer_port, f"BOOKED:{seat}")

            self.requesting = False
            self.remove_own_request()
            self.replies_received = 0

            # Send deferred replies
            for req in sorted(self.request_queue):
                _, other_id = req
                if other_id != self.node_id:
                    self.send_message(5000 + other_id, f"REPLY:{self.node_id}")
                    print(f"[Node {self.node_id}] ✉️ Sent deferred REPLY to Node {other_id}")

    def listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind(("localhost", self.port))
            server_socket.listen()
            print(f"[Node {self.node_id}] 🚀 Listening on port {self.port}")

            while True:
                conn, _ = server_socket.accept()
                threading.Thread(target=self.handle_connection, args=(conn,)).start()

    def handle_connection(self, conn):
        with conn:
            data = conn.recv(1024).decode()
            if data.startswith("REQUEST:"):
                _, ts, sender_id = data.split(":")
                ts = int(ts)
                sender_id = int(sender_id)
                with self.lock:
                    self.clock = max(self.clock, ts) + 1
                    self.request_queue.append((ts, sender_id))
                    if not self.requesting or (ts, sender_id) < self.get_own_request():
                        self.send_message(5000 + sender_id, f"REPLY:{self.node_id}")
                        print(f"[Node {self.node_id}] ✅ Immediate REPLY sent to Node {sender_id}")
                    else:
                        print(f"[Node {self.node_id}] ⏳ Deferred REPLY to Node {sender_id}")

            elif data.startswith("REPLY:"):
                _, sender_id = data.split(":")
                with self.lock:
                    self.replies_received += 1
                    print(f"[Node {self.node_id}] ✅ Received REPLY from Node {sender_id} ({self.replies_received}/{self.total_nodes - 1})")

            elif data.startswith("BOOKED:"):
                _, seat = data.split(":")
                seat = int(seat)
                with self.lock:
                    if seat not in self.booked_seats:
                        self.booked_seats.add(seat)
                        print(f"[Node {self.node_id}] 📬 Seat {seat} marked as booked (sync from peer).")

    def send_message(self, port, message):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("localhost", port))
                s.sendall(message.encode())
        except:
            print(f"[Node {self.node_id}] ❌ Failed to send to port {port}")

    def is_own_request_first(self):
        return self.get_own_request() == min(self.request_queue)

    def get_own_request(self):
        for req in self.request_queue:
            if req[1] == self.node_id:
                return req
        return (float("inf"), self.node_id)

    def remove_own_request(self):
        self.request_queue = [req for req in self.request_queue if req[1] != self.node_id]

if __name__ == "__main__":
    node_id = int(input("Enter node ID: "))
    total_nodes = int(input("Enter total number of nodes: "))
    node = Node(node_id, total_nodes)
    node.start()
