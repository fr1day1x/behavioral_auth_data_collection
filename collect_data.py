import pygame
import sys
import random
import math
import json
import os
import requests  # <-- Requires running 'pip install requests'
from datetime import datetime
from game.recorder import SessionRecorder

# Cyber-Research Palette
BG_COLOR = (14, 16, 22)          # Deep cosmic blue/black
TEXT_PRIMARY = (230, 235, 245)   # Ice white
TEXT_SECONDARY = (110, 120, 140) # Muted slate
TARGET_COLOR = (0, 200, 255)     # Deep neon cyan
TARGET_SHADOW = (0, 70, 100)     # Low glow aura
SUCCESS_COLOR = (0, 255, 120)    # Matrix green
ERROR_COLOR = (255, 60, 60)      # Alert Red

pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("BehaviorAuth - Distributed Research Harvester")
recorder = SessionRecorder()

font = pygame.font.SysFont('segoeui, helvetica, arial', 44, bold=True)
small_font = pygame.font.SysFont('segoeui, helvetica, arial', 24)

def get_grid_positions():
    positions = []
    start_x = 250
    start_y = 150
    spacing = 100
    for row in range(4):
        for col in range(4):
            positions.append((start_x + col * spacing, start_y + row * spacing))
    return positions

grid_positions = get_grid_positions()
active_target_index = random.randint(0, 15)

app_state = "MENU"  
participant_id = ""
status_msg = ""
status_is_error = False

targets_hit = 0
max_targets = 40  
rounds_completed = 0
max_rounds = 3    
all_sessions_raw = []

target_spawn_time = 0
last_click_time = 0
is_mouse_down = False
mouse_down_time = 0

