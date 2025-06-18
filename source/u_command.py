import os
import fcntl
import errno
import time
import signal

def run_command(command, timeout=None, env=None):
    """
    Executes a command, capturing stdout and stderr with optional timeout.
    
    Args:
        command (list): Command and arguments as a list, e.g., ['ls', '-l']
        timeout (float): Timeout in seconds for the command to execute
        env (dict): Environment variables to set for the command

    Returns:
        tuple: stdout (str), stderr (str), exit_status (int)
    """
    r_stdout, w_stdout = os.pipe()
    r_stderr, w_stderr = os.pipe()
    pid = os.fork()

    if pid == 0:  # Child process
        os.close(r_stdout)
        os.close(r_stderr)
        os.dup2(w_stdout, 1)
        os.dup2(w_stderr, 2)
        os.close(w_stdout)
        os.close(w_stderr)

        # Execute the command with optional environment
        try:
            if env:
                os.execvpe(command[0], command, env)
            else:
                os.execvp(command[0], command)
        except Exception as e:
            print(f"Execution failed: {e}", file=os.fdopen(2, 'w'))
            os._exit(1)

    else:  # Parent process
        os.close(w_stdout)
        os.close(w_stderr)
        fcntl.fcntl(r_stdout, fcntl.F_SETFL, fcntl.fcntl(r_stdout, fcntl.F_GETFL) | os.O_NONBLOCK)
        fcntl.fcntl(r_stderr, fcntl.F_SETFL, fcntl.fcntl(r_stderr, fcntl.F_GETFL) | os.O_NONBLOCK)

        stdout_output = []
        stderr_output = []
        start_time = time.time()

        try:
            while True:
                if timeout and (time.time() - start_time) > timeout:
                    os.kill(pid, signal.SIGKILL)
                    raise TimeoutError(f"Command '{command[0]}' timed out after {timeout} seconds")

                # Read from stdout
                try:
                    stdout_chunk = os.read(r_stdout, 4096)
                    if stdout_chunk:
                        stdout_output.append(stdout_chunk.decode())
                except OSError as e:
                    if e.errno != errno.EAGAIN:
                        raise

                # Read from stderr
                try:
                    stderr_chunk = os.read(r_stderr, 4096)
                    if stderr_chunk:
                        stderr_output.append(stderr_chunk.decode())
                except OSError as e:
                    if e.errno != errno.EAGAIN:
                        raise

                # Check if child has exited
                pid_exit, status = os.waitpid(pid, os.WNOHANG)
                if pid_exit == pid:
                    break
                time.sleep(0.01)  # Small sleep to avoid busy-waiting

        finally:
            os.close(r_stdout)
            os.close(r_stderr)

        # Convert output lists to strings
        stdout = ''.join(stdout_output)
        stderr = ''.join(stderr_output)
        return stdout, stderr, os.WEXITSTATUS(status) if pid_exit == pid else -1

# Example usage
try:
    stdout, stderr, status = run_command(['ls', '-l'], timeout=5)
    print("STDOUT:", stdout)
    print("STDERR:", stderr)
    print("STATUS:", status)
except TimeoutError as e:
    print(e)