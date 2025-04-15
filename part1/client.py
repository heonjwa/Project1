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
      padding_needed = (4 - (len(data) % 4))
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
  def run(self):
        """
        Run the entire client protocol
        """
        try:
            # Stage A: Send hello world, receive num, len, udp_port, secretA
            num, length, udp_port = self.stage_a()
        
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
    student_id_last_three_digits = "187"  # Replace with your actual last 3 digits
    
    client = SocketClient(server_name, port, student_id_last_three_digits)
    client.run()

if __name__ == "__main__":
    main()