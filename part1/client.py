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

  def stage_b(self):
      print("Starting Stage B...")
      
      # Create a UDP socket for Stage B
      client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      client_socket.settimeout(self.timeout)
      packet_id = 0
      while True:
          
          message = b'000000000000000000000000'
          payload_len = len(message)
          header = self.create_header(payload_len, self.secrets['A'], 2)
          packet = header + message
          packet = self.pad_to_4_byte_boundary(packet)


          start_time = time.time()
          while time.time() - start_time < 0.5:
            # Send the packet to the server
            client_socket.sendto(packet, (self.server_name, self.port))
            print(f"Sent packet ID {packet_id} to {self.server_name}:{client_socket}")

            # Receive response from server
            try: 
              response, server_address = client_socket.recvfrom(1024)
              print(f"Received response for packet ID {packet_id} from server")
            except socket.timeout:
              continue
            finally:
              # Parse the response (should be 4 integers: num, len, udp_port, secretA)
              # Skip the 12-byte header (we don't need to parse it for the response)
              response_payload = response[12:]
              if (len(response_payload) == 8):
                tcp_port, secretB = struct.unpack("!II", response_payload)
                print(f"Received TCP port {tcp_port} and secretB {secretB} from server")
                self.secrets['B'] = secretB
              else:
                acked_packet_id = struct.unpack("!I", response_payload)
                print(f"Received ACK for packet ID {acked_packet_id} from server")
              packet_id += 1

              

  def run(self):
        """
        Run the entire client protocol
        """
        try:
            # Stage A: Send hello world, receive num, len, udp_port, secretA
            num, length, udp_port = self.stage_a()
            self.stage_b()
        
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