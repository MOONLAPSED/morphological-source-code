import subprocess
import time

def run_command(command, timeout=None, env=None):
    """
    Executes a command in PowerShell on Windows, with timeout handling.

    Args:
        command (list): Command and arguments as a list, e.g., ['Get-Process']
        timeout (float): Timeout in seconds for the command to execute
        env (dict): Environment variables to set for the command

    Returns:
        tuple: stdout (str), stderr (str), exit_status (int)
    """
    # Ensure PowerShell is explicitly invoked on Windows
    command = ["powershell.exe", "-Command"] + command
    
    try:
        # Start the process using subprocess, with environment variables if provided
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )

        # Communicate with the process with a timeout to prevent freezing
        stdout, stderr = process.communicate(timeout=timeout)

        return stdout, stderr, process.returncode

    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()  # Capture any remaining output
        return stdout, stderr + "\nProcess timed out.", process.returncode

# Example usage
try:
    stdout, stderr, status = run_command(['Get-Process'], timeout=5)
    print("STDOUT:", stdout)
    print("STDERR:", stderr)
    print("STATUS:", status)
except Exception as e:
    print("Error:", e)
