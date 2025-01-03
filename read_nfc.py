import evdev


def main():
    print("Waiting for NFC UID...")

    # Specify the path to the input device
    input_device_path = "/dev/input/event4"  # Replace 'eventX' with the correct event number

    # Create an instance of the InputDevice class
    device = evdev.InputDevice(input_device_path)

    # Create a dictionary to map key codes to characters
    key_map = {
        2: '1', 3: '2', 4: '3', 5: '4', 6: '5',
        7: '6', 8: '7', 9: '8', 10: '9', 11: '0'
    }

    # Create an empty string to store the NFC UID
    nfc_uid = ""

    # Continuously read events from the input device
    for event in device.read_loop():
        # Check if the event is a key event
        if event.type == evdev.ecodes.EV_KEY:
            # Check if it's a key press
            if event.value == 1:
                # Translate the key code to a character
                key_code = event.code

                # Check if the key code is in the key map
                if key_code in key_map:
                    # Append the character to the NFC UID string
                    nfc_uid += key_map[key_code]

                # Check if Enter key is pressed
                if key_code == evdev.ecodes.KEY_ENTER:
                    # Print the NFC UID
                    print("NFC UID:", nfc_uid)

                    # Reset the NFC UID string
                    nfc_uid = ""


if __name__ == "__main__":
    main()
