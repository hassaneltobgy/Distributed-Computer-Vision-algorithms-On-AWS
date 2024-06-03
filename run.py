import subprocess
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
def execute_try_py():
    """
    Execute the try.py script.
    """
    try:
        logging.info("Executing fallback script try.py")
        while True:
            try:
                time.sleep(10)
                logging.info("##########################################!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                subprocess.run(["python3", "try.py"], check=True)
                time.sleep(10)
                subprocess.run(["python3", "try.py"], check=True)
                #subprocess.run(["python3", "try.py"], check=True)
            except Exception as e:
                logging.error(f"Error executing try.py: {e}")
                time.sleep(5)  # Wait for 5 seconds before retrying
    except KeyboardInterrupt:
        logging.info("Exiting run.py due to keyboard interrupt.")

if __name__ == "__main__":
    execute_try_py()