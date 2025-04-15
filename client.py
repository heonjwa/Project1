#!/usr/bin/env python3
import socket
import struct
import sys
import time
import random

class SocketClient:
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
        self.timeout = 3  # 3 seconds timeout for UDP
        self.retransmission_interval = 0.5  # 0.5 seconds for retransmissions

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
        # Format: !III means network byte order (big-endian), 3 unsigned ints
        # Format: !IIHh means network byte order, 2 unsigned ints, 1 unsigned short, 1 short
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

    def stage_a(self):
        """
        Implement Stage A of the protocol:
        - Send 'hello world' to the server via UDP
        - Receive num, len, udp_port, secretA from the server
        """
        print("Starting Stage A...")
        
        # Create UDP socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.settimeout(self.timeout)
        
        # Prepare the hello world message
        message = b'hello world\0'  # Don't forget the null terminator
        payload_len = len(message)
        
        # Create header (psecret = 0 for stage A, step = 1)
        header = self.create_header(payload_len, 0, 1)
        
        # Combine header and payload
        packet = header + message
        
        # Pad the packet to a 4-byte boundary
        packet = self.pad_to_4_byte_boundary(packet)
        
        try:
            # Send the packet to the server
            client_socket.sendto(packet, (self.server_name, self.port))
            print(f"Sent 'hello world' to {self.server_name}:{self.port}")
            
            # Receive response from server
            response, server_address = client_socket.recvfrom(1024)
            
            # Parse the response (should be 4 integers: num, len, udp_port, secretA)
            # Skip the 12-byte header (we don't need to parse it for the response)
            response_payload = response[12:]
            num, length, udp_port, secretA = struct.unpack("!IIII", response_payload)
            
            print(f"Received from server: num={num}, len={length}, udp_port={udp_port}, secretA={secretA}")
            
            # Store secretA for later use
            self.secrets['A'] = secretA
            
            return num, length, udp_port
        
        except socket.timeout:
            print("Timeout occurred during Stage A")
            sys.exit(1)
        finally:
            client_socket.close()

    def stage_b(self, num, length, udp_port):
        """
        Implement Stage B of the protocol:
        - Send num UDP packets to the server on udp_port
        - Each packet has a 4-byte id followed by 'len' bytes of zeros
        - Handle packet retransmission if not ACKed
        - Receive TCP port and secretB from server
        """
        print("Starting Stage B...")
        
        # Create UDP socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.settimeout(self.timeout)
        
        # Dictionary to track unacked packets
        unacked_packets = {i: True for i in range(num)}
        
        try:
            # Loop until all packets are acknowledged
            while unacked_packets:
                # Send all unacked packets
                for packet_id in list(unacked_packets.keys()):
                    # Create packet with id and zeros
                    packet_payload = struct.pack("!I", packet_id) + b'\x00' * length
                    payload_len = len(packet_payload)
                    
                    # Create header (using secretA, step = 1)
                    header = self.create_header(payload_len, self.secrets['A'], 1)
                    
                    # Combine header and payload
                    packet = header + packet_payload
                    
                    # Pad to 4-byte boundary
                    packet = self.pad_to_4_byte_boundary(packet)
                    
                    # Send the packet
                    client_socket.sendto(packet, (self.server_name, udp_port))
                    print(f"Sent packet {packet_id} to {self.server_name}:{udp_port}")
                
                # Wait for acknowledgments with timeout
                start_time = time.time()
                while time.time() - start_time < self.retransmission_interval and unacked_packets:
                    try:
                        # Set a short timeout for each receive attempt
                        client_socket.settimeout(0.1)
                        ack, server_address = client_socket.recvfrom(1024)
                        
                        # Parse the ACK (skip the 12-byte header)
                        ack_payload = ack[12:]
                        acked_id = struct.unpack("!I", ack_payload)[0]
                        
                        print(f"Received ACK for packet {acked_id}")
                        
                        # Remove the acknowledged packet from our unacked list
                        if acked_id in unacked_packets:
                            del unacked_packets[acked_id]
                        
                    except socket.timeout:
                        # Timeout for this receive attempt, continue trying
                        continue
            
            # All packets have been acknowledged
            print("All packets acknowledged!")
            
            # Now receive the TCP port and secretB
            response, server_address = client_socket.recvfrom(1024)
            
            # Parse the response (should be 2 integers: tcp_port, secretB)
            # Skip the 12-byte header
            response_payload = response[12:]
            tcp_port, secretB = struct.unpack("!II", response_payload)
            
            print(f"Received from server: tcp_port={tcp_port}, secretB={secretB}")
            
            # Store secretB for later use
            self.secrets['B'] = secretB
            
            return tcp_port
            
        except socket.timeout:
            print("Timeout occurred during Stage B")
            sys.exit(1)
        finally:
            client_socket.close()

    def stage_c_and_d(self, tcp_port):
        """
        Implement Stages C and D of the protocol:
        - Open TCP connection to the server on tcp_port
        - Receive num2, len2, secretC, and char c from server
        - Send num2 payloads of length len2 filled with char c
        - Receive secretD from server
        """
        print("Starting Stages C and D...")
        
        # Create TCP socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(self.timeout)
        
        try:
            # Connect to server
            client_socket.connect((self.server_name, tcp_port))
            print(f"Connected to {self.server_name}:{tcp_port} via TCP")
            
            # Create header for the TCP connection (using secretB, step = 1)
            header = self.create_header(0, self.secrets['B'], 1)
            
            # Send the header
            client_socket.sendall(header)
            
            # Receive the response from the server
            response = client_socket.recv(1024)
            
            # Parse the response (skip 12-byte header)
            response_payload = response[12:]
            
            # Extract num2, len2, secretC, and char c
            # Format: IIIB (3 unsigned ints, 1 unsigned byte)
            num2, len2, secretC = struct.unpack("!III", response_payload[:12])
            c = response_payload[12:13]  # Extract character c (1 byte)
            
            print(f"Received from server: num2={num2}, len2={len2}, secretC={secretC}, c={c}")
            
            # Store secretC for later use
            self.secrets['C'] = secretC
            
            # Now send num2 payloads with character c
            for i in range(num2):
                # Create payload filled with character c
                payload = c * len2
                payload_len = len(payload)
                
                # Create header (using secretC, step = 1)
                header = self.create_header(payload_len, self.secrets['C'], 1)
                
                # Combine header and payload
                packet = header + payload
                
                # Pad to 4-byte boundary
                packet = self.pad_to_4_byte_boundary(packet)
                
                # Send the packet
                client_socket.sendall(packet)
                print(f"Sent payload {i+1}/{num2}")
            
            # Receive secretD from server
            response = client_socket.recv(1024)
            
            # Parse the response (skip 12-byte header)
            response_payload = response[12:]
            secretD = struct.unpack("!I", response_payload)[0]
            
            print(f"Received from server: secretD={secretD}")
            
            # Store secretD
            self.secrets['D'] = secretD
            
        except socket.timeout:
            print("Timeout occurred during Stages C and D")
            sys.exit(1)
        except Exception as e:
            print(f"Error during Stages C and D: {e}")
            sys.exit(1)
        finally:
            client_socket.close()

    def run(self):
        """
        Run the entire client protocol
        """
        try:
            # Stage A: Send hello world, receive num, len, udp_port, secretA
            num, length, udp_port = self.stage_a()
            
            # Stage B: Send num packets, receive tcp_port, secretB
            tcp_port = self.stage_b(num, length, udp_port)
            
            # Stages C and D: TCP connection, send/receive data, get secretD
            self.stage_c_and_d(tcp_port)
            
            # Print all collected secrets
            print("\nCollected Secrets:")
            for stage, secret in self.secrets.items():
                print(f"Secret {stage}: {secret}")
            
            return True
        
        except Exception as e:
            print(f"Error: {e}")
            return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 client.py <server_name> <port>")
        sys.exit(1)
    
    server_name = sys.argv[1]
    port = sys.argv[2]
    
    # Get last 3 digits of student ID (replace with your student ID)
    student_id_last_three_digits = "123"  # Replace with your actual last 3 digits
    
    client = SocketClient(server_name, port, student_id_last_three_digits)
    client.run()

if __name__ == "__main__":
    main()