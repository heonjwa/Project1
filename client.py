#!/usr/bin/env python3
import socket
import struct
import sys
import time
import random
import threading

class ClientHandler:
    def __init__(self, client_address, student_id_last_three_digits):
        self.client_address = client_address
        self.student_id = int(student_id_last_three_digits)
        self.timeout = 3  # 3 seconds timeout
        
        # Generate random secrets for each stage
        self.secretA = random.randint(1000, 9999)
        self.secretB = random.randint(1000, 9999)
        self.secretC = random.randint(1000, 9999)
        self.secretD = random.randint(1000, 9999)
        
        # UDP socket for stage A
        self.udp_socket = None
        
        # UDP socket for stage B
        self.stage_b_socket = None
        self.udp_port = random.randint(10000, 60000)  # Random port for stage B
        
        # TCP socket for stages C and D
        self.tcp_socket = None
        self.tcp_port = random.randint(10000, 60000)  # Random port for TCP connection
        
        print(f"New client: {client_address}, UDP port: {self.udp_port}, TCP port: {self.tcp_port}")
        print(f"Secrets: A={self.secretA}, B={self.secretB}, C={self.secretC}, D={self.secretD}")

    def create_header(self, payload_len, psecret, step):
        """
        Create a packet header as specified in the protocol
        
        Args:
            payload_len: Length of the payload (4 bytes)
            psecret: Secret from previous stage (4 bytes)
            step: Current protocol step (2 bytes)
            
        Returns:
            Packed header as bytes
        """
        return struct.pack("!IIHH", payload_len, psecret, step, self.student_id)

    def pad_to_4_byte_boundary(self, data):
        """
        Pad the data to a 4-byte boundary as required by the protocol
        
        Args:
            data: Data to be padded
            
        Returns:
            Padded data as bytes
        """
        padding_needed = (4 - (len(data) % 4)) % 4
        return data + b'\x00' * padding_needed

    def verify_header(self, packet, expected_psecret, expected_step):
        """
        Verify the header of a packet
        
        Args:
            packet: The packet to verify
            expected_psecret: Expected previous secret
            expected_step: Expected step number
            
        Returns:
            (payload_len, is_valid, client_student_id)
        """
        if len(packet) < 12:
            print("Packet too short to contain a header")
            return 0, False, 0
        
        # Unpack header
        payload_len, psecret, step, client_student_id = struct.unpack("!IIHH", packet[:12])
        
        # Verify psecret and step
        if psecret != expected_psecret:
            print(f"Invalid psecret: expected {expected_psecret}, got {psecret}")
            return payload_len, False, client_student_id
        
        if step != expected_step:
            print(f"Invalid step: expected {expected_step}, got {step}")
            return payload_len, False, client_student_id
        
        return payload_len, True, client_student_id

    def stage_a(self, initial_socket, initial_port):
        """
        Handle Stage A of the protocol:
        - Receive 'hello world' from client via UDP
        - Send num, len, udp_port, secretA to client
        """
        print(f"Starting Stage A for client {self.client_address}")
        
        try:
            # Use the provided socket for the initial message
            self.udp_socket = initial_socket
            
            # Parameters for Stage B
            num = random.randint(5, 10)  # Number of packets for Stage B
            length = random.randint(10, 20)  # Length of payload for Stage B
            
            # Create response (num, len, udp_port, secretA)
            response_payload = struct.pack("!IIII", num, length, self.udp_port, self.secretA)
            payload_len = len(response_payload)
            
            # Create header (psecret = 0 for stage A, step = 2)
            header = self.create_header(payload_len, 0, 2)
            
            # Combine header and payload
            packet = header + response_payload
            
            # Pad to 4-byte boundary
            packet = self.pad_to_4_byte_boundary(packet)
            
            # Send the packet to the client
            self.udp_socket.sendto(packet, self.client_address)
            print(f"Sent stage A response to {self.client_address}")
            
            return num, length
            
        except Exception as e:
            print(f"Error in Stage A: {e}")
            return None, None

    def stage_b(self, num, length):
        """
        Handle Stage B of the protocol:
        - Create UDP socket on udp_port
        - Receive num packets from client
        - Send ACK for each packet (with random drops)
        - Send TCP port and secretB to client
        """
        print(f"Starting Stage B for client {self.client_address}")
        
        # Create UDP socket for Stage B
        self.stage_b_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.stage_b_socket.settimeout(self.timeout)
        self.stage_b_socket.bind(('0.0.0.0', self.udp_port))
        
        received_packets = set()
        
        try:
            while len(received_packets) < num:
                try:
                    # Receive packet
                    packet, client_addr = self.stage_b_socket.recvfrom(1024)
                    
                    # Verify header (psecret should be secretA, step = 1)
                    payload_len, is_valid, client_student_id = self.verify_header(packet, self.secretA, 1)
                    
                    if not is_valid:
                        print("Invalid header, closing connection")
                        return False
                    
                    # Extract packet_id (first 4 bytes of payload)
                    packet_payload = packet[12:12+payload_len]
                    if len(packet_payload) < 4:
                        print("Packet payload too short")
                        return False
                    
                    packet_id = struct.unpack("!I", packet_payload[:4])[0]
                    
                    # Verify packet_id is in range
                    if packet_id >= num:
                        print(f"Invalid packet_id: {packet_id} (should be < {num})")
                        return False
                    
                    # Verify payload length
                    expected_len = 4 + length  # packet_id (4 bytes) + len bytes of zeros
                    if len(packet_payload) != expected_len:
                        print(f"Invalid payload length: expected {expected_len}, got {len(packet_payload)}")
                        return False
                    
                    # Verify zeros in payload
                    zeros = packet_payload[4:]
                    if zeros != b'\x00' * length:
                        print("Payload doesn't contain all zeros")
                        return False
                    
                    print(f"Received valid packet {packet_id} from client")
                    
                    # Add packet to received set
                    received_packets.add(packet_id)
                    
                    # Randomly decide whether to ACK (80% chance)
                    if random.random() < 0.8:
                        # Create ACK packet
                        ack_payload = struct.pack("!I", packet_id)
                        ack_payload_len = len(ack_payload)
                        
                        # Create header (psecret = secretA, step = 2)
                        ack_header = self.create_header(ack_payload_len, self.secretA, 2)
                        
                        # Combine header and payload
                        ack_packet = ack_header + ack_payload
                        
                        # Pad to 4-byte boundary
                        ack_packet = self.pad_to_4_byte_boundary(ack_packet)
                        
                        # Send ACK
                        self.stage_b_socket.sendto(ack_packet, client_addr)
                        print(f"Sent ACK for packet {packet_id}")
                    else:
                        print(f"Deliberately not ACKing packet {packet_id}")
                
                except socket.timeout:
                    print("Timeout in Stage B")
                    return False
            
            # All packets received, send TCP port and secretB
            response_payload = struct.pack("!II", self.tcp_port, self.secretB)
            payload_len = len(response_payload)
            
            # Create header (psecret = secretA, step = 2)
            header = self.create_header(payload_len, self.secretA, 2)
            
            # Combine header and payload
            packet = header + response_payload
            
            # Pad to 4-byte boundary
            packet = self.pad_to_4_byte_boundary(packet)
            
            # Send the packet to the client
            self.stage_b_socket.sendto(packet, client_addr)
            print(f"Sent TCP port {self.tcp_port} and secretB {self.secretB} to client")
            
            return True
            
        except Exception as e:
            print(f"Error in Stage B: {e}")
            return False
        finally:
            if self.stage_b_socket:
                self.stage_b_socket.close()

    def stages_c_and_d(self):
        """
        Handle Stages C and D of the protocol:
        - Create TCP socket and wait for client connection
        - Send num2, len2, secretC, and char c to client
        - Receive num2 payloads of length len2 filled with char c
        - Send secretD to client
        """
        print(f"Starting Stages C and D for client {self.client_address}")
        
        # Create TCP socket
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.settimeout(self.timeout)
        self.tcp_socket.bind(('0.0.0.0', self.tcp_port))
        self.tcp_socket.listen(1)
        
        try:
            # Accept connection from client
            client_socket, client_addr = self.tcp_socket.accept()
            client_socket.settimeout(self.timeout)
            print(f"Accepted TCP connection from {client_addr}")
            
            # Receive initial header from client
            header = client_socket.recv(12)
            if len(header) != 12:
                print("Invalid header length")
                return False
            
            # Verify header (psecret should be secretB, step = 1)
            payload_len, is_valid, client_student_id = self.verify_header(header, self.secretB, 1)
            
            if not is_valid:
                print("Invalid header, closing connection")
                client_socket.close()
                return False
            
            # Parameters for Stage D
            num2 = random.randint(3, 7)
            len2 = random.randint(10, 30)
            c = bytes([random.randint(65, 90)])  # Random ASCII character (A-Z)
            
            # Create response (num2, len2, secretC, c)
            response_payload = struct.pack("!III", num2, len2, self.secretC) + c
            payload_len = len(response_payload)
            
            # Create header (psecret = secretB, step = 2)
            header = self.create_header(payload_len, self.secretB, 2)
            
            # Combine header and payload
            packet = header + response_payload
            
            # Pad to 4-byte boundary
            packet = self.pad_to_4_byte_boundary(packet)
            
            # Send the packet to the client
            client_socket.sendall(packet)
            print(f"Sent num2={num2}, len2={len2}, secretC={self.secretC}, c={c} to client")
            
            # Receive num2 payloads from client
            for i in range(num2):
                # First get the header
                header = client_socket.recv(12)
                if len(header) != 12:
                    print(f"Invalid header length in payload {i+1}")
                    client_socket.close()
                    return False
                
                # Verify header (psecret should be secretC, step = 1)
                payload_len, is_valid, client_student_id = self.verify_header(header, self.secretC, 1)
                
                if not is_valid:
                    print(f"Invalid header in payload {i+1}, closing connection")
                    client_socket.close()
                    return False
                
                # Calculate how many bytes to receive (including padding)
                padded_len = payload_len + ((4 - (payload_len % 4)) % 4)
                
                # Receive payload
                payload = b''
                bytes_received = 0
                while bytes_received < padded_len:
                    chunk = client_socket.recv(padded_len - bytes_received)
                    if not chunk:
                        print(f"Connection closed during payload {i+1}")
                        client_socket.close()
                        return False
                    payload += chunk
                    bytes_received += len(chunk)
                
                # Verify payload (should be len2 bytes of character c)
                if len(payload) < payload_len:
                    print(f"Payload {i+1} too short")
                    client_socket.close()
                    return False
                
                # Only check the non-padding part
                payload = payload[:payload_len]
                
                if payload != c * len2:
                    print(f"Payload {i+1} doesn't contain all {c}")
                    client_socket.close()
                    return False
                
                print(f"Received valid payload {i+1}/{num2} from client")
            
            # All payloads received, send secretD
            response_payload = struct.pack("!I", self.secretD)
            payload_len = len(response_payload)
            
            # Create header (psecret = secretC, step = 2)
            header = self.create_header(payload_len, self.secretC, 2)
            
            # Combine header and payload
            packet = header + response_payload
            
            # Pad to 4-byte boundary
            packet = self.pad_to_4_byte_boundary(packet)
            
            # Send the packet to the client
            client_socket.sendall(packet)
            print(f"Sent secretD {self.secretD} to client")
            
            # Close socket
            client_socket.close()
            
            return True
            
        except socket.timeout:
            print("Timeout in Stages C and D")
            return False
        except Exception as e:
            print(f"Error in Stages C and D: {e}")
            return False
        finally:
            if self.tcp_socket:
                self.tcp_socket.close()

    def handle_client(self, initial_socket, initial_port):
        """
        Handle all stages of the protocol for a client
        """
        try:
            # First, verify the "hello world" message
            packet, _ = initial_socket.recvfrom(1024)
            
            # Verify header (psecret should be 0, step = 1)
            payload_len, is_valid, client_student_id = self.verify_header(packet, 0, 1)
            
            if not is_valid:
                print("Invalid header in initial message, closing connection")
                return
            
            # Extract "hello world" string from payload
            hello_msg = packet[12:12+payload_len]
            expected_msg = b'hello world\0'
            
            if hello_msg != expected_msg:
                print(f"Invalid hello message: expected '{expected_msg}', got '{hello_msg}'")
                return
            
            print("Received valid 'hello world' message from client")
            
            # Handle Stage A (using the same socket)
            num, length = self.stage_a(initial_socket, initial_port)
            if num is None or length is None:
                return
            
            # Handle Stage B
            if not self.stage_b(num, length):
                return
            
            # Handle Stages C and D
            if not self.stages_c_and_d():
                return
            
            print(f"Successfully completed all stages for client {self.client_address}")
            
        except Exception as e:
            print(f"Error handling client: {e}")

