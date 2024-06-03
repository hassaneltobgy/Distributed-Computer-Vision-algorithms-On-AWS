import cv2
import socket
import base64
import os
import numpy as np
import time
import threading
import queue
from mpi4py import MPI

def process_image(img_data, operation):
    # Convert the base64 encoded image data to bytes
    image_bytes = base64.b64decode(img_data)

    # Convert the bytes to a NumPy array
    img_array = np.frombuffer(image_bytes, dtype=np.uint8)

    # Decode the image array to get its dimensions and channels
    img = cv2.imdecode(img_array, flags=cv2.IMREAD_COLOR)

    # Perform the specified image processing operation
    if operation == "grayscale":
        processed_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif operation == "blur":
        processed_img = cv2.GaussianBlur(img, (5, 5), 0)
    elif operation == "edge_detection":
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_img = cv2.Canny(gray_img, 100, 200) # Canny edge detection
    else:
        processed_img = img  # If no operation specified, return original image

    # Encode the processed image to bytes
    _, processed_img_bytes = cv2.imencode('.jpg', processed_img)
    processed_img_str = base64.b64encode(processed_img_bytes).decode()

    return processed_img_str

def handle_client(client_socket, comm, rank):
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

    operation=client_socket.recv(4096).decode()
    client_socket.send(f"operation {operation} is sent".encode())

    # Send the image data and operation to a worker node for processing
    if rank == 0:
        # Master node sends the data to a worker node
        worker_rank = (rank + 1) % comm.Get_size()
        comm.send(image_data, dest=worker_rank)
        comm.send(operation.encode(), dest=worker_rank)

        # Receive the processed image data from the worker node
        processed_img_data = comm.recv(source=worker_rank)
        print(f"Task processed by worker node {worker_rank-1}")
    else:
        # Worker node receives the data from the master node
        image_data = comm.recv(source=0)
        operation = comm.recv(source=0).decode()

        # Process the image data
        processed_img_data = process_image(base64.b64encode(image_data).decode(), operation)

        # Send the processed image data back to the master node
        comm.send(processed_img_data, dest=0)

    # Save the processed image to a file and send it back to the client
    timestamp = int(time.time())  # Use current timestamp as part of filename
    processed_filename = f"processed_image_{timestamp}+{operation}.jpg"
    with open(processed_filename, "wb") as f:
        f.write(base64.b64decode(processed_img_data))
    with open(processed_filename, "rb") as f:
        img_data = f.read(4096)
        while img_data:
            client_socket.send(img_data)
            img_data = f.read(4096)
    message = b"DONE"
    client_socket.send(message)

def start_server(host, port, comm, rank):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on {host}:{port}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket, comm, rank))
        client_thread.start()

if __name__ == "__main__":
    HOST = "0.0.0.0"  # Listen on all available interfaces
    PORT = 10240  # Choose a port number

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()

    if rank == 0:
        # Start the server on the master node
        start_server(HOST, PORT, comm, rank)
    else:
        # Worker nodes wait for tasks from the master node
        while True:
            image_data = comm.recv(source=0)
            operation = comm.recv(source=0).decode()
            processed_img_data = process_image(base64.b64encode(image_data).decode(), operation)
            comm.send(processed_img_data, dest=0)
