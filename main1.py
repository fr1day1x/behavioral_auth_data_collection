import pygame
import sys
import random
import math

pygame.init()

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("BehaviorAuth")

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

targets_hit = 0
max_targets = 12

target_spawn_time = pygame.time.get_ticks()
last_click_time = 0

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and targets_hit < max_targets:
                mouse_x, mouse_y = event.pos
                target_x, target_y = grid_positions[active_target_index]
                
                distance = math.hypot(mouse_x - target_x, mouse_y - target_y)
                
                if distance <= 40:
                    current_time = pygame.time.get_ticks()
                    
                    reaction_time = current_time - target_spawn_time
                    print(f"Target {targets_hit + 1} - Reaction Latency: {reaction_time}ms")
                    
                    if targets_hit > 0:
                        inter_tap_interval = current_time - last_click_time
                        print(f"Target {targets_hit + 1} - Inter-tap Interval: {inter_tap_interval}ms")
                    
                    last_click_time = current_time
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
                        print("Round Complete!")
                        print("------------------")

    screen.fill((255, 255, 255))

    if targets_hit < max_targets:
        active_pos = grid_positions[active_target_index]
        pygame.draw.circle(screen, (0, 200, 0), active_pos, 40)
    else:
        font = pygame.font.Font(None, 48)
        text = font.render("Round Complete! Close window.", True, (0, 0, 0))
        text_rect = text.get_rect(center=(400, 300))
        screen.blit(text, text_rect)

    pygame.display.flip()

pygame.quit()
sys.exit()