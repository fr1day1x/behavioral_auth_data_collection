import pygame
import time
import json
import os

# --- Configuration ---
TARGET_PHRASE = "authenticator"
REQUIRED_ROUNDS = 5
OUTPUT_FILE = "keystroke_baseline.json"

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 400))
    pygame.display.set_caption("Keystroke Dynamics - Baseline Replication")
    font = pygame.font.Font(None, 36)
    clock = pygame.time.Clock()

    participant_id = input("Enter Subject ID in terminal before starting: ").strip().upper()

    session_data = {
        "participant_id": participant_id,
        "rounds": []
    }

    print(f"\n[SYSTEM] Switch to the Pygame window.")
    print(f"[SYSTEM] Type '{TARGET_PHRASE}' exactly as shown. Press ENTER when done.")

    running = True
    current_input = ""
    rounds_completed = 0
    
    # Tracking variables
    key_down_times = {}
    last_keyup_time = None
    
    current_round_dwells = []
    current_round_flights = []

    while running:
        screen.fill((14, 16, 22)) # Dark theme
        
        # UI Rendering
        prompt_surf = font.render(f"Type this phrase: {TARGET_PHRASE}", True, (0, 200, 255))
        input_surf = font.render(f"Your input: {current_input}", True, (230, 235, 245))
        round_surf = font.render(f"Rounds Completed: {rounds_completed}/{REQUIRED_ROUNDS}", True, (110, 120, 140))
        
        screen.blit(prompt_surf, (50, 100))
        screen.blit(input_surf, (50, 180))
        screen.blit(round_surf, (50, 300))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            elif event.type == pygame.KEYDOWN:
                now_ms = time.time() * 1000
                key_name = pygame.key.name(event.key)
                
                # Record initial press time for Dwell calculation
                key_down_times[key_name] = now_ms
                
                # Calculate Flight Time (Time since the LAST key was released)
                if last_keyup_time is not None and key_name != "return":
                    flight_time = now_ms - last_keyup_time
                    current_round_flights.append(round(flight_time, 2))
                
                if event.key == pygame.K_RETURN:
                    if current_input == TARGET_PHRASE:
                        # Save round data
                        session_data["rounds"].append({
                            "dwell_times": current_round_dwells.copy(),
                            "flight_times": current_round_flights.copy()
                        })
                        rounds_completed += 1
                        print(f"Round {rounds_completed} saved.")
                        
                        if rounds_completed >= REQUIRED_ROUNDS:
                            save_data(session_data)
                            running = False
                    else:
                        print("Error: Input did not match target phrase. Try again.")
                        
                    # Reset round variables
                    current_input = ""
                    current_round_dwells.clear()
                    current_round_flights.clear()
                    last_keyup_time = None
                    key_down_times.clear()
                    
                elif event.key == pygame.K_BACKSPACE:
                    current_input = current_input[:-1]
                else:
                    current_input += event.unicode

            elif event.type == pygame.KEYUP:
                now_ms = time.time() * 1000
                key_name = pygame.key.name(event.key)
                last_keyup_time = now_ms
                
                # Calculate Dwell Time (Key Up - Key Down)
                if key_name in key_down_times:
                    dwell_time = now_ms - key_down_times[key_name]
                    if key_name != "return":
                        current_round_dwells.append(round(dwell_time, 2))
                    del key_down_times[key_name]

        clock.tick(120)

    pygame.quit()

def save_data(data):
    file_exists = os.path.isfile(OUTPUT_FILE)
    
    # Append to JSON array if file exists, else create new
    if file_exists:
        with open(OUTPUT_FILE, "r") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []
        
    existing_data.append(data)
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(existing_data, f, indent=4)
    print(f"\n[SUCCESS] Baseline keystroke data written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()