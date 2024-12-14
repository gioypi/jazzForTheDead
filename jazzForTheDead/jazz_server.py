""" Server script for the "Jazz for the dead!" game.

Wait for a client from the local network to connect and play the game. Update the score on the database.
"""

import jazz_operations as jo
import socket
import sqlite3
from random import random
from math import sqrt, floor
from json import decoder
import pygame

FPS_CAP = 60
HOST = "0.0.0.0"                                    # Address used to listen to all possible connections on LAN.

delta_time = 1 / FPS_CAP                            # Not actual delta time, expects a stable frame rate.
immune_frames = jo.PLAYER_IMMUNE_DUR * FPS_CAP      # Number of frames that the player is immune to damage after a hit.


def start_gameplay():
    """ Transition from the menu to the gameplay screen. """
    global start_active
    global menu_screen
    global run
    global countdown_next_iter
    start_active = False
    try:
        conn.sendall("start".encode())
        countdown_next_iter = True
    except socket.error:
        print("Failed to send start signal to client.")
        run = False


def calculate_score():
    """ Calculate the score for the current level and add it to the total score of the team. Return the score of the
    finished level. """
    global score
    global enemies_killed
    global hp
    level_score = enemies_killed * jo.SLIME_POINTS + hp * jo.HP_POINTS
    score += level_score
    return level_score


def spawn_slime(all_slimes):
    """ Add a new slime on the list of enemies. """
    spawn_index = floor(random() * len(jo.levels[level_index].enemy_spawns))
    new_slime = [jo.levels[level_index].enemy_spawns[spawn_index], 0, False]
    all_slimes.append(new_slime)


def spawn_sword(all_swords):
    """ Add a new sword on the list of active swords. """
    new_index = floor(random() * jo.MAX_SWORDS)
    while new_index in all_swords:
        new_index = floor(random() * jo.MAX_SWORDS)
    jo.ding_sound.play()
    all_swords.append(new_index)


def get_distance(point1, point2):
    """ Calculate and return the distance between two given points. """
    return sqrt(((point2[0] - point1[0]) ** 2) + ((point2[1] - point1[1]) ** 2))


def move_slimes(all_slimes):
    """ Track the movement and animation of all enemies for the current game frame. """
    offset_x = 20
    offset_y = 90
    inertia_x = 30
    for slime in all_slimes:
        # Update animation frame.
        slime[1] += jo.ENEMY_ANIM_STEP
        if slime[1] > jo.slime_num_frames["walk"] - 1:
            slime[1] = 0
        # Choose the player that is closer.
        server_pos = (server_x, server_y)
        client_pos = (client_x, client_y)
        if get_distance(slime[0], server_pos) <= get_distance(slime[0], client_pos):
            goal_pos = server_pos
        else:
            goal_pos = client_pos
        # Calculate the new position.
        if goal_pos[0] + (offset_x * jo.PLAYER_SCALE) < slime[0][0]:
            # When the distance is smaller than the step, use a smaller step to avoid passing the player.
            new_x = slime[0][0] - min(enemy_vel, abs(slime[0][0] - goal_pos[0]))
            # Introduce inertia in turning the other way.
            if abs(slime[0][0] - goal_pos[0]) + (offset_x * jo.PLAYER_SCALE) > inertia_x:
                slime[2] = False
        else:
            new_x = slime[0][0] + min(enemy_vel, abs(slime[0][0] - goal_pos[0]))
            if abs(slime[0][0] - goal_pos[0]) + (offset_x * jo.PLAYER_SCALE) > inertia_x:
                slime[2] = True
        if goal_pos[1] + (offset_y * jo.PLAYER_SCALE) < slime[0][1]:
            new_y = slime[0][1] - min(enemy_vel, abs(slime[0][1] - goal_pos[1]))
        else:
            new_y = slime[0][1] + min(enemy_vel, abs(slime[0][1] - goal_pos[1]))
        slime[0] = (new_x, new_y)


def db_connect(db_path):
    """ Open a connection with a new database. """
    try:
        connection = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        print("Creating connection error: " + e.sqlite_errorname)
        raise SystemExit
    return connection


def execute_write_query(connection, query):
    """ Send an SQL-style query to a connected database. """
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
    except sqlite3.Error as e:
        print("Query execution error: " + e.sqlite_errorname)


def execute_read_query(connection, query):
    """ Send an SQL-style query that expects results to a connected database and return the response. """
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        result = cursor.fetchall()
    except sqlite3.Error as e:
        result = None
        print("Read query execution error: " + e.sqlite_errorname)
    return result


