""" Client script for the "Jazz for the dead!" game.

Connect to a server on the local network and play the game.
"""

import jazz_operations as jo
import socket
from ipaddress import IPv4Network
from math import sqrt
from json import decoder
import pygame

FPS_CAP = 60
# Keys that are allowed to be pressed during IP user input.
IP_CHARS = [pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7,
            pygame.K_8, pygame.K_9, pygame.K_KP0, pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP4,
            pygame.K_KP5, pygame.K_KP6, pygame.K_KP7, pygame.K_KP8, pygame.K_KP9, pygame.K_PERIOD, pygame.K_KP_PERIOD]

delta_time = 1 / FPS_CAP                            # Not actual delta time, expects a stable frame rate.
immune_frames = jo.PLAYER_IMMUNE_DUR * FPS_CAP      # Number of frames that the player is immune to damage after a hit.


def is_ipv4(string):
    """ Return 'True' if the given string is a valid IPv4 address or 'False' otherwise."""
    try:
        IPv4Network(string)
        return True
    except ValueError:
        return False


# Initialize connection with the server.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


# Pygame and variable initialization.
pygame.init()
screen = pygame.display.set_mode((jo.SCREEN_WIDTH, jo.SCREEN_HEIGHT), vsync=1)
pygame.display.set_caption("Jazz for the dead! - client")
clock = pygame.time.Clock()
# menu_screen ranges from '1' to '3' for the starting menu, '4' in-between levels and '5' for the leaderboard.
# Negative values indicate that the current screen is NOT a menu.
menu_screen = 1
level_index = 0
menu_bg = pygame.image.load(jo.GRAPHICS_DIR + "menu_bg.png")
level1_bg = pygame.image.load(jo.GRAPHICS_DIR + "level1.png")
level2_bg = pygame.image.load(jo.GRAPHICS_DIR + "level2.png")
menu_window = pygame.image.load(jo.GRAPHICS_DIR + "ui_window.png").convert_alpha()
menu_title = pygame.image.load(jo.GRAPHICS_DIR + "game_title.png").convert_alpha()
insert_ip_text = jo.dosis_font.render("Insert the host's IP to join:", 1, jo.PINK)
insert_ip_text_rect = insert_ip_text.get_rect(center=(jo.width_center, 500))
host_ip = ""
input_active = True
show_ip_error = False
ip_error_text = jo.dosis_font.render("Error", 1, jo.PINK)
wait_name_text = jo.dosis_font.render("The host is picking a team name...", 1, jo.PINK)
wait_name_text_rect = wait_name_text.get_rect(center=(jo.width_center, 640))
team_name = ""
client_role = ""       # Can either be 's' for skeleton or 'z' for zombie.
server_role = ""       # Can either be 's' for skeleton or 'z' for zombie.
hourglass = pygame.image.load(jo.GRAPHICS_DIR + "hourglass.png")
countdown_active = False
hp = jo.FULL_HP        # Shared health for the team.
server_attacks = jo.INIT_ATTACKS
client_attacks = jo.INIT_ATTACKS
movement_active = False
attack_active = False
server_x, server_y = jo.START_POS_SERVER
client_x, client_y = jo.START_POS_CLIENT
looking_left = True
walking = False
attacking = False
simple_vel = jo.VEL_CONST * delta_time
diagonal_vel = sqrt(simple_vel * simple_vel / 2)    # Velocity for each axis when moving on both, to avoid speeding up.
velocity = simple_vel
walk_count = 0
idle_count = 0
attack_count = 0
server_anim_key = "idle"
server_anim_index = 0
client_anim_key = None
client_anim_index = None
server_flipped = False
client_flipped = False
slimes = []
swords = []
sword_rects = []
slime_rects = []
client_rect = None
client_immune = False
client_can_kill = False
client_immune_frame = 0
stop_gameplay = False
victorious = False
partial_score = None
final_score = None
top_teams = []
team_rank = None

# Start playing menu music.
pygame.mixer.music.set_volume(jo.MENU_MUSIC_VOL)
pygame.mixer.music.load(jo.SOUNDS_DIR + "menu_music.mp3")
pygame.mixer.music.play(-1)


