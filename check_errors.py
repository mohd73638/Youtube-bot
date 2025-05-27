import os
import subprocess

def run_checker():
    print("Running Pylint...\n")
    subprocess.run(["pylint", "."], check=False)

    print("\nRunning Syntax Check (compileall)...\n")
    subprocess.run(["python", "-m", "compileall", "."], check=False)

if __name__ == "__main__":
    run_checker()
