def speak(text: str, *, brain=None):
    print(f"JARVIS: {text}")


# """
# speaker_windows.py — Windows TTS using SAPI via pywin32.
# """

# import logging

# logger = logging.getLogger("jarvis.speaker.windows")

# try:
#     import win32com.client
#     _speaker = win32com.client.Dispatch("SAPI.SpVoice")
# except Exception as e:
#     _speaker = None
#     logger.warning(f"Windows TTS initialization failed: {e}")

# def speak(text: str, *, brain=None) -> None:
#     """
#     Speak text on Windows using SAPI if available.
#     Always prints to console as well.
#     """
#     print(f"JARVIS: {text}")
#     logger.info(f"SPEAK(win): {text}")

#     if _speaker is None:
#         return

#     try:
#         _speaker.Speak(text)
#     except Exception as e:
#         logger.warning(f"Windows TTS failed: {e}")

