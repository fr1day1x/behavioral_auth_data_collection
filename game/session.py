import random
import time
import pygame
from config import (
    TARGETS_PER_ROUND, TARGET_VISIBLE_DURATION,
    DELAY_MIN, DELAY_MAX, GRID_TOTAL,
    BACKGROUND_COLOR, WINDOW_WIDTH
)
from game.grid import build_grid, draw_grid, get_clicked_index, get_click_offset
from game.recorder import Recorder


class GameSession:
    """
    Manages a single round of the authentication game.
    Handles target sequencing, user input, and recording.
    """

    def __init__(self, surface, font):
        self.surface = surface
        self.font = font
        self.positions = build_grid()
        self.recorder = Recorder()

    def run_round(self, round_number=1, total_rounds=1):
        """
        Runs one complete round of TARGETS_PER_ROUND targets.
        Returns raw behavioral data from the Recorder.
        """
        self.recorder.reset()

        # Pick TARGETS_PER_ROUND random positions (no immediate repeats)
        target_sequence = self._generate_sequence()

        for i, target_idx in enumerate(target_sequence):
            # Random delay before showing next target
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            self._wait(delay)

            # Show target
            self.recorder.on_target_appear()
            target_hit = False
            appear_time = time.time()

            while not target_hit:
                # Check timeout
                if time.time() - appear_time > TARGET_VISIBLE_DURATION:
                    # Target expired without a hit — count as miss
                    self.recorder.on_incorrect_tap()
                    break

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        raise SystemExit

                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = event.pos
                        clicked = get_clicked_index(self.positions, mx, my)

                        if clicked == target_idx:
                            offset = get_click_offset(self.positions, target_idx, mx, my)
                            self.recorder.on_correct_tap(offset)
                            target_hit = True
                            self._draw(target_idx, flash_index=target_idx, flash_hit=True,
                                       progress=i + 1, round_number=round_number,
                                       total_rounds=total_rounds)
                            pygame.display.flip()
                            pygame.time.wait(150)  # brief hit flash
                        else:
                            self.recorder.on_incorrect_tap()
                            if clicked is not None:
                                self._draw(target_idx, flash_index=clicked, flash_hit=False,
                                           progress=i + 1, round_number=round_number,
                                           total_rounds=total_rounds)
                                pygame.display.flip()
                                pygame.time.wait(100)

                self._draw(target_idx if not target_hit else None,
                           progress=i + 1, round_number=round_number,
                           total_rounds=total_rounds)
                pygame.display.flip()

        return self.recorder.get_raw_data()

    def _generate_sequence(self):
        """Generates a sequence of TARGETS_PER_ROUND target indices with no immediate repeats."""
        sequence = []
        last = None
        all_indices = list(range(GRID_TOTAL))

        for _ in range(TARGETS_PER_ROUND):
            choices = [i for i in all_indices if i != last]
            chosen = random.choice(choices)
            sequence.append(chosen)
            last = chosen

        return sequence

    def _wait(self, seconds):
        """Waits for a given number of seconds while keeping the display blank of active targets."""
        self._draw(active_index=None)
        pygame.display.flip()
        start = time.time()
        while time.time() - start < seconds:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
            pygame.time.wait(10)

    def _draw(self, active_index=None, flash_index=None, flash_hit=True,
              progress=0, round_number=1, total_rounds=1):
        """Draws the full game frame."""
        self.surface.fill(BACKGROUND_COLOR)
        draw_grid(self.surface, self.positions, active_index, flash_index, flash_hit)

        # Status bar
        status = self.font.render(
            f"Round {round_number}/{total_rounds}   Target {progress}/{TARGETS_PER_ROUND}",
            True, (200, 200, 200)
        )
        self.surface.blit(status, (20, 15))
