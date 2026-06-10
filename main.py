import pygame
import sys
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, BACKGROUND_COLOR,
    ROUNDS_PER_ENROLLMENT, ROUNDS_PER_VERIFICATION
)
from game.session import GameSession
from auth.features import extract_features, average_vectors
from auth.template import save_template
from auth.matcher import authenticate


def get_participant_id(screen, font):
    """Simple text input screen to enter participant ID."""
    input_text = ""
    clock = pygame.time.Clock()

    while True:
        screen.fill(BACKGROUND_COLOR)
        prompt = font.render("Enter Participant ID (e.g. P001):", True, (200, 200, 200))
        entry = font.render(input_text + "|", True, (0, 200, 100))
        hint = font.render("Press ENTER to confirm", True, (120, 120, 120))

        screen.blit(prompt, (WINDOW_WIDTH // 2 - prompt.get_width() // 2, 250))
        screen.blit(entry, (WINDOW_WIDTH // 2 - entry.get_width() // 2, 320))
        screen.blit(hint, (WINDOW_WIDTH // 2 - hint.get_width() // 2, 400))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and input_text.strip():
                    return input_text.strip().upper()
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    input_text += event.unicode

        clock.tick(30)


def get_mode(screen, font):
    """Mode selection screen — Enroll or Verify."""
    clock = pygame.time.Clock()

    while True:
        screen.fill(BACKGROUND_COLOR)
        title = font.render("BehaviourAuth", True, (0, 200, 100))
        opt1 = font.render("Press E — Enroll", True, (200, 200, 200))
        opt2 = font.render("Press V — Verify", True, (200, 200, 200))
        opt3 = font.render("Press Q — Quit", True, (120, 120, 120))

        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 200))
        screen.blit(opt1, (WINDOW_WIDTH // 2 - opt1.get_width() // 2, 310))
        screen.blit(opt2, (WINDOW_WIDTH // 2 - opt2.get_width() // 2, 370))
        screen.blit(opt3, (WINDOW_WIDTH // 2 - opt3.get_width() // 2, 430))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    return "enroll"
                if event.key == pygame.K_v:
                    return "verify"
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

        clock.tick(30)


def show_message(screen, font, message, color=(200, 200, 200), duration=2000):
    """Displays a message for a set duration."""
    screen.fill(BACKGROUND_COLOR)
    text = font.render(message, True, color)
    screen.blit(text, (WINDOW_WIDTH // 2 - text.get_width() // 2, WINDOW_HEIGHT // 2))
    pygame.display.flip()
    pygame.time.wait(duration)


def run_enrollment(screen, font, participant_id):
    """Runs 3 rounds of enrollment and saves the averaged template."""
    session = GameSession(screen, font)
    vectors = []

    for round_num in range(1, ROUNDS_PER_ENROLLMENT + 1):
        show_message(screen, font,
                     f"Enrollment Round {round_num}/{ROUNDS_PER_ENROLLMENT} — Click to start",
                     duration=1500)
        raw = session.run_round(round_number=round_num, total_rounds=ROUNDS_PER_ENROLLMENT)
        vec = extract_features(raw)
        vectors.append(vec)
        print(f"[Enroll] Round {round_num} vector: {vec}")

    template = average_vectors(vectors)
    save_template(participant_id, template)
    show_message(screen, font, f"Enrollment complete for {participant_id}!",
                 color=(0, 200, 100), duration=2000)


def run_verification(screen, font, participant_id):
    """Runs 1 verification round and prints the authentication result."""
    session = GameSession(screen, font)
    show_message(screen, font, "Verification — Click to start", duration=1500)
    raw = session.run_round(round_number=1, total_rounds=1)
    live_vec = extract_features(raw)

    result, distance, threshold = authenticate(participant_id, live_vec)

    color = (0, 200, 100) if result else (200, 50, 50)
    msg = f"{'ACCEPTED' if result else 'REJECTED'} — Distance: {distance:.4f}"
    show_message(screen, font, msg, color=color, duration=3000)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("BehaviourAuth")
    font = pygame.font.SysFont("Arial", 24)

    while True:
        mode = get_mode(screen, font)
        participant_id = get_participant_id(screen, font)

        if mode == "enroll":
            run_enrollment(screen, font, participant_id)
        elif mode == "verify":
            run_verification(screen, font, participant_id)


if __name__ == "__main__":
    main()