# Pygame loop.
run = True
while run:
    clock.tick(FPS_CAP)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

        # Handle user input for the host IP.
        if event.type == pygame.KEYDOWN and input_active:
            if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                input_active = False
                show_ip_error = False
                if is_ipv4(host_ip):
                    try:
                        s.connect((host_ip, jo.PORT))
                        # print("Connection established.")
                        menu_screen += 1
                    except socket.error:
                        ip_error_text = jo.dosis_font.render("Error: Host not found", 1, jo.PINK)
                        show_ip_error = True
                        input_active = True
                else:
                    ip_error_text = jo.dosis_font.render("Error: Invalid IP address", 1, jo.PINK)
                    show_ip_error = True
                    input_active = True
            elif event.key == pygame.K_BACKSPACE and len(host_ip) > 0:
                show_ip_error = False
                host_ip = host_ip[:-1]
            elif len(host_ip) < 15 and event.key in IP_CHARS:
                show_ip_error = False
                host_ip += event.unicode

    # Exit game when pressing escape.
    keys = pygame.key.get_pressed()
    if keys[pygame.K_ESCAPE]:
        run = False

    # Handle player actions.
    if keys[pygame.K_SPACE] and attack_active and client_attacks > 0:
        movement_active = False
        attack_active = False
        attacking = True
        client_can_kill = True
        walking = False
        jo.hit_miss_sound.play()
        client_attacks -= 1
    if (keys[pygame.K_LEFT] or keys[pygame.K_a]) and client_x > 40 and movement_active:
        looking_left = True
        walking = True
        walking_horiz = True
    elif ((keys[pygame.K_RIGHT] or keys[pygame.K_d]) and client_x < jo.SCREEN_WIDTH - (
            220 * jo.PLAYER_SCALE) - 40 and
          movement_active):
        looking_left = False
        walking = True
        walking_horiz = True
    else:
        walking_horiz = False
    if (keys[pygame.K_UP] or keys[pygame.K_w]) and client_y > 20 and movement_active:
        walking = True
        walking_vertic = True
    elif ((keys[pygame.K_DOWN] or keys[pygame.K_s]) and client_y < jo.SCREEN_HEIGHT - (
            350 * jo.PLAYER_SCALE) - 55 and
          movement_active):
        walking = True
        walking_vertic = True
    else:
        walking_vertic = False
    if walking_horiz and walking_vertic:
        velocity = diagonal_vel
    else:
        velocity = simple_vel
    if (keys[pygame.K_LEFT] or keys[pygame.K_a]) and client_x > 40 and movement_active:
        client_x -= velocity
    elif ((keys[pygame.K_RIGHT] or keys[pygame.K_d]) and client_x < jo.SCREEN_WIDTH - (
            220 * jo.PLAYER_SCALE) - 40 and
          movement_active):
        client_x += velocity
    if (keys[pygame.K_UP] or keys[pygame.K_w]) and client_y > 20 and movement_active:
        client_y -= velocity
    elif ((keys[pygame.K_DOWN] or keys[pygame.K_s]) and client_y < jo.SCREEN_HEIGHT - (
            350 * jo.PLAYER_SCALE) - 55 and
          movement_active):
        client_y += velocity
    if not walking_horiz and not walking_vertic:
        walk_count = 0
        walking = False

    # Render the background.
    if menu_screen > 0:
        bg = menu_bg
    elif level_index == 0:
        bg = level1_bg
    else:
        bg = level2_bg
    screen.blit(bg, (0, 0))

    # Render the elements of the current screen.
    if menu_screen > 0:         # Any menu.
        screen.blit(menu_window, jo.MENU_WIN_POS)
        screen.blit(menu_title, (0, 0))
    if menu_screen == 1:        # IP screen.
        screen.blit(insert_ip_text, insert_ip_text_rect)
        pygame.draw.rect(screen, jo.WHITE, (jo.width_center - 200, 640, 400, 70))
        host_ip_text = jo.dosis_font_large.render(host_ip + "_", 1, jo.BLACK)
        host_ip_text_rect = host_ip_text.get_rect(center=(jo.width_center, 674))
        screen.blit(host_ip_text, host_ip_text_rect)
        if show_ip_error:
            ip_error_text_rect = ip_error_text.get_rect(center=(jo.width_center, 780))
            screen.blit(ip_error_text, ip_error_text_rect)
    elif menu_screen == 2:      # Team name screen.
        screen.blit(wait_name_text, wait_name_text_rect)
        pygame.display.update()         # Show the updated screen before the blocking operation.
        try:
            team_name = s.recv(1024).decode()
            if len(team_name) > 0:      # If the server closes, the client might receive empty data.
                menu_screen += 1
        except socket.error:
            print("Failed to receive team name from server.")
            run = False
    elif menu_screen == 3:      # Start screen.
        if len(client_role) == 0:
            try:
                client_role = s.recv(1024).decode()
            except socket.error:
                print("Failed to receive client role from server.")
                run = False
        if len(client_role) > 0:        # If the server closes, the client might receive empty data.
            if client_role == "s":
                server_role = "z"
            else:
                server_role = "s"
            jo.draw_start_menu(team_name, screen, client_role)
            if not countdown_active:
                screen.blit(hourglass, (jo.width_center - hourglass.get_width() / 2, 780))
                pygame.display.update()
                try:
                    start_signal = s.recv(1024).decode()
                    if start_signal == "start":
                        countdown_active = True
                except socket.error:
                    print("Failed to receive start signal from server.")
                    run = False
            else:
                pygame.mixer.music.fadeout(1200)
                jo.countdown_from(jo.COUNTDOWN_SEC, screen)
                pygame.mixer.music.set_volume(jo.GAME_MUSIC_VOL)
                pygame.mixer.music.load(jo.SOUNDS_DIR + "level1_music.mp3")
                countdown_active = False
                menu_screen = -1
                movement_active = True
                attack_active = True
    elif menu_screen == 4:      # Next level screen.
        # Receive the level score from the server.
        if partial_score is None:
            countdown_active = False
            jo.victory_sound.play()
            try:
                partial_score = int(s.recv(1024).decode())
            except socket.error:
                print("Failed to receive level score from server.")
                run = False
        # Render UI elements.
        screen.blit(jo.level_cleared_text, jo.level_cleared_text_rect)
        partial_score_text = jo.dosis_font.render("Score: " + str(partial_score), 1, jo.PINK)
        partial_score_text_rect = partial_score_text.get_rect(center=(jo.width_center, 640))
        screen.blit(partial_score_text, partial_score_text_rect)
        if not countdown_active:
            screen.blit(hourglass, (jo.width_center - hourglass.get_width() / 2, 780))
            pygame.display.update()
            # Wait for the signal to start the next level.
            try:
                start_signal = s.recv(1024).decode()
                if start_signal == "start":
                    countdown_active = True
            except socket.error:
                print("Failed to receive start signal from server.")
                run = False
        # Begin countdown to the next level.
        else:
            jo.countdown_from(jo.COUNTDOWN_SEC, screen)
            pygame.mixer.music.load(jo.SOUNDS_DIR + "level2_music.mp3")
            pygame.mixer.music.play(-1)
            countdown_active = False
            menu_screen = -1
            movement_active = True
            attack_active = True
            # Reset gameplay and prepare the next level.
            hp = jo.FULL_HP
            server_attacks = jo.INIT_ATTACKS - 1
            client_attacks = jo.INIT_ATTACKS - 1
            server_x, server_y = jo.START_POS_SERVER
            client_x, client_y = jo.START_POS_CLIENT
            looking_left = False
            walking = False
            attacking = False
            walk_count = 0
            idle_count = 0
            attack_count = 0
            server_anim_key = "idle"
            server_anim_index = 0
            client_anim_key = None
            client_anim_index = 0
            server_flipped = False
            client_flipped = False
            slimes = []
            swords = []
            sword_rects = []
            slime_rects = []
            client_rect = None
            client_immune = False
            client_can_kill = False
            client_immune_frame = 0
            level_index += 1
    elif menu_screen == 5:      # Leaderboard.
        # Show cursor.
        pygame.mouse.set_visible(True)
        if final_score is None:                         # Run once.
            # Receive the total score from the server.
            try:
                final_score = int(s.recv(1024).decode())
            except socket.error:
                print("Failed to receive total score from server.")
                run = False
            # Play the appropriate sound.
            if victorious:
                jo.victory_sound.play()
            else:
                jo.defeat_sound.play()
            # Receive data derived from the database from the server.
            try:
                db_data = s.recv(2048)
                (top_teams, team_rank) = jo.decode_db_data(db_data)
            except socket.error:
                print("Failed to receive database data from server.")
                run = False
        # Render UI elements.
        jo.draw_leaderboard(top_teams, (team_rank, team_name, final_score), victorious, screen)
    elif menu_screen < 0:       # Actual gameplay.
        # Hide cursor.
        pygame.mouse.set_visible(False)
        # Render UI elements.
        you_portrait_pos = (12, 4)
        mate_portrait_pos = (jo.SCREEN_WIDTH - jo.skeleton_portrait.get_width() - 12, 4)
        if client_role == "s":
            screen.blit(jo.skeleton_portrait, you_portrait_pos)
            screen.blit(jo.zombie_portrait, mate_portrait_pos)
        else:
            screen.blit(jo.zombie_portrait, you_portrait_pos)
            screen.blit(jo.skeleton_portrait, mate_portrait_pos)
        for i in range(jo.FULL_HP):
            if i + 1 <= hp:
                heart = jo.full_heart
            else:
                heart = jo.broken_heart
            screen.blit(heart, (((jo.broken_heart.get_width() + 3) * i) + 676, 18))
        screen.blit(jo.sword_small, (180, 43))
        sword_text = jo.dosis_font_large.render(str(client_attacks), 1, jo.BLACK)
        screen.blit(sword_text, (146, 38))
        screen.blit(jo.sword_small, (1716, 43))
        teammate_sword_text = jo.dosis_font_large.render(str(server_attacks), 1, jo.BLACK)
        screen.blit(teammate_sword_text, (1683, 38))
        # Render sprites.
        if server_y <= client_y:
            jo.draw_teammate(server_anim_key, server_anim_index, server_role, (server_x, server_y), server_flipped,
                             screen)
        counts = (walk_count, idle_count, attack_count)
        flags = (looking_left, walking, attacking, movement_active, attack_active, client_immune)
        client_anim_key, client_anim_index, client_flipped, counts, flags, client_rect = (
            jo.draw_player(client_role, (client_x, client_y), screen, counts, flags))
        (walk_count, idle_count, attack_count) = counts
        (looking_left, walking, attacking, movement_active, attack_active, client_immune) = flags
        if server_y > client_y:
            jo.draw_teammate(server_anim_key, server_anim_index, server_role, (server_x, server_y), server_flipped,
                             screen)
        jo.draw_slimes(slimes, screen)
        jo.draw_swords(swords, level_index, screen)
        # Render low health effect, when appropriate.
        if hp == 1:
            screen.blit(jo.low_hp_fx, (0, 0))
    else:
        print("menu_screen value not recognized.")

    pygame.display.update()

    # Exchange information for the current game frame with the server.
    if menu_screen < 0 and client_anim_key is not None:     # Actual gameplay.
        try:
            frame_data = s.recv(2048)
            (server_anim_key, server_anim_index, server_flipped, (server_x, server_y), server_attacks, hp, slimes,
             new_swords, stop_gameplay) = jo.decode_frame_data(frame_data)
            if len(new_swords) > len(swords):
                jo.ding_sound.play()
            swords = new_swords
        except socket.error:                 # Will occur if the server shuts down mid-play.
            print("Failed to receive frame update information from server.")
        except decoder.JSONDecodeError:      # Will occur with an empty message.
            print("Failed to decode frame update information from server.")
        frame_data = jo.encode_frame_data(client_anim_key, client_anim_index, client_flipped,
                                          (client_x, client_y), client_attacks)
        try:
            s.sendall(frame_data)
        except socket.error:
            print("Failed to send frame update information to server.")

    # Handle transition from gameplay to next level screen or to end game screen.
    if stop_gameplay:
        stop_gameplay = False
        movement_active = False
        attack_active = False
        pygame.mixer.music.stop()
        if hp <= 0:                     # Game over.
            menu_screen = 5
            victorious = False
        elif level_index == 0:          # Level cleared.
            menu_screen = 4
        else:                           # Victory.
            menu_screen = 5
            victorious = True

    # Handle collisions with swords and enemies.
    # Must run after the frame data exchange with the server, otherwise it will trigger twice.
    if menu_screen < 0:     # Actual gameplay.
        # Check if a sword was picked.
        sword_rects = jo.draw_swords(swords, level_index, screen)   # Redraw to get the updated rectangles.
        for sword_rect in sword_rects:
            if client_rect.colliderect(sword_rect):
                if client_attacks < jo.MAX_ATTACKS:
                    client_attacks += 1
                jo.sword_sound.play()
                break

        # Check if there is conflict with an enemy.
        slime_rects = jo.draw_slimes(slimes, screen)                # Redraw to get the updated rectangles.
        for slime_rect in slime_rects:
            if client_rect.colliderect(slime_rect):
                if attacking and client_can_kill:                   # Kill an enemy.
                    client_can_kill = False
                    jo.hit_kill_sound.play()
                elif not attacking and not client_immune:           # Take damage.
                    client_immune = True
                    client_immune_frame = 0
                    jo.damage_sound.play()
                break

        # Track immunity duration.
        if client_immune:
            client_immune_frame += 1
            if client_immune_frame >= immune_frames:
                client_immune = False


# Clean-up and shut down.
try:
    s.close()
except socket.error:
    print("Error closing socket.")
pygame.quit()
