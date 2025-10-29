if __name__ == "__main__":
    nodes = {
        0: ('localhost', 5000),
        1: ('localhost', 5001),
        2: ('localhost', 5002),
    }
    current_id = int(input("Enter Node ID (0/1/2): "))
    other_peers = [addr for i, addr in nodes.items() if i != current_id]
    
    node = Node(current_id, nodes[current_id][1], other_peers)

    while True:
        cmd = input("Type 'book' to request a seat: ")
        if cmd.strip() == 'book':
            node.request_booking()
