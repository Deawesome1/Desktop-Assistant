import inspect
import traceback

class CommandAdapter:
    def __init__(self, func, name):
        self.func = func
        self.name = name.lower()

    def __call__(self, brain, query=""):
        # Skip dangerous commands
        if "exit" in self.name or "shutdown" in self.name:
            return {
                "success": False,
                "message": f"Command '{self.name}' is disabled in demo mode.",
                "data": {"blocked": True},
            }

        try:
            sig = inspect.signature(self.func)
            argc = len(sig.parameters)

            # Most Omega commands use: run(brain, user_text, args=None, context=None)
            if argc >= 2:
                return self.func(brain, query)

            # Some older commands use: run(query)
            if argc == 1:
                return self.func(query)

            # Rare commands use: run()
            return self.func()

        except Exception as e:
            return {
                "success": False,
                "message": f"Command '{self.name}' failed.",
                "data": {
                    "error": str(e),
                    "trace": traceback.format_exc(),
                },
            }
