import socket
import struct
import sys
import random
import threading

class SocketServer:
    def __init__(self, server_name, port, student_id_last_three_digits):
        self.server_name = server_name
        self.port = int(port)
        self.student_id = int(student_id_last_three_digits)
        self.secrets = {
            'A': None,
            'B': None,
            'C': None,
            'D': None
        }

    def create_header(self, payload_len, psecret, step):
        return struct.pack("!IIHH", payload_len, psecret, step, self.student_id)

    def pad_to_4_byte_boundary(self, data):
        padding_needed = (4 - (len(data) % 4)) % 4
        return data + b'\x00' * padding_needed

    def handle_udp_client(self, data, client_addr, sock):
        try:
            # Strip off header: not used in stage A
            payload = data[12:]
            message = payload.decode('utf-8').rstrip('\x00')

            if message != "hello world":
                print(f"[REJECTED] Invalid message from {client_addr}: {message}")
                return

            print(f"[STAGE A] Valid message from {client_addr}: {message}")

            # Generate values for Stage A
            num = random.randint(5, 25)
            length = random.randint(5, 50)
            udp_port = random.randint(20000, 60000)
            secret_a = random.randint(10000, 2**32 - 1)
            self.secrets['A'] = secret_a

            # Pack payload
            payload = struct.pack("!IIII", num, length, udp_port, secret_a)
            padded_payload = self.pad_to_4_byte_boundary(payload)

            # Header (psecret = 0 for stage A, step = 1)
            header = self.create_header(len(payload), 0, 1)
            response = header + padded_payload

            # Send response back to the client
            sock.sendto(response, client_addr)
            print(f"[STAGE A] Sent response to {client_addr}")
            print(f"  num = {num}, len = {length}, udp_port = {udp_port}, secretA = {secret_a}")

            # Optionally: open a new socket on udp_port for Stage B
            # This can be implemented in stage_b()
        except Exception as e:
            print(f"[ERROR] Error handling client {client_addr}: {e}")

    def stage_a(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.server_name, self.port))
        print(f"[SERVER] UDP socket bound to {self.server_name}:{self.port}")

        while True:
            try:
                data, client_addr = sock.recvfrom(1024)
                thread = threading.Thread(target=self.handle_udp_client, args=(data, client_addr, sock))
                thread.start()
            except socket.timeout:
                print("[TIMEOUT] No client message received.")
            except KeyboardInterrupt:
                print("\n[SERVER] Shutting down.")
                break

    def run(self):
        try:
            self.stage_a()
        except Exception as e:
            print(f"[ERROR] {e}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 server.py <server_name> <port>")
        sys.exit(1)

    server_name = sys.argv[1]
    port = sys.argv[2]
    student_id_last_three_digits = "056"  # Replace with your own

    server = SocketServer(server_name, port, student_id_last_three_digits)
    server.run()

if __name__ == "__main__":
    main()
