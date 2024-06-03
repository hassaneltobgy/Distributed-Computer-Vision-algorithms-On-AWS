from mpi4py import MPI
import cv2
import socket
import os
import numpy as np
import time
import subprocess
import logging
import sys
import threading

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

CHUNK_SIZE = 1024 * 1024


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
    elif operation == "edge_detection":
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_img = cv2.Canny(gray_img, 100, 200)  # Canny edge detection
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


def check_hosts_alive(hosts):
    alive_hosts = []
    for host in hosts:
        try:
            subprocess.check_output(["ping", "-c", "1", "-W", "1", host])
            alive_hosts.append(host)
            logging.info(f"{host} is alive!")
        except subprocess.CalledProcessError:
            logging.warning(f"{host} is not reachable!")
    return alive_hosts


def launch_mpi_processes(alive_hosts, script_path):
    num_processes = len(alive_hosts) + 1  # Include master node
    all_hosts = [socket.gethostname()] + alive_hosts

    command = ["mpirun", "-np", str(num_processes), "--host", ",".join(all_hosts), "python3", script_path]
    logging.info(f"Full mpirun command: {' '.join(command)}")

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy())
        stdout, stderr = process.communicate()
        return_code = process.returncode
        logging.info(f"mpirun return code: {return_code}")
        logging.debug(f"Output from mpirun: {stdout.decode()}")
        if return_code != 0:
            logging.error(f"Errors from mpirun: {stderr.decode()}")
            execute_try_py()
    except Exception as e:
        logging.error(f"Failed to launch MPI processes: {e}")
        execute_try_py()


def handle_client(client_socket):
    try:
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
        client_socket.recv(4096).decode()

        if rank == 0:
            logging.debug("Rank 0: Starting to process image data")
            num_chunks = (len(image_data) + CHUNK_SIZE - 1) // CHUNK_SIZE
            logging.debug(f"Rank 0: Calculated num_chunks = {num_chunks}")

            for i in range(1, size):
                comm.send(num_chunks, dest=i, tag=1)
                comm.send(operation, dest=i, tag=5)

            logging.info(f"Master node is distributing {num_chunks} chunks to {size - 1} slave nodes.")

            processed_chunks = [None] * num_chunks
            failed_nodes = []

            for chunk_index in range(num_chunks):
                start = chunk_index * CHUNK_SIZE
                end = min(start + CHUNK_SIZE, len(image_data))
                for i in range(1, size):
                    try:
                        comm.send(image_data[start:end], dest=i, tag=2)
                        comm.recv(source=i, tag=4)
                    except MPI.Exception as e:
                        logging.error(f"Failed to send/receive data to/from slave {i}: {e}")
                        failed_nodes.append(i)
                        execute_try_py()
                        return

            for chunk_index in range(num_chunks):
                for i in range(1, size):
                    if i in failed_nodes:
                        continue
                    try:
                        processed_chunk = comm.recv(source=i, tag=3)
                        processed_chunks[chunk_index] = processed_chunk
                    except MPI.Exception as e:
                        logging.error(f"Failed to receive processed chunk from slave {i}: {e}")
                        failed_nodes.append(i)
                        execute_try_py()
                        return

            processed_img_bytes = b"".join([chunk for chunk in processed_chunks if chunk is not None])

            timestamp = int(time.time())
            processed_filename = f"processed_image_{timestamp}+{operation}.jpg"
            with open(processed_filename, "wb") as f:
                f.write(processed_img_bytes)

            with open(processed_filename, "rb") as f:
                img_data = f.read(4096)
                while img_data:
                    client_socket.send(img_data)
                    img_data = f.read(4096)

            message = b"DONE"
            client_socket.send(message)
            os.remove(processed_filename)
    except Exception as e:
        logging.error(f"Error handling client: {e}")
        execute_try_py()


def execute_try_py():
    try:
        logging.info("Executing fallback script try.py")
        subprocess.run(["python3", "try.py"], check=True)
    except Exception as e:
        logging.error(f"Failed to execute try.py: {e}")


def start_server(host, port):
    if rank == 0:
        slave_hosts = ["slave1", "slave2", "slave3", "slave4", "slave11"]  # Replace with your slave hostnames
        alive_hosts = check_hosts_alive(slave_hosts)

        if not alive_hosts:
            logging.error("No alive slave hosts found. Exiting.")
            execute_try_py()
            return

        script_path = os.path.abspath(__file__)
        launch_mpi_processes(alive_hosts, script_path)

        def monitor_slaves():
            while True:
                time.sleep(10)  # Adjust the interval as needed
                current_alive_hosts = check_hosts_alive(slave_hosts)
                if set(current_alive_hosts) != set(alive_hosts):
                    logging.error("One or more slave hosts became unreachable. Executing fallback.")
                    execute_try_py()
                    break

        threading.Thread(target=monitor_slaves, daemon=True).start()

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(5)
        logging.info(f"Server listening on {host}:{port}")

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                logging.info(f"Connection from {client_address}")
                handle_client(client_socket)
            except Exception as e:
                logging.error(f"Error accepting client connection: {e}")
                execute_try_py()
    else:
        while True:
            try:
                logging.debug(f"Slave node {rank} waiting for instructions")
                num_chunks = comm.recv(source=0, tag=1)
                operation = comm.recv(source=0, tag=5)

                logging.info(f"Slave node {rank} received {num_chunks} chunks to process.")

                for chunk_index in range(num_chunks):
                    try:
                        image_chunk = comm.recv(source=0, tag=2)
                        comm.send(True, dest=0, tag=4)

                        processed_chunk = process_image(image_chunk, operation)

                        comm.send(processed_chunk, dest=0, tag=3)
                    except MPI.Exception as e:
                        logging.error(f"Error processing chunk {chunk_index} in slave node {rank}: {e}")
                        execute_try_py()
                        return
            except Exception as e:
                logging.error(f"Error in slave node {rank}: {e}")
                execute_try_py()


if __name__ == "__main__":
    HOST = "0.0.0.0"
    PORT = 10240

    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    logging.info(f"Environment Variables: {os.environ}")

    try:
        mpi_path = subprocess.check_output(["which", "mpirun"]).strip().decode()
        logging.info(f"mpirun path: {mpi_path}")
    except subprocess.CalledProcessError as e:
        logging.error("mpirun not found in PATH")

    try:
        start_server(HOST, PORT)
    except Exception as e:
        logging.error(f"Critical error in server: {e}")
        execute_try_py()
