import subprocess
import sys

def get_installed_version(package_name):
    try:
        output = subprocess.check_output([sys.executable, '-m', 'pip', 'show', package_name], text=True)
        for line in output.splitlines():
            if line.startswith('Version:'):
                return line.split(' ')[-1]  # Return the version number
    except subprocess.CalledProcessError:
        return None  # Package is not installed

def check_dependencies(requirements_file='requirements.txt'):
    try:
        with open(requirements_file, 'r') as f:
            dependencies = f.read().splitlines()

        for dependency in dependencies:
            package_name, _, required_version = dependency.partition('==')
            
            installed_version = get_installed_version(package_name)
            
            if installed_version is None:
                print(f"{package_name} missing, trying to install it")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])  # Install latest version
            elif required_version and installed_version != required_version:
                print(f"{package_name} version mismatch (installed: {installed_version}, required: {required_version}). Trying to install the required version.")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', f"{package_name}=={required_version}"])

    except FileNotFoundError:
        print(f"Requirements file '{requirements_file}' not found.")
        sys.exit(1)
