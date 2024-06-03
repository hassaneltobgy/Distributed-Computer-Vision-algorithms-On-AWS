import cv2
import socket
import base64
import os
import numpy as np
import json

def process_image(img_data, operation):
    # Convert the base64 encoded image data to bytes
    #image_bytes = base64.b64decode(img_data)

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
        processed_img = cv2.Canny(gray_img, 100, 200)  # Canny edge detection
    else:
        processed_img = img  # If no operation specified, return original image

    # Encode the processed image to bytes
    retval, buffer = cv2.imencode('.jpg', processed_img)
    processed_img_bytes = base64.b64encode(buffer)
    return processed_img_bytes

def handle_client(client_socket):
    # Receive the image data and operation sent by the client
    image_data = b""
    while True:
        chunk = client_socket.recv(2048)
        if not chunk:
            break
        if chunk==b"IMAGE SENT":
            client_socket.send(b"IMAGE RECEIVED")
            break
        image_data += chunk

    operation=client_socket.recv(2048)
    processed_img_bytes=process_image(image_data,operation)
    # Send the processed image data back to the client
    offset = 0
    chunk_size = 2048
    while offset < len(processed_img_bytes):
        img_data_chunk = processed_img_bytes[offset:offset + chunk_size]
        client_socket.send(img_data_chunk)
        offset += chunk_size
    client_socket.send(b"IMAGE PROCCESSED SENT")

def start_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on {host}:{port}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")
        handle_client(client_socket)

if __name__ == "__main__":
    HOST = "127.0.0.1"  # Listen on all available interfaces
    PORT = 12345  # Choose a port number

    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    start_server(HOST, PORT)
