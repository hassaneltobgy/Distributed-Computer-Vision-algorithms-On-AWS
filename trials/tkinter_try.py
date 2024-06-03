from mpi4py import MPI
import cv2
import socket
import base64
import numpy as np
import os

def process_image(img, operation):
    # Process the image based on the operation
    if operation == "grayscale":
        processed_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif operation == "blur":
        processed_img = cv2.GaussianBlur(img, (5, 5), 0)
    elif operation == "edge_detection":
        processed_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_img = cv2.Canny(processed_img, 100, 200)  # Canny edge detection
    else:
        processed_img = img  # If no operation specified, return original image

    # Encode the processed image to base64
    retval, buffer = cv2.imencode('.jpg', processed_img)
    base64_encoded_img = base64.b64encode(buffer)
    return base64_encoded_img

def handle_client(client_socket):
    try:
        # Receive the operation to be performed from the client
        operation = client_socket.recv(1024).decode()

        # Receive the length of the image data from the client
        length_str = client_socket.recv(1024).decode()
        length = int(length_str)

        # Receive the image data from the client
        image_data = b''
        while len(image_data) < length:
            packet = client_socket.recv(4096)
            if not packet:
                break
            image_data += packet

        # Convert the bytes data to a numpy array
        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Process the image
        processed_img = process_image(img, operation)

        # Send the processed image back to the client
        client_socket.send(processed_img)
    except ValueError as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()


def start_master_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Master server listening on {host}:{port}")

    comm = MPI.COMM_WORLD
    size = comm.Get_size()

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")

        # Handle client in a separate function
        handle_client(client_socket)

if __name__ == "__main__":
    HOST = "172.31.4.1"  # Listen on all available interfaces
    PORT = 10240  # Choose a port number

    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    start_master_server(HOST, PORT)
