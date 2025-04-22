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
        self.timeout = 3
        self.retransmission_interval = 0.5

  def create_header(self, payload_len, psecret, step):
      return struct.pack("!IIHH", payload_len, psecret, step, self.student_id)

  def pad_to_4_byte_boundary(self, data):
      padding_needed = (4 - (len(data) % 4)) % 4
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
          client_socket.sendto(packet, (self.server_name, self.port))
          
          response, server_address = client_socket.recvfrom(1024)
          
          response_payload = response[12:]
          num, length, udp_port, secretA = struct.unpack("!IIII", response_payload)
          
          print(f"Received from server: num={num}, len={length}, udp_port={udp_port}, secretA={secretA}")
          
          self.secrets['A'] = secretA
          
          return num, length, udp_port
      
      except socket.timeout:
          print("Timeout occurred during Stage A")
          sys.exit(1)
      finally:
          client_socket.close()

  def stage_b(self, num, length, udp_port):
    print(f"Starting Stage B... Sending {num} packets with {length} zero bytes to port {udp_port}")
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(0.5)
    
    for packet_id in range(num):
        packet_id_bytes = struct.pack("!I", packet_id)
        zeros = b'\x00' * length
        
        payload = packet_id_bytes + zeros
        header = self.create_header(len(payload), self.secrets['A'], 1)
        
        packet = header + payload
        packet = self.pad_to_4_byte_boundary(packet)

        acked = False
        retries = 0
        max_retries = 10
        
        while not acked and retries < max_retries:
            try:
                client_socket.sendto(packet, (self.server_name, udp_port))
                print(f"Sent packet {packet_id} to {self.server_name}:{udp_port}")

                response, server_address = client_socket.recvfrom(1024)

                response_payload = response[12:]
                
                if len(response_payload) == 4:
                    acked_id = struct.unpack("!I", response_payload)[0]
                    print(f"Received ACK for packet ID {acked_id}")
                    
                    if acked_id == packet_id:
                        acked = True
                        print(f"Successfully ACKed packet {packet_id}")
                    else:
                        print(f"Received ACK for packet {acked_id}, expecting {packet_id}")
                
                elif len(response_payload) == 8:
                    tcp_port, secretB = struct.unpack("!II", response_payload)
                    print(f"Received TCP port {tcp_port} and secretB {secretB}")
                    self.secrets['B'] = secretB
                    return tcp_port
                
                else:
                    print(f"Unexpected payload: {response_payload.hex()}")
            
            except socket.timeout:
                retries += 1
        
        if not acked:
            print(f"Failed to get ACK for packet {packet_id} after {max_retries} retries")
            return None

    client_socket.settimeout(5.0)
    
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
  
  def stage_c(self, tcp_port):
    print(f"Starting Stage C... Connecting to TCP port {tcp_port}")
    
    try:
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.settimeout(self.timeout)
        
        self.tcp_socket.connect((self.server_name, tcp_port))
        print(f"Connected to server on TCP port {tcp_port}")
        
        response = self.tcp_socket.recv(1024)

        response_payload = response[12:]

        if len(response_payload) < 13:
            print(f"Unexpected response payload length: {len(response_payload)}")
            return None
        
        num2, len2, secretC = struct.unpack("!III", response_payload[:12])
        c = response_payload[12:13]
        
        print(f"Received from server: num2={num2}, len2={len2}, secretC={secretC}, c={c}")
        self.secrets['C'] = secretC
        
        return num2, len2, c
        
    except socket.timeout:
        print("Timeout occurred during Stage C")
        self.tcp_socket.close()
        return None
    except Exception as e:
        print(f"Error in Stage C: {e}")
        if hasattr(self, 'tcp_socket'):
            self.tcp_socket.close()
        return None
        
  def stage_d(self, num2, len2, c, tcp_port):
    print(f"Starting Stage D... Sending {num2} payloads, each with {len2} '{c}' characters over the existing TCP connection")
    
    try:
        if not hasattr(self, 'tcp_socket'):
            print("Error: No TCP connection available")
            return None
            
        message = c * len2
        
        for i in range(num2):
            header = self.create_header(len(message), self.secrets['C'], 1)
            
            packet = header + message
            packet = self.pad_to_4_byte_boundary(packet)
            
            self.tcp_socket.sendall(packet)
            
            if i < num2 - 1:
                time.sleep(0.1)
        
        self.tcp_socket.settimeout(5.0)
        
        response = self.tcp_socket.recv(1024)
        print(f"Received final response: {response.hex()}")
        
        if len(response) >= 16:
            response_payload = response[12:]
            
            if len(response_payload) >= 4:
                secretD = struct.unpack("!I", response_payload[:4])[0]
                self.secrets['D'] = secretD
                return secretD
        
        print("Did not receive expected response")
        return None
        
    except socket.timeout:
        print("Timeout occurred during Stage D")
        return None
    except Exception as e:
        print(f"Error in Stage D: {e}")
        return None
    finally:
        self.tcp_socket.close()
            
    

  def run(self):
    try:
        num, length, udp_port = self.stage_a()
            
        tcp_port = self.stage_b(num, length, udp_port)
            
        res_c = self.stage_c(tcp_port)
        if res_c is None:
            print("Stage C failed")
            return False
            
        num2, len2, c = res_c
        
        self.stage_d(num2, len2, c, tcp_port)
            
        print("All stages completed successfully!")
        print(f"Secrets: A={self.secrets['A']}, B={self.secrets['B']}, C={self.secrets['C']}, D={self.secrets['D']}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(self, 'tcp_socket'):
            self.tcp_socket.close()
        return False
    
        
def main():
    if len(sys.argv) != 3:
        print("Usage: python3 client.py <server_name> <port>")
        sys.exit(1)
    
    server_name = sys.argv[1]
    port = sys.argv[2]
    student_id_last_three_digits = "187"
    
    client = SocketClient(server_name, port, student_id_last_three_digits)
    client.run()

if __name__ == "__main__":
    main()