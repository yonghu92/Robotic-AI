#!/usr/bin/env python3
"""
F310 Controller Test Script
Tests each button and axis individually
"""
import pygame
import time

def main():
    pygame.init()
    pygame.joystick.init()

    # Check for controllers
    count = pygame.joystick.get_count()
    if count == 0:
        print("ERROR: No controller found!")
        print("Make sure F310 is connected via USB")
        return

    # Initialize first controller
    js = pygame.joystick.Joystick(0)
    js.init()

    print("=" * 60)
    print(f"Controller: {js.get_name()}")
    print(f"Buttons: {js.get_numbuttons()}")
    print(f"Axes: {js.get_numaxes()}")
    print(f"Hats (D-pad): {js.get_numhats()}")
    print("=" * 60)
    print("\nMove sticks, press buttons, use triggers to test")
    print("Press Ctrl+C to exit\n")
    print("=" * 60)

    try:
        while True:
            pygame.event.pump()

            # Clear screen (works in most terminals)
            print("\033[H\033[J", end="")

            print("=" * 60)
            print("       F310 CONTROLLER TEST")
            print("=" * 60)

            # === AXES (Sticks and Triggers) ===
            print("\n--- STICKS & TRIGGERS ---")
            
            # Left Stick: axes 0 (X) and 1 (Y) - correct mapping
            if js.get_numaxes() >= 2:
                lx = js.get_axis(0)
                ly = js.get_axis(1)
                print(f"Left Stick:   X={lx:+.2f}  Y={ly:+.2f}", end="")
                if abs(lx) > 0.1 or abs(ly) > 0.1:
                    print("  <-- MOVING", end="")
                print()

            # Right Stick: axes 2 (X) and 3 (Y) - Linux mapping (flipped, Y inverted)
            # Always show right stick if we have at least axis 3
            if js.get_numaxes() >= 4:
                rx = js.get_axis(2)  # Right stick X (axis 2)
                ry = -js.get_axis(3)  # Right stick Y (axis 3, inverted)
                print(f"Right Stick:  X={rx:+.2f}  Y={ry:+.2f}", end="")
                if abs(rx) > 0.1 or abs(ry) > 0.1:
                    print("  <-- MOVING", end="")
                print()

            # Right Trigger: axis 5 - Linux mapping (if available)
            if js.get_numaxes() >= 6:
                rt = js.get_axis(5)
                print(f"Right Trigger (axis 5): {rt:+.2f}", end="")
                if rt > -0.9:
                    print("  <-- PRESSED", end="")
                print()

            # === D-PAD ===
            print("\n--- D-PAD ---")
            # D-Pad: reading from hat 0 - correct mapping
            if js.get_numhats() > 0:
                hat = js.get_hat(0)
                direction = ""
                if hat[1] == 1: direction += "UP "
                if hat[1] == -1: direction += "DOWN "
                if hat[0] == -1: direction += "LEFT "
                if hat[0] == 1: direction += "RIGHT "
                if direction:
                    print(f"D-Pad: {direction} <-- PRESSED")
                else:
                    print("D-Pad: (none)")

            # === BUTTONS ===
            print("\n--- BUTTONS ---")
            button_names = [
                "A (0)", "B (1)", "X (2)", "Y (3)",
                "LB (4)", "RB (5)", "Back (6)", "Start (7)",
                "L3 (8)", "R3 (9)", "Home (10)"
            ]

            pressed_buttons = []
            for i in range(min(js.get_numbuttons(), 11)):
                if js.get_button(i):
                    pressed_buttons.append(button_names[i] if i < len(button_names) else f"Btn {i}")

            if pressed_buttons:
                print(f"Pressed: {', '.join(pressed_buttons)}")
            else:
                print("Pressed: (none)")

            # Show all button states
            print("\nAll buttons: ", end="")
            for i in range(js.get_numbuttons()):
                if js.get_button(i):
                    print(f"[{i}]", end=" ")
                else:
                    print(f" {i} ", end=" ")
            print()

            # === RAW AXIS VALUES ===
            print("\n--- RAW AXIS VALUES ---")
            print("Axes: ", end="")
            for i in range(js.get_numaxes()):
                val = js.get_axis(i)
                print(f"[{i}]={val:+.2f}", end="  ")
            print()

            print("\n" + "=" * 60)
            print("Press Ctrl+C to exit")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nTest ended.")
        pygame.quit()

if __name__ == "__main__":
    main()
