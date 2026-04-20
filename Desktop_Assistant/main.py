# main.py — JARVIS runtime only
# stub
from brain import Brain
from bot.runtime import run


def main():
    brain = Brain()
    run(debug=False, dry_run=False)


if __name__ == "__main__":
    main()

# """
# main.py — Unified launcher for JARVIS (Omega)

# This file:
#     - Detects OS
#     - Creates the correct virtual environment
#     - Installs base + OS-specific requirements
#     - Initializes the Brain
#     - Starts the runtime loop
# """

# import os
# import sys
# import subprocess
# from commands.os_scanner import current_os
# from dependency_manager import install_requirements
# from bot.runtime import run
# from brain import Brain


# # ------------------------------------------------------------
# # Helper: run shell commands
# # ------------------------------------------------------------
# def sh(cmd):
#     print(f"→ {cmd}")
#     subprocess.check_call(cmd, shell=True)


# # ------------------------------------------------------------
# # Create virtual environment
# # ------------------------------------------------------------
# def create_venv():
#     """
#     Creates a venv folder depending on OS:
#         - venv_windows on Windows
#         - venv_macos on macOS
#     """

#     venv_name = "venv_windows" if current_os == "windows" else "venv_macos"
#     venv_path = os.path.join(os.getcwd(), venv_name)

#     if os.path.exists(venv_path):
#         print(f"✓ Virtual environment already exists: {venv_name}")
#         return venv_path

#     print(f"Creating virtual environment: {venv_name}")
#     sh(f"{sys.executable} -m venv {venv_name}")

#     return venv_path


# # ------------------------------------------------------------
# # Install requirements into the venv
# # ------------------------------------------------------------
# def install_into_venv(venv_path):
#     """
#     Installs requirements into the newly created venv.
#     """

#     pip_path = (
#         os.path.join(venv_path, "Scripts", "pip.exe")
#         if current_os == "windows"
#         else os.path.join(venv_path, "bin", "pip")
#     )

#     print(f"\nUsing pip at: {pip_path}")

#     # Install base + OS-specific requirements
#     install_requirements()

#     print("\n✓ Requirements installed successfully!")
#     return pip_path


# # ------------------------------------------------------------
# # Activate venv (instructions only)
# # ------------------------------------------------------------
# def print_activation_instructions(venv_path):
#     print("\nTo activate your virtual environment:")

#     if current_os == "windows":
#         print(f"  {venv_path}\\Scripts\\activate")
#     else:
#         print(f"  source {venv_path}/bin/activate")

#     print("\nThen run:")
#     print("  python main.py")


# # ------------------------------------------------------------
# # MAIN ENTRY POINT
# # ------------------------------------------------------------
# def main():
#     print(f"Detected OS: {current_os}")

#     # 1. Create venv
#     venv_path = create_venv()

#     # 2. Install requirements
#     install_into_venv(venv_path)

#     # 3. Initialize Brain
#     brain = Brain()

#     # 4. Start runtime
#     run(debug=False, dry_run=False)


# if __name__ == "__main__":
#     main()

