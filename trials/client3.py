import socket
import base64
import cv2
import numpy as np
import time

def send_request(filename, operation, host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    print("Image is being processed .....")
    with open(filename, "rb") as f:
        img_data = f.read(8192)
        while img_data:
            client_socket.send(img_data)
            img_data=f.read(8192)

    message=b"IMAGE SENT"
    client_socket.send(message)

    message=client_socket.recv(8192)
    if message==b"IMAGE RECEIVED":
        print("Server recieved image safely")
        client_socket.send(f"{operation}".encode())

    message=client_socket.recv(8192).decode()
    print(message)

    client_socket.send(f"operation request is sent successfully, waiting for image to be processed".encode())

    processed_img_bytes = b""
    while True:
        chunk = client_socket.recv(8192)
        #print("Chunk received:", chunk)
        if not chunk:
            break
        processed_img_bytes += chunk
        if b"DONE" in chunk:
            print("Processed image received at client")
            break

    img_array = np.frombuffer(processed_img_bytes, dtype=np.uint8)
    processed_img = cv2.imdecode(img_array, flags=cv2.IMREAD_COLOR)
    # Check the dimensions of the decoded image
    if processed_img is not None and processed_img.size > 0:
        # Display the image if it has valid dimensions
        cv2.imshow('Processed image on client', processed_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("Error: Invalid image dimensions.")


    # Save the processed image
    timestamp = int(time.time())  # Use current timestamp as part of filename
    processed_filename = f"processed_image_{timestamp}.jpg"
    cv2.imwrite(processed_filename,processed_img)
    # with open(processed_filename, "wb") as f:
    #     f.write(processed_img)
    print(f"Processed image saved as {processed_filename} successfully.")
    # Close the socket
    client_socket.close()
    print("Socket closed.")


if __name__ == "__main__":
     # Replace with the public IP address or domain name of your EC2 instance
    PORT = 10240 # Same port number used in the server code
    HOST='13.38.35.41'
    filename = "OIP.jpg"  # Path to your image file
    operation = "grayscale"  # Choose operation: "grayscale", "blur", "edge_detection", etc.
    send_request(filename, operation, HOST, PORT)


