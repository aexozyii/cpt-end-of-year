import keyboard, sys, etc


print("a")

keyboard.add_hotkey('spacebar', print, args=('The quick brown fox jumps over the lazy dog.'))
keyboard.add_hotkey('w', print, args=('triggered', 'hotkey'))
keyboard.wait('esc')

keyboard.wait()