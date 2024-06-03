import socket
import base64
import cv2
import numpy as np
import time
import json

def send_request(filename, operation, host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    with open(filename, "rb") as f:
        img_data = f.read(2048)
        while img_data:
            client_socket.send(img_data)
            img_data=f.read(2048)
    client_socket.send(b"IMAGE SENT")
    message=client_socket.recv(2048)
    print(message)
    if message==b"IMAGE RECEIVED":
        client_socket.send(b"{operation}")

    print("Request sent successfully.")

    processed_img_bytes = b""
    while True:
        chunk = client_socket.recv(2048)
        if not chunk:
            break
        processed_img_bytes += chunk
    if chunk == b"IMAGE PROCCESSED SENT":
       print("Proccessed image received ")


    #
    img_array = np.frombuffer(processed_img_bytes, dtype=np.uint8)
    # #
    # #
    processed_img = cv2.imdecode(img_array, flags=cv2.IMREAD_COLOR)


    # Save the processed image
    timestamp = int(time.time())  # Use current timestamp as part of filename
    processed_filename = f"processed_image_{timestamp}.jpg"
    with open(processed_filename, "wb") as f:
        f.write(processed_img)

    print(f"Processed image received and saved as {processed_filename} successfully.")

    # Close the socket
    client_socket.close()

    print("Socket closed.")


if __name__ == "__main__":
     # Replace with the public IP address or domain name of your EC2 instance
    PORT = 12345 # Same port number used in the server code
    HOST='127.0.0.1'
    filename = "OIP.jpg"  # Path to your image file
    operation = "edge_detection"  # Choose operation: "grayscale", "blur", "edge_detection", etc.
    send_request(filename, operation, HOST, PORT)
