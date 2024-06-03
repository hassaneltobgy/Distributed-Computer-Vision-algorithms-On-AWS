from mpi4py import MPI
import cv2
import socket
import base64
import os
import numpy as np
import time

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()  # Get the actual number of nodes running

CHUNK_SIZE = 1024 * 1024  # 1 MB chunks
HEARTBEAT_TIMEOUT = 5  # Seconds

def process_image(img_data, operation, width=None, height=None):
    # Convert the bytes to a NumPy array
    img_array = np.frombuffer(img_data, dtype=np.uint8)

    # Decode the image array to get its dimensions and channels
    img = cv2.imdecode(img_array, flags=cv2.IMREAD_COLOR)

    # Perform the specified image processing operation
    if operation == "grayscale":
        processed_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif operation == "blur":
        processed_img = cv2.GaussianBlur(img, (5, 5), 0)
    elif operation == "edge_detection":
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_img = cv2.Canny(gray_img, 100, 200)
    elif operation == "thresholding":
        ret, processed_img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    elif operation == "histogram_equalization":
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_img = cv2.equalizeHist(gray_img)
    elif operation == "rotation_left":
        rows, cols = img.shape[:2]
        rotation_matrix = cv2.getRotationMatrix2D((cols / 2, rows / 2), 90, 1)  # Rotate left
        processed_img = cv2.warpAffine(img, rotation_matrix, (cols, rows))
    elif operation == "rotation_right":
        rows, cols = img.shape[:2]
        rotation_matrix = cv2.getRotationMatrix2D((cols / 2, rows / 2), -90, 1)  # Rotate right
        processed_img = cv2.warpAffine(img, rotation_matrix, (cols, rows))
    elif operation == "scaling":
        if width is None or height is None:
            raise ValueError("Width and height must be specified for scaling operation")
        processed_img = cv2.resize(img, (width, height))
    elif operation == "corner_detection":
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        dst = cv2.cornerHarris(gray_img, 2, 3, 0.04)  # Corner detection
        dst = cv2.dilate(dst, None)
        processed_img = img.copy()
        processed_img[dst > 0.01 * dst.max()] = [0, 0, 255]  # Mark corners in red
    elif operation == "deblurring":
        processed_img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)  # Deblurring
    else:
        processed_img = img  # If no operation specified, return original image

    # Encode the processed image to bytes
    _, buffer = cv2.imencode('.jpg', processed_img)
    return buffer.tobytes()
def handle_client(client_socket):
    # Receive the image data and operation sent by the client
    image_data = b""
    while True:
        chunk = client_socket.recv(4096)
        if not chunk:
            break
        if b"IMAGE SENT" in chunk:
            client_socket.send(b"IMAGE RECEIVED")
            break
        image_data += chunk

    operation = client_socket.recv(4096).decode()
    client_socket.send(f"operation {operation} is sent".encode())
    client_socket.recv(4096).decode()  # Wait for acknowledgment

    # Master node distributes the work to slaves
    if rank == 0:
        num_chunks = (len(image_data) + CHUNK_SIZE - 1) // CHUNK_SIZE

        # Tell slaves how many chunks and the operation to expect
        for i in range(1, size):  # Only send to available slaves
            comm.send(num_chunks, dest=i, tag=1)
            comm.send(operation, dest=i, tag=5)  # Send operation to slaves

        print(f"Master node is distributing {num_chunks} chunks to {size - 1} slave nodes.")

        # Heartbeat and Redistribution Logic
        heartbeat_timer = time.time()
        alive_slaves = set(range(1, size))  # Track which slaves are alive

        # Distribute chunks to slaves
        for chunk_index in range(num_chunks):
            # Send heartbeat to all slaves
            for i in range(1, size):
                try:
                    comm.send(True, dest=i, tag=100)  # Heartbeat
                    comm.recv(source=i, tag=100, timeout=HEARTBEAT_TIMEOUT)  # Expect reply
                except MPI.Exception.Timeout:
                    print(f"Slave node {i} appears to be down. Removing from alive_slaves")
                    alive_slaves.remove(i)

            # Redistribute tasks if slaves are down
            if len(alive_slaves) < size - 1:
                print(f"Redistributing chunks for failed slaves. {len(alive_slaves)} slaves remain")
                redistributed_chunks = []
                for i in range(1, size):
                    if i not in alive_slaves:  # This slave is down
                        # Find unassigned chunks and send them to a working slave
                        for j in range(chunk_index, num_chunks):
                            if j not in redistributed_chunks:
                                if len(alive_slaves) > 0:
                                    slave_to_assign = list(alive_slaves)[0]  # Choose the first available slave
                                    comm.send(image_data[j * CHUNK_SIZE:(j + 1) * CHUNK_SIZE], dest=slave_to_assign, tag=2)
                                    comm.recv(source=slave_to_assign, tag=4)  # Wait for acknowledgment
                                    redistributed_chunks.append(j)
                                else:
                                    print(f"Warning: No available slaves to handle chunk {j}.")
                                    break

            # Receive processed chunks from slaves
            # Now use a dynamic loop to receive from all ALIVE slaves
            processed_chunks = []
            for i in alive_slaves:
                processed_chunk = comm.recv(source=i, tag=3)
                processed_chunks.append(processed_chunk)

            # ... (Combine processed chunks and send the processed image back to the client) ... 

def start_server(host, port):
    if rank == 0:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"Server listening on {host}:{port}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")
            handle_client(client_socket)
    else:
        # Slave nodes wait for instructions from master
        while True:
            num_chunks = comm.recv(source=0, tag=1)
            operation = comm.recv(source=0, tag=5)  # Receive operation from master

            print(f"Slave node {rank} received {num_chunks} chunks to process.")

            for chunk_index in range(num_chunks):
                # Process image chunk
                image_chunk = comm.recv(source=0, tag=2)
                comm.send(True, dest=0, tag=4)  # Acknowledge receipt

                # Process image chunk
                processed_chunk = process_image(image_chunk, operation)

                # Send processed chunk back to master
                comm.send(processed_chunk, dest=0, tag=3)

            # Heartbeat handler
            try:
                heartbeat = comm.recv(source=0, tag=100, timeout=HEARTBEAT_TIMEOUT)
                comm.send(True, dest=0, tag=100)  # Respond to heartbeat
            except MPI.Exception.Timeout:
                print(f"Slave node {rank} did not receive heartbeat from master. Assuming master is down.")
                break  # Exit the loop and potentially handle this event

if __name__ == "__main__":
    HOST = "0.0.0.0"
    PORT = 10240

    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    start_server(HOST, PORT)