class SocketServer:
    def __init__(self, server_name, port, student_id_last_three_digits):
        self.server_name = server_name
        self.port = int(port)
        self.student_id = student_id_last_three_digits
        
        # UDP socket for initial connections
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.server_name, self.port))
        
        print(f"Server started on {self.server_name}:{self.port}")
        
    def run(self):
        """
        Run the server, listening for client connections
        """
        try:
            while True:
                # Wait for initial UDP packet from client
                packet, client_address = self.udp_socket.recvfrom(1024)
                print(f"Received initial packet from {client_address}")
                
                # Create a new socket for this client to avoid blocking other connections
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                client_socket.bind(('0.0.0.0', 0))  # Bind to random port
                _, client_port = client_socket.getsockname()
                
                # Create a new thread to handle this client
                client_handler = ClientHandler(client_address, self.student_id)
                
                # Create and start a new thread for this client
                client_thread = threading.Thread(
                    target=client_handler.handle_client,
                    args=(self.udp_socket, self.port)
                )
                client_thread.daemon = True
                client_thread.start()
                
                print(f"Started new thread for client {client_address}")
                
        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            if self.udp_socket:
                self.udp_socket.close()

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 server.py <server_name> <port>")
        sys.exit(1)
    
    server_name = sys.argv[1]
    port = sys.argv[2]
    
    # Get last 3 digits of student ID (replace with your actual last 3 digits)
    student_id_last_three_digits = "123"  # Replace with your actual last 3 digits
    
    server = SocketServer(server_name, port, student_id_last_three_digits)
    server.run()

if __name__ == "__main__":
    main()