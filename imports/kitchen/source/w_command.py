import subprocess
import time
import os
import signal
from threading import Thread
from queue import Queue, Empty

def wread_stream(stream, queue):
    """Read lines from a stream and push them to a queue."""
    for line in iter(stream.readline, b''):
        queue.put(line.decode())
    stream.close()

def wrun_command(command, timeout=None, env=None):
    """
    Executes a command, capturing stdout and stderr with optional timeout.
    
    Args:
        command (list): Command and arguments as a list, e.g., ['cmd', '/c', 'dir']
        timeout (float): Timeout in seconds for the command to execute
        env (dict): Environment variables to set for the command

    Returns:
        tuple: stdout (str), stderr (str), exit_status (int)
    """
    # Start the subprocess
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,  # Read binary streams
        env=env
    )
    
    # Queues for communication
    stdout_queue = Queue()
    stderr_queue = Queue()

    # Threads to read stdout and stderr
    stdout_thread = Thread(target=wread_stream, args=(process.stdout, stdout_queue))
    stderr_thread = Thread(target=wread_stream, args=(process.stderr, stderr_queue))
    stdout_thread.start()
    stderr_thread.start()

    start_time = time.time()

    try:
        while True:
            if timeout and (time.time() - start_time) > timeout:
                process.send_signal(signal.CTRL_BREAK_EVENT if os.name == 'nt' else signal.SIGKILL)
                raise TimeoutError(f"Command '{command[0]}' timed out after {timeout} seconds")

            # Check if process has completed
            ret_code = process.poll()
            if ret_code is not None:
                break

            time.sleep(0.01)  # Prevent busy-waiting

    finally:
        # Ensure threads finish
        stdout_thread.join()
        stderr_thread.join()
        
        # Close the process
        process.stdout.close()
        process.stderr.close()

    # Collect output from queues
    stdout = ''.join(iter(lambda: stdout_queue.get_nowait() if not stdout_queue.empty() else '', ''))
    stderr = ''.join(iter(lambda: stderr_queue.get_nowait() if not stderr_queue.empty() else '', ''))

    return stdout, stderr, process.returncode

# Example usage
try:
    stdout, stderr, status = wrun_command(['cmd', '/c', 'dir'], timeout=5)
    print("STDOUT:", stdout)
    print("STDERR:", stderr)
    print("STATUS:", status)
except TimeoutError as e:
    print(e)
