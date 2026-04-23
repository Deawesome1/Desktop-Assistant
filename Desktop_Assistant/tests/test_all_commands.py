from .faux.fake_brain import FakeBrain
from ..commands.command_hub import CommandHub
from Desktop_Assistant.tests.faux.faux_inputs import FAUX_INPUTS

def run_all_commands():
    print("=== Running JARVIS Command Tests ===\n")

    brain = FakeBrain()
    print("DEBUG: Loaded commands =", list(brain.commands.keys()))
    hub = CommandHub(brain, debug=False, dry_run=False)

    results = []

    for cmd_name, module in brain.commands.items():
        label = cmd_name
        faux_cases = FAUX_INPUTS.get(cmd_name, [cmd_name])

        for test_phrase in faux_cases:
            try:
                response = hub.execute(test_phrase)

                if response.get("success", False):
                    results.append((label, test_phrase, "PASS", None))
                else:
                    results.append((label, test_phrase, "FAIL",
                                    response.get("meta", {}).get("error_type", "unknown")))
            except Exception as e:
                results.append((label, test_phrase, "FAIL", str(e)))

    # Print results
    print("\n=== Test Results ===\n")
    for name, phrase, status, err in results:
        if status == "PASS":
            print(f"[PASS] {name:<20} | \"{phrase}\"")
        else:
            print(f"[FAIL] {name:<20} | \"{phrase}\" — {err}")

    passed = sum(1 for _, _, s, _ in results if s == "PASS")
    failed = sum(1 for _, _, s, _ in results if s == "FAIL")

    print("\n=== Summary ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total tests: {len(results)}")

if __name__ == "__main__":
    run_all_commands()
