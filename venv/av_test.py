from AppKit import NSBundle
from Foundation import NSObject
import AVFoundation

session = AVFoundation.AVAudioSession.sharedInstance()
err = session.setCategory_error_(AVFoundation.AVAudioSessionCategoryPlayAndRecord, None)
err = session.setActive_error_(True, None)

print("If you see this, AVAudioSession initialized successfully.")
