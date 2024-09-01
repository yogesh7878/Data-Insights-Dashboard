import subprocess
import sys

def run_streamlit():
    script_path = "whole.py"
    command = f"streamlit run {script_path}"

    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_streamlit()
