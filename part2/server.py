import socket
import struct
import sys
import random
import threading
import logging

TIMEOUT = 3
STUDENT_ID = "056"  # Replace with your own

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def pad_to_4_byte_boundary(data):
    padding_needed = (4 - (len(data) % 4)) % 4
    return data + b'\x00' * padding_needed

def create_header(payload_len, psecret, step):
  return struct.pack("!IIHH", payload_len, psecret, step, int(STUDENT_ID))

def verify_header(p_secret, header, length):         
    payload_len, psecret, step, student_id = struct.unpack("!IIHH", header)
    return psecret == p_secret and step == 1 and payload_len == length



class ClientHandler(threading.Thread):
    def __init__(self, client_addr, secret_a, num, length, udp_port, server_name):
        super().__init__()
        self.client_addr = client_addr
        self.secret_a = secret_a
        self.num = num
        self.length = length
        self.udp_port = udp_port
        self.tcp_port = random.randint(20000, 30000)
        self.secretB = random.randint(1000, 9999)
        self.secretC = random.randint(1000, 9999)
        self.secretD = random.randint(1000, 9999)
        self.server_name = server_name

    def run(self):
        try:
            logging.info(f'Client {self.client_addr} | Stage B start on UDP {self.udp_port}')
            self.handle_stage_b()

            logging.info(f'Client {self.client_addr} | Stage C start on TCP {self.tcp_port}')
            self.handle_stage_c()

            logging.info(f'Client {self.client_addr} | Stage D start')
            self.handle_stage_d()

            logging.info(f'Client {self.client_addr} | Session complete!')

        except Exception as e:
            logging.warning(f'Client {self.client_addr} | Error: {e}')

    def handle_stage_b(self):
        # TODO: Create UDP socket on self.udp_port
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((self.server_name, self.udp_port))

        curr_packet = 0
        while curr_packet < self.num:
            try:
                data, addr = udp_socket.recvfrom(1024)
                udp_socket.settimeout(TIMEOUT)
                # TODO: Receive self.num packets, verify IDs and len
                # Verify length = length + 4
                # Verify header
                if not verify_header(self.secret_a, data[:12], self.length + 4):
                    logging.warning(f"Invalid header from {addr}")
                    curr_packet = 0
                    continue

                payload = data[12:]
                packet_num = struct.unpack("!I", payload[:4])[0]
                if packet_num != curr_packet:
                    logging.warning(f"Packet number mismatch: expected {curr_packet}, got {packet_num}")
                    curr_packet = 0
                    continue

                rest_of_payload = payload[4:]
                if rest_of_payload != bytes(len(rest_of_payload)):
                    logging.warning(f"Non-zero data found in payload from {addr}")
                    curr_packet = 0
                    continue

                rand_num = random.randint(0, 100)
                if rand_num < 100:
                    header = create_header(4, self.secret_a, 2)
                    ack_payload = struct.pack("!I", curr_packet) 
                    ack_packet = header + ack_payload
                    udp_socket.sendto(ack_packet, self.client_addr)
                    logging.info(f"Sent ACK for packet {curr_packet} to {self.client_addr}")

            except socket.timeout:
                logging.warning("Main server timed out waiting for packets.")
                curr_packet = 0
            except Exception as e:
                logging.error(f"Server error: {e}")
                break
            
        header = create_header(8, self.secret_b, 2)
        ack_payload = struct.pack("!II", self.tcp_port, self.secretB)
        ack_packet = header + ack_payload
        ack_packet = pad_to_4_byte_boundary(ack_packet)
        udp_socket.sendto(ack_packet, self.client_addr)
        # TODO: Send acks randomly, ensure 1+ is dropped
        # TODO: Send self.tcp_port and self.secretB
        pass

    def handle_stage_c(self):
        # TODO: Accept TCP connection on self.tcp_port
        # TODO: Send num2, len2, secretC, c
        pass

    def handle_stage_d(self):
        # TODO: Receive num2 payloads of char c
        # TODO: Respond with secretD
        pass

def start_server(server_name, port):
    logging.info(f'Starting server on UDP port {port}')
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((server_name, port))

    while True:
        try:
            data, addr = udp_socket.recvfrom(1024)
            udp_socket.settimeout(TIMEOUT)

            # Probably wrong
            payload = data[12:]
            message = payload.decode('utf-8').rstrip('\x00')
            if message != "hello world":
                logging.warning(f"Invalid initial message from {addr}")
                continue

            # Generate parameters
            num = random.randint(5, 25)
            length = random.randint(5, 50)
            udp_port = random.randint(1024, 65535)
            secret_a = random.randint(10000000, 99999999)

            logging.info(f'Client {addr} | Received hello world. Spawning handler...')

            # Respond to client
            payload = struct.pack('!IIII', num, length, udp_port, secret_a)
            payload_len = len(payload)
            padded_payload = pad_to_4_byte_boundary(payload)

            header = create_header(payload_len, secret_a, 2)

            packet = header + padded_payload

            udp_socket.sendto(packet, addr)

            # Start client handler thread
            handler = ClientHandler(addr, secret_a, num, length, udp_port, server_name)
            handler.start()

        except socket.timeout:
            logging.warning("Main server timed out waiting for packets.")
        except Exception as e:
            logging.error(f"Server error: {e}")
            break

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 server.py <server_name> <port>")
        sys.exit(1)

    server_name = sys.argv[1]
    port = int(sys.argv[2])
    start_server(server_name, port)

if __name__ == "__main__":
    main()
