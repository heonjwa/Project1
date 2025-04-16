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
    print(f"Starting Stage B... Sending {num} packets of length {length}")
    
    # Create a UDP socket for Stage B
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(self.timeout)
    
    # Keep track of which packets have been acknowledged
    acked_packets = set()
    
    start_time = time.time()
    
    # Continue until all packets are acknowledged
    while len(acked_packets) < num:
        # Determine which packets need to be sent or resent
        for packet_id in range(num):
            if packet_id not in acked_packets:
                # Create packet with packet_id as first 4 bytes of payload
                packet_id_bytes = struct.pack("!I", packet_id)
                # Add len bytes of zeros as the rest of the payload
                zeros = b'\x00' * length
                
                # Complete payload
                payload = packet_id_bytes + zeros
                payload_len = len(payload)
                
                # Create packet header with secretA as psecret
                header = self.create_header(payload_len, self.secrets['A'], 1)
                
                # Combine header and payload
                packet = header + payload
                
                # Ensure 4-byte alignment (though it should already be aligned)
                packet = self.pad_to_4_byte_boundary(packet)
                print(f"Sending packet ID {packet_id} with packet length {len(packet)}")
                # Send the packet
                client_socket.sendto(packet, (self.server_name, udp_port))
                print(f"Sent packet ID {packet_id} to {self.server_name}:{udp_port}")
        
        # Check for acknowledgements until timeout
        try:
            while True:
                response, server_address = client_socket.recvfrom(1024)
                print(f"Received response from server: {response}")
                
                # First check if this is the final response (with TCP port and secretB)
                if len(response) >= 20:  # Header (12) + two integers (8)
                    response_payload = response[12:]
                    if len(response_payload) == 8:
                        tcp_port, secretB = struct.unpack("!II", response_payload)
                        print(f"Received TCP port {tcp_port} and secretB {secretB} from server")
                        self.secrets['B'] = secretB
                        return tcp_port
                
                # Otherwise it should be an ACK
                if len(response) >= 16:  # Header (12) + one integer (4)
                    response_payload = response[12:]
                    acked_id = struct.unpack("!I", response_payload)[0]
                    acked_packets.add(acked_id)
                    print(f"Received ACK for packet ID {acked_id} from server ({len(acked_packets)}/{num} acknowledged)")
        
        except socket.timeout:
            # If we time out waiting for ACKs, we'll retry the unacknowledged packets
            print(f"Timeout waiting for ACKs. Retransmitting unacknowledged packets. {len(acked_packets)}/{num} received.")
            time.sleep(self.retransmission_interval)
    
    # If we get here, all packets were acknowledged but we didn't get the final message
    print("All packets acknowledged but didn't receive TCP port and secretB!")
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