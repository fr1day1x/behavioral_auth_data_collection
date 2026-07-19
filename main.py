import pygame
import sys
import random
import math
import numpy as np
import os
import csv
from datetime import datetime
from game.recorder import SessionRecorder
from auth.features import extract_features
from auth.matcher import train_mahalanobis, authenticate

# Dark Mode Palette
BG_COLOR = (18, 18, 18)          # Deep charcoal/black
TEXT_PRIMARY = (240, 240, 240)   # Off-white
TEXT_SECONDARY = (150, 150, 150) # Muted gray
TARGET_COLOR = (0, 255, 170)     # Cyber-cyan
TARGET_SHADOW = (0, 100, 70)     # Dark cyan for depth
ERROR_COLOR = (255, 60, 60)      # Alert red
SUCCESS_COLOR = (40, 200, 80)    # Clean green

pygame.init()

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("BehaviorAuth")
recorder = SessionRecorder()
# Use standard system fonts for a cleaner look
font = pygame.font.SysFont('segoeui, helvetica, arial', 48, bold=True)
small_font = pygame.font.SysFont('segoeui, helvetica, arial', 28)

database = {}

# --- PARSE THE FLATTENED HIGH-DIMENSIONAL DATABASE ON STARTUP ---
if os.path.isfile('database.csv'):
    with open('database.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) > 1:
                p_id = row[0]
                
                # CHANGE THIS: Slice columns 1 to 15 (14 features) as the mean template
                template = np.array([float(x) for x in row[1:15]])

                # CHANGE THIS: Slice from column 15 onwards for the 14x14 matrix (196 elements)
                flat_matrix = np.array([float(x) for x in row[15:]])
                
                print("DEBUG: Raw matrix data type:", type(flat_matrix), "| Content length:", len(flat_matrix))
                inv_cov = flat_matrix.reshape(14, 14)
                
                database[p_id] = {"template": template, "inv_cov": inv_cov}

def get_grid_positions():
    positions = []
    start_x = 250
    start_y = 150
    spacing = 100
    for row in range(4):
        for col in range(4):
            x = start_x + col * spacing
            y = start_y + row * spacing
            positions.append((x, y))
    return positions

grid_positions = get_grid_positions()
active_target_index = random.randint(0, 15)

app_state = "MENU"  
participant_id = ""
verification_result_text = ""

targets_hit = 0
max_targets = 15  
rounds_completed = 0
max_rounds = 5  # Expanded to the optimized 5-round framework
enrollment_vectors = []

target_spawn_time = 0
last_click_time = 0

is_mouse_down = False
mouse_down_time = 0

running = True
while running:
    current_time = pygame.time.get_ticks()

    if app_state in ["ENROLL", "VERIFY"] and targets_hit < max_targets:
        mx, my = pygame.mouse.get_pos()
        recorder.record_mouse_movement(current_time, mx, my)


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if app_state == "MENU":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    participant_id = participant_id[:-1]
                elif event.key == pygame.K_e and len(participant_id) > 0:
                    if participant_id in database:
                        verification_result_text = f"ID {participant_id} exists! Pick another."
                    else:
                        app_state = "ENROLL"
                        max_rounds = 5
                        rounds_completed = 0
                        enrollment_vectors = []
                        targets_hit = 0
                        recorder.reset()
                        verification_result_text = ""
                        target_spawn_time = pygame.time.get_ticks()
                        last_click_time = target_spawn_time
                        is_mouse_down = False
                elif event.key == pygame.K_v and len(participant_id) > 0:
                    if participant_id in database:
                        app_state = "VERIFY"
                        max_rounds = 1
                        rounds_completed = 0
                        targets_hit = 0
                        recorder.reset()
                        verification_result_text = ""
                        target_spawn_time = pygame.time.get_ticks()
                        last_click_time = target_spawn_time
                        is_mouse_down = False
                    else:
                        verification_result_text = "ID not found! Enroll first."
                else:
                    if event.unicode.isalnum():
                        participant_id += event.unicode.upper()

        elif app_state in ["ENROLL", "VERIFY"]:
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
                            print(f"Target {targets_hit + 1} - WARMUP (Ignored) | Dwell: {dwell_time}ms")
                        elif targets_hit == 3:
                            print(f"Target {targets_hit + 1} - First Click | Reaction: {reaction_time}ms | Dwell: {dwell_time}ms")
                            recorder.record_hit("First", reaction_time, 0, dwell_time, x_offset, y_offset)
                        else:
                            inter_tap_interval = mouse_down_time - last_click_time
                            
                            r1 = previous_target_index // 4
                            c1 = previous_target_index % 4
                            r2 = active_target_index // 4
                            c2 = active_target_index % 4
                            grid_dist = math.hypot(r2 - r1, c2 - c1)
                            
                            if grid_dist == 1.0:
                                jump_type = "Adjacent"
                            elif grid_dist > 1.0 and grid_dist <= 1.5:
                                jump_type = "Diagonal"
                            elif grid_dist > 1.5 and grid_dist <= 2.5:
                                jump_type = "Medium"
                            else:
                                jump_type = "Long"
                            
                            print(f"Target {targets_hit + 1} - {jump_type} | Reaction: {reaction_time}ms | ITI: {inter_tap_interval}ms | Dwell: {dwell_time}ms")
                            recorder.record_hit(jump_type, reaction_time, inter_tap_interval, dwell_time, x_offset, y_offset)

                        previous_target_index = active_target_index
                        last_click_time = mouse_down_time
                        targets_hit += 1
                        
                        if targets_hit < max_targets:
                            screen.fill((255, 255, 255))
                            pygame.display.flip()
                            
                            delay_ms = random.randint(500, 1500)
                            pygame.time.delay(delay_ms)
                            
                            new_target = random.randint(0, 15)
                            while new_target == active_target_index:
                                new_target = random.randint(0, 15)
                            active_target_index = new_target
                            target_spawn_time = pygame.time.get_ticks()
                            
                        else:
                            raw_data = recorder.get_raw_data()
                            feature_vector = extract_features(raw_data)
                            
                            dist_score = "N/A" 
                            result_status = "ENROLLING"
                            
                            if app_state == "VERIFY":
                                stored_data = database[participant_id]
                                stored_template = stored_data["template"]
                                inv_cov_matrix = stored_data["inv_cov"]
                                
                                # Verification now executes regularized Mahalanobis evaluations
                                is_match, dist_score = authenticate(feature_vector, stored_template, inv_cov_matrix, threshold=5)
                                
                                if is_match:
                                    result_status = "ACCEPTED"
                                    verification_result_text = f"ACCEPTED! Score: {dist_score:.3f}"
                                    print(f"ACCEPTED! Score: {dist_score}")
                                else:
                                    result_status = "REJECTED"
                                    verification_result_text = f"REJECTED! Score: {dist_score:.3f}"
                                    print(f"REJECTED! Score: {dist_score}")
                            
                            file_exists = os.path.isfile('session_logs.csv')
                            with open('session_logs.csv', 'a', newline='') as f:
                                writer = csv.writer(f)
                                if not file_exists:
                                    writer.writerow(['Timestamp', 'Participant_ID', 'Mode', 'Round_Num', 
                                                     'RT_Adj', 'RT_Diag', 'RT_Med', 'RT_Long', 
                                                     'ITI_Adj', 'ITI_Diag', 'ITI_Med', 'ITI_Long',
                                                     'DWL_Adj', 'DWL_Diag', 'DWL_Med', 'DWL_Long',
                                                     'X_Mean', 'X_Std', 'X_Med', 'Y_Mean', 'Y_Std', 'Y_Med', 'Errors',
                                                     'Distance_Score', 'Result'])
                                
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                writer.writerow([timestamp, participant_id, app_state, rounds_completed + 1] + 
                                                [round(num, 3) for num in feature_vector.tolist()] + 
                                                [dist_score, result_status])
                            
                            if app_state == "ENROLL":
                                enrollment_vectors.append(feature_vector)
                                print(f"--- ROUND {rounds_completed + 1} VECTOR ---")
                                print(np.round(feature_vector, 3))
                                
                                rounds_completed += 1
                                
                                if rounds_completed < max_rounds:
                                    targets_hit = 0
                                    recorder.reset()
                                    screen.fill((10, 40, 20))
                                    pygame.display.flip()
                                    pygame.time.delay(2000) 
                                    
                                    active_target_index = random.randint(0, 15)
                                    target_spawn_time = pygame.time.get_ticks()
                                    last_click_time = target_spawn_time
                                    is_mouse_down = False
                                else:
                                    print("\n=== ENROLLMENT COMPLETE ===")
                                    # 1. Compute regularized matrix transformation data
                                    final_template, inv_cov_matrix = train_mahalanobis(enrollment_vectors)
                                    
                                    # 2. Commit to RAM database mapping
                                    database[participant_id] = {"template": final_template, "inv_cov": inv_cov_matrix}
                                    
                                    # 3. Flatten 19x19 matrix to a 361-element array and append to disk
                                    flat_inv_cov = inv_cov_matrix.flatten().tolist()
                                    with open('database.csv', 'a', newline='') as f:
                                        writer = csv.writer(f)
                                        writer.writerow([participant_id] + final_template.tolist() + flat_inv_cov)
                                        
                                    verification_result_text = f"Enrolled {participant_id} successfully!"
                                    app_state = "MENU"
                            
                            elif app_state == "VERIFY":
                                app_state = "MENU"
                    else:
                        recorder.record_miss()
                        print(f"Target {targets_hit + 1} - MISS REGISTERED!")
                        is_mouse_down = False

    if app_state in ["ENROLL", "VERIFY"] and targets_hit < max_targets:
        if current_time - target_spawn_time > 2000: 
            print(f"Target {targets_hit + 1} - TIMEOUT!")
            recorder.record_miss()
            screen.fill((40, 10, 10))
            pygame.display.flip()
            pygame.time.delay(150)
            
            new_target = random.randint(0, 15)
            while new_target == active_target_index:
                new_target = random.randint(0, 15)
            active_target_index = new_target
            target_spawn_time = pygame.time.get_ticks()
            last_click_time = target_spawn_time 
            is_mouse_down = False

    screen.fill((255, 255, 255))

    # ==========================================
    # RENDERING
    # ==========================================
    screen.fill(BG_COLOR)

    if app_state == "MENU":
        # Title
        title = font.render("Behavior Authentication", True, TEXT_PRIMARY)
        title_rect = title.get_rect(center=(400, 150))
        screen.blit(title, title_rect)
        
        # ID Input Box
        id_text = small_font.render(f"Participant ID: {participant_id}_", True, TARGET_COLOR)
        id_rect = id_text.get_rect(center=(400, 270))
        screen.blit(id_text, id_rect)
        
        # Instructions
        inst_text = small_font.render("Press [E] to Enroll  |  Press [V] to Verify", True, TEXT_SECONDARY)
        inst_rect = inst_text.get_rect(center=(400, 360))
        screen.blit(inst_text, inst_rect)
        
        # Results/Feedback
        # Color dynamically based on success/fail
        res_color = ERROR_COLOR if "REJECTED" in verification_result_text or "exists" in verification_result_text else SUCCESS_COLOR
        res_text = small_font.render(verification_result_text, True, res_color)
        res_rect = res_text.get_rect(center=(400, 480))
        screen.blit(res_text, res_rect)

    elif app_state in ["ENROLL", "VERIFY"]:
        if targets_hit < max_targets:
            active_pos = grid_positions[active_target_index]
            
            # Draw a subtle "shadow/glow" slightly larger than the target
            pygame.draw.circle(screen, TARGET_SHADOW, active_pos, 44)
            # Draw the crisp inner target
            pygame.draw.circle(screen, TARGET_COLOR, active_pos, 40)
            
            # UI Overlay
            mode_text = "ENROLLMENT" if app_state == "ENROLL" else "VERIFICATION"
            prog_text = small_font.render(f"{mode_text} - Round {rounds_completed+1}/{max_rounds}  |  Target {targets_hit}/{max_targets}", True, TEXT_SECONDARY)
            screen.blit(prog_text, (20, 20))

    pygame.display.flip()

pygame.quit()
sys.exit()