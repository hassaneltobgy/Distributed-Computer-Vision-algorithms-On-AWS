import subprocess
import os
import socket


def check_hosts_alive(hosts):
    """Pings hosts to check if they are reachable.

    Args:
        hosts (list): A list of hostnames to ping.

    Returns:
        list: A list of hostnames that responded to pings.
    """
    alive_hosts = []
    counter = 0

    for host in hosts:
        try:
            subprocess.check_output(["ping", "-c", "1", "-W", "1", host])  # Adjust ping parameters as needed
            alive_hosts.append(host)
            print(f"{host} is alive!")
        except subprocess.CalledProcessError:
            counter += 1
            print(f"{host} is not reachable!")

    if counter == len(hosts):
        # If all initial hosts are unreachable, try to ping slave11
        try:
            subprocess.check_output(["ping", "-c", "1", "-W", "1", "slave11"])
            alive_hosts.append("slave11")
            print(f"slave11 is alive!")
        except subprocess.CalledProcessError:
            print(f"slave11 is also not reachable!")

    return alive_hosts


def launch_mpi_processes(alive_hosts, script_path):
    """Launches MPI processes across the specified hosts.

    Args:
        alive_hosts (list): A list of hostnames where MPI processes should be launched.
        script_path (str):  The absolute path to your Python script.
    """

    # Ensure script_path is an absolute path
    script_path = os.path.abspath(script_path)

    num_processes = len(alive_hosts) + 1  # Include the master node
    all_hosts = [socket.gethostname()] + alive_hosts
    host_string = ",".join(all_hosts)

    command = [
        "mpirun",
        "-n", str(num_processes),
        "--host", host_string,
        "python3", script_path
    ]

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return_code = process.returncode

        print(f"mpirun return code: {return_code}")
        print(f"Output from mpirun: {stdout.decode()}")

        if return_code != 0:
            print(f"Errors from mpirun: {stderr.decode()}")

    except Exception as e:
        print(f"Failed to launch MPI processes: {e}")


# Example usage:
potential_hosts = ["slave1", "slave2", "slave3", "slave4"]
responsive_hosts = check_hosts_alive(potential_hosts)

if responsive_hosts:
    script_path = "master-node4.py"
    launch_mpi_processes(responsive_hosts, script_path)
else:
    print("No alive slave hosts found. Exiting.")