# Set-up network connection.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, jo.PORT))
s.listen(1)
conn = None

# Use this IP on the client to connect. Necessary to connect two machines over LAN.
private_ip = socket.gethostbyname(socket.gethostname())

# Initialize the highscore database.
db_conn = db_connect(jo.DATABASE_DIR + "highscore_db.sqlite")
sql_create_table = """
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        score INTEGER NOT NULL
    );
"""
execute_write_query(db_conn, sql_create_table)


# Pygame and variable initialization.
pygame.init()
screen = pygame.display.set_mode((jo.SCREEN_WIDTH, jo.SCREEN_HEIGHT), vsync=1)
pygame.display.set_caption("Jazz for the dead! - server")
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
share_ip_text = jo.dosis_font.render("You are the host. Share your IP with your teammate:", 1, jo.PINK)
share_ip_text_rect = share_ip_text.get_rect(center=(jo.width_center, 500))
ip_text = jo.dosis_font_large.render(private_ip, 1, jo.WHITE)
ip_text_rect = ip_text.get_rect(center=(jo.width_center, 640))
listen_text = jo.dosis_font.render("Listening for connections...", 1, jo.PINK)
listen_text_rect = listen_text.get_rect(center=(jo.width_center, 780))
name_prompt_text = jo.dosis_font.render("What's your team called?", 1, jo.PINK)
name_prompt_text_rect = name_prompt_text.get_rect(center=(jo.width_center, 500))
team_name = ""
input_active = False
server_role = ""       # Can either be 's' for skeleton or 'z' for zombie.
client_role = ""       # Can either be 's' for skeleton or 'z' for zombie.
start_button = pygame.image.load(jo.GRAPHICS_DIR + "start_button.png")
start_active = False
countdown_next_iter = False
countdown_active = False
hp = jo.FULL_HP         # Shared health for the team.
server_attacks = jo.INIT_ATTACKS
client_attacks = jo.INIT_ATTACKS
score = 0               # For all levels. Shared for the team.
enemies_killed = 0      # For the current level.
movement_active = False
attack_active = False
server_x, server_y = jo.START_POS_SERVER
client_x, client_y = jo.START_POS_CLIENT
looking_left = False
walking = False
attacking = False
simple_vel = jo.VEL_CONST * delta_time
diagonal_vel = sqrt(simple_vel * simple_vel / 2)    # Velocity for each axis when moving on both, to avoid speeding up.
enemy_vel = diagonal_vel * jo.ENEMY_VEL_MULT
velocity = simple_vel
walk_count = 0
idle_count = 0
attack_count = 0
server_anim_key = None
server_anim_index = None
client_anim_key = "idle"
client_anim_index = 0
server_flipped = False
client_flipped = False
slimes = []
swords = []
slimes_to_spawn = jo.levels[level_index].enemies_num
client_rect = None
client_immune = False
server_immune = False
client_can_kill = False
server_can_kill = False
client_immune_frame = 0
server_immune_frame = 0
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

        # Handle user input for the team name.
        if event.type == pygame.KEYDOWN and input_active:
            if (event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER) and len(team_name) > 0:
                input_active = False
                menu_screen += 1
                try:
                    conn.sendall(team_name.encode())
                    start_active = True
                except socket.error:
                    print("Failed to send team name to client.")
                    run = False
            elif event.key == pygame.K_BACKSPACE and len(team_name) > 0:
                team_name = team_name[:-1]
            elif len(team_name) < 25 and ((pygame.K_a <= event.key <= pygame.K_z) or event.key == pygame.K_SPACE):
                team_name += event.unicode

        # Event listener for the start button.
        if event.type == pygame.MOUSEBUTTONUP and (menu_screen == 3 or menu_screen == 4) and start_active:
            mouse_pos = pygame.mouse.get_pos()
            if start_button.get_rect(topleft=(jo.width_center - start_button.get_width() / 2, 780)). \
                    collidepoint(mouse_pos):
                start_gameplay()

    # Exit game when pressing escape.
    keys = pygame.key.get_pressed()
    if keys[pygame.K_ESCAPE]:
        run = False

    # Handle player actions.
    if keys[pygame.K_SPACE] and attack_active and server_attacks > 0:
        movement_active = False
        attack_active = False
        attacking = True
        server_can_kill = True
        walking = False
        jo.hit_miss_sound.play()
        server_attacks -= 1
    if (keys[pygame.K_LEFT] or keys[pygame.K_a]) and server_x > 40 and movement_active:
        looking_left = True
        walking = True
        walking_horiz = True
    elif ((keys[pygame.K_RIGHT] or keys[pygame.K_d]) and server_x < jo.SCREEN_WIDTH - (220 * jo.PLAYER_SCALE) - 40 and
          movement_active):
        looking_left = False
        walking = True
        walking_horiz = True
    else:
        walking_horiz = False
    if (keys[pygame.K_UP] or keys[pygame.K_w]) and server_y > 20 and movement_active:
        walking = True
        walking_vertic = True
    elif ((keys[pygame.K_DOWN] or keys[pygame.K_s]) and server_y < jo.SCREEN_HEIGHT - (350 * jo.PLAYER_SCALE) - 55 and
          movement_active):
        walking = True
        walking_vertic = True
    else:
        walking_vertic = False
    if walking_horiz and walking_vertic:
        velocity = diagonal_vel
    else:
        velocity = simple_vel
    if (keys[pygame.K_LEFT] or keys[pygame.K_a]) and server_x > 40 and movement_active:
        server_x -= velocity
    elif ((keys[pygame.K_RIGHT] or keys[pygame.K_d]) and server_x < jo.SCREEN_WIDTH - (220 * jo.PLAYER_SCALE) - 40 and
          movement_active):
        server_x += velocity
    if (keys[pygame.K_UP] or keys[pygame.K_w]) and server_y > 20 and movement_active:
        server_y -= velocity
    elif ((keys[pygame.K_DOWN] or keys[pygame.K_s]) and server_y < jo.SCREEN_HEIGHT - (350 * jo.PLAYER_SCALE) - 55 and
          movement_active):
        server_y += velocity
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
        screen.blit(share_ip_text, share_ip_text_rect)
        screen.blit(ip_text, ip_text_rect)
        screen.blit(listen_text, listen_text_rect)
    elif menu_screen == 2:      # Team name screen.
        screen.blit(name_prompt_text, name_prompt_text_rect)
        pygame.draw.rect(screen, jo.WHITE, (jo.width_center - 335, 640, 670, 70))
        team_name_text = jo.dosis_font_large.render(team_name + "_", 1, jo.BLACK)
        team_name_text_rect = team_name_text.get_rect(center=(jo.width_center, 674))
        screen.blit(team_name_text, team_name_text_rect)
        input_active = True
    elif menu_screen == 3:      # Start screen.
        if len(server_role) == 0:
            if random() < 0.5:
                server_role = "s"  # Server is playing skeleton.
                client_role = "z"  # Client is playing zombie.
            else:
                server_role = "z"  # Server is playing zombie.
                client_role = "s"  # Client is playing skeleton.
            try:
                conn.sendall(client_role.encode())
            except socket.error:
                print("Failed to send client role to client.")
                run = False
        jo.draw_start_menu(team_name, screen, server_role)
        if start_active:
            screen.blit(start_button, (jo.width_center - start_button.get_width() / 2, 780))
        if countdown_next_iter:
            countdown_next_iter = False
            countdown_active = True
        elif countdown_active:
            pygame.mixer.music.fadeout(1200)
            jo.countdown_from(jo.COUNTDOWN_SEC, screen)
            pygame.mixer.music.set_volume(jo.GAME_MUSIC_VOL)
            pygame.mixer.music.load(jo.SOUNDS_DIR + "level1_music.mp3")
            pygame.mixer.music.play(-1)
            countdown_active = False
            menu_screen = -1
            movement_active = True
            attack_active = True
    elif menu_screen == 4:      # Next level screen.
        # Show cursor.
        pygame.mouse.set_visible(True)
        # Calculate and communicate score.
        if partial_score is None:
            start_active = False
            countdown_next_iter = False
            countdown_active = False
            jo.victory_sound.play()
            partial_score = calculate_score()
            try:
                conn.sendall(str(partial_score).encode())
                start_active = True
            except socket.error:
                print("Failed to send level score to client.")
                run = False
        # Render UI elements.
        screen.blit(jo.level_cleared_text, jo.level_cleared_text_rect)
        partial_score_text = jo.dosis_font.render("Score: " + str(partial_score), 1, jo.PINK)
        partial_score_text_rect = partial_score_text.get_rect(center=(jo.width_center, 640))
        screen.blit(partial_score_text, partial_score_text_rect)
        if start_active:
            screen.blit(start_button, (jo.width_center - start_button.get_width() / 2, 780))
        if countdown_next_iter:
            countdown_next_iter = False
            countdown_active = True
        # Begin countdown to the next level.
        elif countdown_active:
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
            enemies_killed = 0
            server_x, server_y = jo.START_POS_SERVER
            client_x, client_y = jo.START_POS_CLIENT
            looking_left = False
            walking = False
            attacking = False
            walk_count = 0
            idle_count = 0
            attack_count = 0
            server_anim_key = None
            server_anim_index = 0
            client_anim_key = "idle"
            client_anim_index = 0
            server_flipped = False
            client_flipped = False
            slimes = []
            swords = []
            client_rect = None
            client_immune = False
            server_immune = False
            client_can_kill = False
            server_can_kill = False
            client_immune_frame = 0
            server_immune_frame = 0
            level_index += 1
            slimes_to_spawn = jo.levels[level_index].enemies_num
    elif menu_screen == 5:      # Leaderboard.
        # Show cursor.
        pygame.mouse.set_visible(True)
        if final_score is None:                     # Run only once.
            # Calculate and communicate score.
            calculate_score()
            final_score = score
            try:
                conn.sendall(str(final_score).encode())
                pygame.time.delay(200)      # Prevent merging with the next message.
            except socket.error:
                print("Failed to send total score to client.")
                run = False
            # Play the appropriate sound.
            if victorious:
                jo.victory_sound.play()
            else:
                jo.defeat_sound.play()
            # Access the database and update it, if appropriate.
            sql_select_team = """
                SELECT * FROM teams WHERE name = '""" + team_name + """';
            """
            team_entry = execute_read_query(db_conn, sql_select_team)
            if len(team_entry) == 0:
                sql_insert_team = """
                    INSERT INTO teams (name, score)
                        values
                        ('""" + team_name + """', """ + str(final_score) + """);
                """
                execute_write_query(db_conn, sql_insert_team)
            elif team_entry[0][2] < final_score:
                sql_update_team = """
                    UPDATE teams SET score = """ + str(final_score) + """ WHERE name = '""" + team_name + """';
                """
                execute_write_query(db_conn, sql_update_team)
            sql_select_top = """
                SELECT name, score FROM teams ORDER BY score DESC LIMIT 3;
            """
            top_teams = execute_read_query(db_conn, sql_select_top)
            sql_calculate_rank = """
                SELECT COUNT(*) FROM teams WHERE score >= """ + str(final_score) + """;
            """
            rank_result = execute_read_query(db_conn, sql_calculate_rank)
            team_rank = rank_result[0][0]       # Rank for this run's score, not the best score of the team.
            # Send data derived from the database to the client.
            db_data = jo.encode_db_data(top_teams, team_rank)
            try:
                conn.sendall(db_data)
            except socket.error:
                print("Failed to send database data to client.")
        # Render UI elements.
        jo.draw_leaderboard(top_teams, (team_rank, team_name, final_score), victorious, screen)
    elif menu_screen < 0:       # Actual gameplay.
        # Hide cursor.
        pygame.mouse.set_visible(False)
        # Take a chance at spawning enemies and swords.
        if slimes_to_spawn > 0 and random() < 0.25 * delta_time:
            spawn_slime(slimes)
            slimes_to_spawn -= 1
        if len(swords) < jo.MAX_SWORDS and random() < 0.07 * delta_time:
            spawn_sword(swords)
        # Update the slimes regarding NPC movement and animation.
        move_slimes(slimes)
        # Render UI elements.
        you_portrait_pos = (12, 4)
        mate_portrait_pos = (jo.SCREEN_WIDTH - jo.skeleton_portrait.get_width() - 12, 4)
        if server_role == "s":
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
        sword_text = jo.dosis_font_large.render(str(server_attacks), 1, jo.BLACK)
        screen.blit(sword_text, (146, 38))
        screen.blit(jo.sword_small, (1716, 43))
        teammate_sword_text = jo.dosis_font_large.render(str(client_attacks), 1, jo.BLACK)
        screen.blit(teammate_sword_text, (1683, 38))
        # Render sprites.
        if client_y <= server_y:
            client_rect = jo.draw_teammate(client_anim_key, client_anim_index, client_role, (client_x, client_y),
                                           client_flipped, screen)
        counts = (walk_count, idle_count, attack_count)
        flags = (looking_left, walking, attacking, movement_active, attack_active, server_immune)
        server_anim_key, server_anim_index, server_flipped, counts, flags, server_rect = (
            jo.draw_player(server_role, (server_x, server_y), screen, counts, flags))
        (walk_count, idle_count, attack_count) = counts
        (looking_left, walking, attacking, movement_active, attack_active, server_immune) = flags
        if client_y > server_y:
            client_rect = jo.draw_teammate(client_anim_key, client_anim_index, client_role, (client_x, client_y),
                                           client_flipped, screen)
        slime_rects = jo.draw_slimes(slimes, screen)
        sword_rects = jo.draw_swords(swords, level_index, screen)
        # Render low health effect, when appropriate.
        if hp == 1:
            screen.blit(jo.low_hp_fx, (0, 0))
        # Check if a sword was picked.
        for sword_rect in sword_rects:
            if client_rect.colliderect(sword_rect):
                swords.pop(sword_rects.index(sword_rect))
                sword_rects.remove(sword_rect)       # In case server and client touch the same sword at the same frame.
                break
        for sword_rect in sword_rects:
            if server_rect.colliderect(sword_rect):
                if server_attacks < jo.MAX_ATTACKS:
                    server_attacks += 1
                jo.sword_sound.play()
                swords.pop(sword_rects.index(sword_rect))
                break
        # Check if there is conflict with an enemy.
        for slime_rect in slime_rects:
            if client_rect.colliderect(slime_rect):
                if client_anim_key == "attack" and client_can_kill:                   # Kill an enemy.
                    client_can_kill = False
                    enemies_killed += 1
                    slimes.pop(slime_rects.index(slime_rect))
                    slime_rects.remove(slime_rect)  # In case server and client kill the same enemy at the same frame.
                elif not client_anim_key == "attack" and not client_immune:           # Take damage.
                    client_immune = True
                    client_immune_frame = 0
                    jo.damage_sound.play()
                    hp -= 1
                break
        for slime_rect in slime_rects:
            if server_rect.colliderect(slime_rect):
                if attacking and server_can_kill:                   # Kill an enemy.
                    server_can_kill = False
                    jo.hit_kill_sound.play()
                    enemies_killed += 1
                    slimes.pop(slime_rects.index(slime_rect))
                elif not attacking and not server_immune:           # Take damage.
                    server_immune = True
                    server_immune_frame = 0
                    jo.damage_sound.play()
                    hp -= 1
                break
        # Track immunity duration.
        if client_immune:
            client_immune_frame += 1
            if client_immune_frame >= immune_frames:
                client_immune = False
        if server_immune:
            server_immune_frame += 1
            if server_immune_frame >= immune_frames:
                server_immune = False
        # Check if the level or the game has ended.
        if hp <= 0 or enemies_killed >= jo.levels[level_index].enemies_num:
            stop_gameplay = True
    else:
        print("menu_screen value not recognized.")

    # Establish a connection with the client.
    if conn is None:
        pygame.display.update()     # The first frame will not be drawn otherwise.
        try:
            conn, addr = s.accept()
            # print("Connection established.")
            menu_screen += 1
        except socket.error:
            listen_text = jo.dosis_font.render("Failed to connect to client.", 1, jo.PINK)
            listen_text_rect = listen_text.get_rect(center=(jo.width_center, 780))
            screen.blit(listen_text, listen_text_rect)

    pygame.display.update()

    # Exchange information for the current game frame with the client.
    if menu_screen < 0 and server_anim_key is not None:     # Actual gameplay.
        frame_data = jo.encode_frame_data(server_anim_key, server_anim_index, server_flipped,
                                          (server_x, server_y), server_attacks, hp, slimes, swords, stop_gameplay)
        try:
            conn.sendall(frame_data)
        except socket.error:
            print("Failed to send frame update information to client.")
        try:
            frame_data = conn.recv(2048)
            new_client_anim_key, client_anim_index, client_flipped, (client_x, client_y), client_attacks = (
                jo.decode_frame_data(frame_data))[0:5]
            if new_client_anim_key == "attack" and client_anim_key != "attack":     # First frame of attack sequence.
                client_can_kill = True
            client_anim_key = new_client_anim_key
        except socket.error:                 # Will occur if the client shuts down mid-play.
            print("Failed to receive frame update information from client.")
        except decoder.JSONDecodeError:      # Will occur with an empty message.
            print("Failed to decode frame update information from client.")

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


# Clean-up and shut down.
try:
    conn.close()
except socket.error:
    print("Error closing connection.")
pygame.quit()
