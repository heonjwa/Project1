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
      return struct.pack("!IIHH", payload_len, psecret, step, self.student_id)

  def pad_to_4_byte_boundary(self, data):
      padding_needed = (4 - (len(data) % 4))
      return data + b'\x00' * padding_needed

  def stage_a(self):
      print("Starting Stage A...")
      
      client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      client_socket.settimeout(self.timeout)
      
      message = b'hello world\0'
      payload_len = len(message)
      
      header = self.create_header(payload_len, 0, 1)

      packet = header + message
      
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
    print(f"Starting Stage B... Sending {num} packets with {length} zero bytes to port {udp_port}")
    
    # Create a UDP socket for Stage B
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    for packet_id in range(num):
        # Set timeout for this packet's ACK
        client_socket.settimeout(0.5)
        
        # Create the packet ID bytes
        packet_id_bytes = struct.pack("!I", packet_id)
        
        # Create zeros payload exactly as length specifies
        zeros = b'\x00' * length
        
        # Payload is packet_id followed by zeros
        payload = packet_id_bytes + zeros
        
        # Create header with secretA, step=1, and correct payload length
        header = self.create_header(len(payload), self.secrets['A'], 1)
        
        # Create complete packet
        packet = header + payload
        
        # Ensure packet is padded to 4-byte boundary if needed
        packet = self.pad_to_4_byte_boundary(packet)
        
        # Debug information
        print(f"Packet {packet_id}: header={header.hex()}, payload_len={len(payload)}")
        
        # Send and retry until ACK received
        acked = False
        retries = 0
        max_retries = 10
        
        while not acked and retries < max_retries:
            try:
                # Send packet
                client_socket.sendto(packet, (self.server_name, udp_port))
                print(f"Sent packet {packet_id} to {self.server_name}:{udp_port}")
                
                # Wait for response
                response, server_address = client_socket.recvfrom(1024)
                print(f"Received response: {response.hex()}")
                
                # Skip header (12 bytes)
                response_payload = response[12:]
                
                # Check if it's an ACK (4 bytes)
                if len(response_payload) == 4:
                    acked_id = struct.unpack("!I", response_payload)[0]
                    print(f"Received ACK for packet ID {acked_id}")
                    
                    if acked_id == packet_id:
                        acked = True
                        print(f"Successfully ACKed packet {packet_id}")
                    else:
                        print(f"Received ACK for packet {acked_id}, expecting {packet_id}")
                
                # Check if it's the final response (8 bytes)
                elif len(response_payload) == 8:
                    tcp_port, secretB = struct.unpack("!II", response_payload)
                    print(f"Received TCP port {tcp_port} and secretB {secretB}")
                    self.secrets['B'] = secretB
                    return tcp_port
                
                else:
                    print(f"Unexpected payload: {response_payload.hex()}")
            
            except socket.timeout:
                retries += 1
                print(f"Timeout waiting for ACK for packet {packet_id}, retry {retries}/{max_retries}")
        
        if not acked:
            print(f"Failed to get ACK for packet {packet_id} after {max_retries} retries")
            return None
    
    # After all packets are sent and ACKed, wait for the final response
    print("All packets ACKed, waiting for final response...")
    client_socket.settimeout(3.0)  # Longer timeout for final response
    
    try:
        response, server_address = client_socket.recvfrom(1024)
        response_payload = response[12:]
        
        if len(response_payload) == 8:
            tcp_port, secretB = struct.unpack("!II", response_payload)
            print(f"Received TCP port {tcp_port} and secretB {secretB}")
            self.secrets['B'] = secretB
            return tcp_port
        else:
            print(f"Unexpected final response: {response_payload.hex()}")
    
    except socket.timeout:
        print("Timeout waiting for final response")
    
    return None

              

  def run(self):
    try:
        num, length, udp_port = self.stage_a()
        tcp_port = self.stage_b(num, length, udp_port)
    
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
    student_id_last_three_digits = "187"
    
    client = SocketClient(server_name, port, student_id_last_three_digits)
    client.run()

if __name__ == "__main__":
    main()