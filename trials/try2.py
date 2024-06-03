import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import os
from mpi4py import MPI

from tkinter_try import operation_var

# Initialize MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Worker capabilities (modify as needed)
worker_capabilities = {
    1: ["grayscale", "blur"],
    2: ["edge_detection"],
    # Add more workers and capabilities as necessary
}

# Task queue (only on the master node)
if rank == 0:
    task_queue = []

# Image processing function
def process_image(image_path, operation):
    img = cv2.imread(image_path)
    if operation == "grayscale":
        processed_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif operation == "blur":
        processed_img = cv2.GaussianBlur(img, (5, 5), 0)
    elif operation == "edge_detection":
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        processed_img = cv2.Canny(gray_img, 100, 200)
    else:
        raise ValueError("Invalid operation")
    return processed_img

# Function to handle image selection and processing (on master node)
def select_and_process_image():
    root.withdraw()
    file_path = filedialog.askopenfilename()
    root.deiconify()

    if file_path:
        operation = operation_var.get()
        task_queue.append((file_path, operation))

        # Distribute task to appropriate worker based on operation
        for worker_rank, capabilities in worker_capabilities.items():
            if operation in capabilities:
                task = task_queue.pop(0)
                comm.send(task, dest=worker_rank)
                break  # Task sent, move to the next one

# Master node logic
if rank == 0:
    # Tkinter GUI code (similar to before)
    root = tk.Tk()
    # ... (Add GUI elements for image selection and operation dropdown)

    # Handle incoming results from workers
    for _ in range(len(task_queue)):
        result = comm.recv(source=MPI.ANY_SOURCE)
        # ... (Process or display the result)

    root.mainloop()

# Worker node logic
else:
    while True:
        # Receive task from master
        image_path, operation = comm.recv(source=0)
        # Process image
        processed_img = process_image(image_path, operation)
        # Send result back to master
        comm.send(processed_img, dest=0)