running = True
while running:
    current_time = pygame.time.get_ticks()

    if app_state == "COLLECT" and targets_hit < max_targets:
        mx, my = pygame.mouse.get_pos()
        recorder.record_mouse_movement(current_time, mx, my)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if app_state == "MENU":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    participant_id = participant_id[:-1]
                elif event.key == pygame.K_RETURN and len(participant_id) > 0:
                    app_state = "COLLECT"
                    rounds_completed = 0
                    targets_hit = 0
                    all_sessions_raw = []
                    recorder.reset()
                    status_msg = ""
                    target_spawn_time = pygame.time.get_ticks()
                    last_click_time = target_spawn_time
                    is_mouse_down = False
                else:
                    if event.unicode.isalnum():
                        participant_id += event.unicode.upper()

        elif app_state == "COLLECT":
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and targets_hit < max_targets:
                    mouse_down_time = current_time
                    is_mouse_down = True

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and is_mouse_down and targets_hit < max_targets:
                    is_mouse_down = False
                    dwell_time = current_time - mouse_down_time
                    
                    mouse_x, mouse_y = event.pos
                    target_x, target_y = grid_positions[active_target_index]
                    distance = math.hypot(mouse_x - target_x, mouse_y - target_y)
                    
                    if distance <= 40:
                        reaction_time = mouse_down_time - target_spawn_time
                        x_offset = mouse_x - target_x
                        y_offset = mouse_y - target_y
                        
                        if targets_hit < 3:
                            print(f"Target {targets_hit + 1} [WARMUP] | Dwell: {dwell_time}ms")
                        elif targets_hit == 3:
                            print(f"Target {targets_hit + 1} [START] | RT: {reaction_time}ms | Dwell: {dwell_time}ms")
                            recorder.record_hit("First", reaction_time, 0, dwell_time, x_offset, y_offset)
                        else:
                            inter_tap_interval = mouse_down_time - last_click_time
                            
                            r1, c1 = previous_target_index // 4, previous_target_index % 4
                            r2, c2 = active_target_index // 4, active_target_index % 4
                            grid_dist = math.hypot(r2 - r1, c2 - c1)
                            
                            if grid_dist == 1.0: jump_type = "Adjacent"
                            elif grid_dist <= 1.5: jump_type = "Diagonal"
                            elif grid_dist <= 2.5: jump_type = "Medium"
                            else: jump_type = "Long"
                            
                            print(f"Target {targets_hit + 1} [{jump_type}] | RT: {reaction_time}ms | ITI: {inter_tap_interval}ms | Dwell: {dwell_time}ms")
                            recorder.record_hit(jump_type, reaction_time, inter_tap_interval, dwell_time, x_offset, y_offset)

                        previous_target_index = active_target_index
                        last_click_time = mouse_down_time
                        targets_hit += 1
                        
                        if targets_hit < max_targets:
                            screen.fill((255, 255, 255))
                            pygame.display.flip()
                            pygame.time.delay(random.randint(400, 1200))
                            
                            new_target = random.randint(0, 15)
                            while new_target == active_target_index:
                                new_target = random.randint(0, 15)
                            active_target_index = new_target
                            target_spawn_time = pygame.time.get_ticks()
                        else:
                            all_sessions_raw.append(recorder.get_raw_data())
                            rounds_completed += 1
                            
                            if rounds_completed < max_rounds:
                                targets_hit = 0
                                recorder.reset()
                                screen.fill((10, 25, 45))
                                pygame.display.flip()
                                pygame.time.delay(1500)
                                active_target_index = random.randint(0, 15)
                                target_spawn_time = pygame.time.get_ticks()
                                last_click_time = target_spawn_time
                            else:
                                # Packaging full data payload
                                payload = {
                                    "participant_id": participant_id,
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "sessions": all_sessions_raw
                                }
                                
                                # CHANGE THIS: Replace with your actual cloud backend URL once deployed
                                server_url = "http://localhost:8000/submit-session"
                                headers = {
                                    "X-Research-Token": "your_shared_secret_research_key_here",
                                    "Content-Type": "application/json"
                                }
                                
                                print("\n=== TRANSMITTING TELEMETRIC MATRIX ===")
                                try:
                                    response = requests.post(server_url, json=payload, headers=headers, timeout=10)
                                    if response.status_code == 200:
                                        print("[NETWORK SUCCESS] Data injected into database.")
                                        status_msg = f"Data safely logged for {participant_id}!"
                                        status_is_error = False
                                    else:
                                        raise requests.exceptions.RequestException(f"Server rejected ({response.status_code})")
                                except Exception as network_err:
                                    print(f"[NETWORK ERROR] {network_err} -> Activating emergency cache recovery...")
                                    
                                    # Emergency Fallback: Write immediately to localized backup text record
                                    backup_filename = f"emergency_backup_{participant_id}_{int(current_time)}.json"
                                    with open(backup_filename, "w") as backup_f:
                                        json.dump(payload, backup_f, indent=4)
                                        
                                    print(f"[CACHED SUCCESS] Local record saved safely as: {backup_filename}")
                                    status_msg = "Network failed! Saved backup locally."
                                    status_is_error = True
                                    
                                app_state = "MENU"
                    else:
                        recorder.record_miss()
                        print(f"Target {targets_hit + 1} - MISS REGISTERED!")
                        is_mouse_down = False

    # Render Interface Matrix
    screen.fill(BG_COLOR)
    if app_state == "MENU":
        lbl = font.render("Data Harvesting Engine", True, TEXT_PRIMARY)
        screen.blit(lbl, lbl.get_rect(center=(400, 160)))
        
        inp = small_font.render(f"Enter Subject ID: {participant_id}_", True, TARGET_COLOR)
        screen.blit(inp, inp.get_rect(center=(400, 280)))
        
        hint = small_font.render("Press [ENTER] to execute data acquisition", True, TEXT_SECONDARY)
        screen.blit(hint, hint.get_rect(center=(400, 360)))
        
        if status_msg:
            msg_color = ERROR_COLOR if status_is_error else SUCCESS_COLOR
            msg = small_font.render(status_msg, True, msg_color)
            screen.blit(msg, msg.get_rect(center=(400, 480)))
            
    elif app_state == "COLLECT" and targets_hit < max_targets:
        pos = grid_positions[active_target_index]
        pygame.draw.circle(screen, TARGET_SHADOW, pos, 44)
        pygame.draw.circle(screen, TARGET_COLOR, pos, 40)
        
        status = small_font.render(f"HARVESTING DATA - Profile: {participant_id} | Round {rounds_completed+1}/{max_rounds} | Target {targets_hit}/{max_targets}", True, TEXT_SECONDARY)
        screen.blit(status, (20, 20))

    pygame.display.flip()

pygame.quit()
sys.exit()