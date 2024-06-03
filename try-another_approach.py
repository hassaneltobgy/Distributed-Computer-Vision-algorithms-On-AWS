import subprocess
import os
import socket
import time
import boto3

def start_instance(instance_id):
    ec2_client = boto3.client('ec2', region_name='eu-west-3', aws_access_key_id='-----------------',
                                  aws_secret_access_key= "---------------------------------")
    try:
        time.sleep(30)
        # instance_id= instance_ids['slave1']
        ec2_client.start_instances(InstanceIds=[instance_id])
        print("Starting instance", instance_id)
        waiter = ec2_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        print("Instance", instance_id, "is now running")
        return True
    except Exception as e:
        return False
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


    if counter ==4:

        # If all initial hosts are unreachable, try to ping slave11
        try:
            if start_instance("i-0bee8c352438c2f79"):
                print("First instance is up")
            else:
                print("Something went wrong while starting instance 1")
            if start_instance("i-0e81b548788928158"):
                print("Second instance is up")
            else:
                print("Something went wrong while starting instance 2")
            if start_instance("i-0ee7e5fdc91136e05"):
                print("Third instance is up")
            else:
                print("Something went wrong while starting instance 3")
            if start_instance("i-05415edfc29f4dbb3"):
                print("Fourth instance is up")
            else:
                print("Something went wrong while starting instance 4")

        except Exception as e:
            print("Something went wrong while starting instances")
            print(e)

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


#Example usage:
potential_hosts = ["slave1", "slave2", "slave3", "slave4"]
responsive_hosts = check_hosts_alive(potential_hosts)

if responsive_hosts:
    script_path = "master-node4.py"
    launch_mpi_processes(responsive_hosts, script_path)
else:
    print("No alive slave hosts found. Exiting.")
