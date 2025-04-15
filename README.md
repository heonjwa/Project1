# Project 1: The Sockets API

This project implements a client-server application using the sockets API. The implementation follows a specific protocol for communication between the client and server.

## Team Members

- Name: Heon (NetID: [Your NetID])
- Name: [Team Member 2] (NetID: [Team Member 2 NetID])
- Name: [Team Member 3] (NetID: [Team Member 3 NetID])

## Project Structure

The project is organized as follows:

```
cse461-p1/
├── part1/
│   ├── client.py           # Client implementation
│   ├── run_client.sh       # Script to run the client
│   └── README.md           # Part 1 documentation
├── part2/
│   ├── server.py           # Server implementation
│   ├── run_server.sh       # Script to run the server
│   └── README.md           # Part 2 documentation
└── README.md               # Main documentation
```

## Part 1: Client Implementation

The client follows the protocol described in the project specification, communicating with a server through UDP and TCP sockets.

### Features

- Implements all stages of the protocol (A, B, C, D)
- Handles proper header formatting and packet padding
- Implements reliable packet transmission in Stage B with retransmission
- Collects and stores secrets from each stage

### Dependencies

- Python 3.6 or higher
- Standard Python libraries (socket, struct, time, sys, random)

### Running the Client

You can run the client using the provided script:

```bash
./part1/run_client.sh <server_name> <port>
```

For example:

```bash
./part1/run_client.sh attu2.cs.washington.edu 12235
```

## Part 2: Server Implementation

The server implements the matching protocol to communicate with clients via UDP and TCP sockets.

### Features

- Processes all stages of the protocol (A, B, C, D)
- Handles multiple clients simultaneously using threading
- Validates client requests and properly enforces the protocol
- Generates random secrets for each stage
- Implements intentional packet dropping in Stage B

### Dependencies

- Python 3.6 or higher
- Standard Python libraries (socket, struct, time, sys, random, threading)

### Running the Server

You can run the server using the provided script:

```bash
./part2/run_server.sh <server_name> <port>
```

For example:

```bash
./part2/run_server.sh localhost 12235
```

## Important Notes

1. Make sure to replace the placeholder student ID in both client.py and server.py with your actual student ID (last 3 digits).
2. The server is designed to listen on any interface (0.0.0.0) so it can accept connections from any client.
3. For testing, you can run both the client and server on the same machine using localhost as the server name.
4. For submission, please ensure that the code is tested on attu.cs.washington.edu or the UW CSE VM.

## Troubleshooting

- If you encounter connection issues, ensure that the firewall is not blocking the ports used by the application.
- If the client or server hangs, it may be due to a timeout. Check the timeout values in the code.
- For more assistance, contact the course staff or refer to the project specification.