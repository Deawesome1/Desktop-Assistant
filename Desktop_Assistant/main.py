from brain import Brain
from bot.runtime import run
import sys

def main():
    print("=== JARVIS RUNTIME ===")
    print("Python executable:", sys.executable)

    brain = Brain()
    run(debug=False, dry_run=False)

if __name__ == "__main__":
    main()
