""" Library of functions, variables and constants used by jazz_server and jazz_client.

Screen resolution is considered static and is the same for server and client.
"""

import pygame
from math import floor
import json

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
PORT = 2000                     # Arbitrary, can be changed if used by another application.
GRAPHICS_DIR = "graphics/"
SOUNDS_DIR = "sounds/"
FONTS_DIR = "fonts/"
DATABASE_DIR = "database/"
SLIME_POINTS = 10               # Score for killing an enemy.
HP_POINTS = 20                  # Score for saving a heart until the end of a level.
FULL_HP = 5                     # Per team. Resets per level.
INIT_ATTACKS = 4                # Per player. Resets per level.
MAX_ATTACKS = 9                 # Per player.
MAX_SWORDS = 3                  # Available on the map at the same time.
FONT_SIZE_MEDIUM = 24
FONT_SIZE_LARGE = 48
MENU_WIN_POS = (451, 378)
COUNTDOWN_SEC = 3               # Time period (in seconds) before transitioning to gameplay, after pressing "start".
PLAYER_SCALE = 0.6
ENEMY_SCALE = 0.4
VEL_CONST = 280
ENEMY_VEL_MULT = 0.4
PLAYER_ANIM_STEP = 0.2          # Used to slow down the animation speed of the player sprites.
ENEMY_ANIM_STEP = 0.2           # Used to slow down the animation speed of the slime sprites.
START_POS_SERVER = (368, 800)   # Starting position for the server's player.
START_POS_CLIENT = (733, 800)   # Starting position for the client's player.
PLAYER_IMMUNE_DUR = 2.4         # Duration (in seconds) that the player has immunity to damage, after getting hit.
IMMUNE_ALPHA = 128
MENU_MUSIC_VOL = 0.6
GAME_MUSIC_VOL = 0.4

# RGB values used in the UI.
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
PINK = (170, 68, 115)


class Level:
    def __init__(self, enemies_num, enemy_spawns, sword_spawns):
        self.enemies_num = enemies_num         # Number of enemies to spawn during gameplay. Killing all wins the level.
        self.enemy_spawns = enemy_spawns       # Positions of possible spawn points for slimes.
        self.sword_spawns = sword_spawns       # Positions of possible spawn points for extra attacks.


width_center = SCREEN_WIDTH / 2
height_center = SCREEN_HEIGHT / 2
levels = [
    Level(10, [(36, 428), (1042, 129), (1764, 428)],
          [(471, 172), (1250, 228), (1310, 709)]),
    Level(15, [(994, 134), (1648, 134), (1648, 907)],
          [(52, 469), (1312, 168), (1189, 887)])
]


def draw_start_menu(team_name, screen, role):
    """ Prepare the 'start game' menu screen to be rendered.

    Parameters:
        team_name (string): The user-defined name of the team.
        screen (pygame.Surface): The caller's main pygame Surface.
        role (string): Either 's' for skeleton or 'z' for zombie.
    """

    team_name_text = dosis_font_large.render(team_name, 1, WHITE)
    team_name_text_rect = team_name_text.get_rect(center=(width_center, 450))
    screen.blit(team_name_text, team_name_text_rect)
    names_offset = 200
    names_height = 550
    you_text = dosis_font.render("You", 1, PINK)
    you_text_rect = you_text.get_rect(center=(width_center - names_offset, names_height))
    screen.blit(you_text, you_text_rect)
    mate_text = dosis_font.render("Teammate", 1, PINK)
    mate_text_rect = mate_text.get_rect(center=(width_center + names_offset, names_height))
    screen.blit(mate_text, mate_text_rect)
    you_portrait_pos = (width_center - names_offset - skeleton_portrait.get_width() / 2, names_height + 20)
    mate_portrait_pos = (width_center + names_offset - skeleton_portrait.get_width() / 2, names_height + 20)
    if role == "s":
        screen.blit(skeleton_portrait, you_portrait_pos)
        screen.blit(zombie_portrait, mate_portrait_pos)
    else:
        screen.blit(zombie_portrait, you_portrait_pos)
        screen.blit(skeleton_portrait, mate_portrait_pos)


def countdown_from(seconds, screen):
    """ Start a blocking countdown for the given amount of time, with visual and audio feedback.

    Parameters:
        seconds (int): Number of seconds to count down from.
        screen (pygame.Surface): The caller's main pygame Surface.
    """

    countdown = seconds
    while countdown > 0:
        countdown_text = dosis_font_large.render(str(countdown), 1, PINK)
        countdown_text_rect = countdown_text.get_rect(center=(width_center, 780))
        pygame.draw.rect(screen, BLACK, (width_center - 50, 780 - 50, 100, 100))    # Erase previous number.
        screen.blit(countdown_text, countdown_text_rect)
        pygame.display.update()
        ding_sound.play()
        pygame.time.delay(1000)
        countdown -= 1


def draw_player(role, pos, screen, counts, flags):
    """ Render the appropriate frame of the specified sprite.

    Parameters:
        role (string): Either 's' for skeleton or 'z' for zombie.
        pos (tuple of ints): Position where the sprite will be rendered.
        screen (pygame.Surface): Surface where the sprite will be rendered.
        counts (tuple of floats): Frame counters for all the animations.
        flags (tuple of booleans): Various states of the player.

    Returns:
        tuple of:
            dict_key (string): Key for the dictionary of animation lists, corresponding to the frame used.
            anim_index (int): Index of the frame used in its animation list.
            flipped (boolean): Whether the rendered frame was flipped horizontally.
            counts (tuple of floats): Updated counts.
            flags (tuple of booleans): Updated flags.
            rect (pygame.Rect): The rectangle of the rendered spite. Useful for collision handling.
    """

    walk_count = counts[0]
    idle_count = counts[1]
    attack_count = counts[2]
    looking_left = flags[0]
    walking = flags[1]
    attacking = flags[2]
    movement_active = flags[3]
    attack_active = flags[4]
    is_immune = flags[5]
    if role == "s":
        num_frames = skeleton_num_frames
        idle_anim = skeleton_idle
        walk_anim = skeleton_walk
        attack_anim = skeleton_attack
    else:
        num_frames = zombie_num_frames
        idle_anim = zombie_idle
        walk_anim = zombie_walk
        attack_anim = zombie_attack
    if walk_count + PLAYER_ANIM_STEP > num_frames["walk"]:
        walk_count = 0
    if idle_count + PLAYER_ANIM_STEP > num_frames["idle"]:
        idle_count = 0
    if attack_count + PLAYER_ANIM_STEP > num_frames["attack"]:
        attack_count = 0
        movement_active = True
        attack_active = True
        attacking = False
    if walking:
        dict_key = "walk"
        anim_index = floor(walk_count % (num_frames[dict_key] - 1))
        frame = walk_anim[anim_index]
        walk_count += PLAYER_ANIM_STEP
        idle_count = 0
        attack_count = 0
    elif attacking:
        dict_key = "attack"
        anim_index = floor(attack_count % (num_frames[dict_key] - 1))
        frame = attack_anim[anim_index]
        attack_count += PLAYER_ANIM_STEP
        idle_count = 0
        walk_count = 0
    else:
        dict_key = "idle"
        anim_index = floor(idle_count % (num_frames[dict_key] - 1))
        frame = idle_anim[anim_index]
        idle_count += PLAYER_ANIM_STEP
        walk_count = 0
        attack_count = 0
    transformed_frame = pygame.transform.scale(frame, (frame.get_width() * PLAYER_SCALE,
                                                       frame.get_height() * PLAYER_SCALE))
    # Flip the frame horizontally, if looking the other way than the original image files.
    flipped = False
    if not looking_left:
        transformed_frame = pygame.transform.flip(transformed_frame, True, False)
        flipped = True
    # Make semi-transparent, if under damage immunity.
    if is_immune:
        transformed_frame.fill((255, 255, 255, IMMUNE_ALPHA), special_flags=pygame.BLEND_RGBA_MULT)
    # Compensate for the horizontal offset of the attacking animation.
    if attacking and looking_left:
        new_pos = (pos[0] - 60, pos[1])
    else:
        new_pos = pos
    screen.blit(transformed_frame, new_pos)
    counts = (walk_count, idle_count, attack_count)
    flags = (looking_left, walking, attacking, movement_active, attack_active, is_immune)
    rect = transformed_frame.get_rect(topleft=new_pos)
    return dict_key, anim_index, flipped, counts, flags, rect


def encode_frame_data(anim_key, anim_index, flipped, pos, attacks, hp=None, slimes=None, swords=None, stop=False):
    """ Compose and encode the data for the current frame to send to the teammate, using a custom protocol.

    Parameters:
        anim_key (string): Dictionary key for the list of the animation used by the player.
        anim_index (int): Frame index for the animation list used by the player.
        flipped (boolean): Whether the rendered frame was flipped horizontally.
        pos (tuple of floats): The position of the frame on the screen.
        attacks (int): The number of available hits left.
        hp (int): Health points of the team.
        slimes (list of tuples): Data for each enemy currently in-game. Could be empty.
        swords (list of ints): Indexes of sword spawns of swords currently in-game. Could be empty.
        stop (boolean): Whether the gameplay must stop and the screen mode to change.

    Returns:
        (bytes): Data ready to be sent through the custom protocol.
    """

    var_dict = {
        "anim_key": anim_key,
        "anim_index": anim_index,
        "flipped": flipped,
        "pos": pos,
        "attacks": attacks,
        "hp": hp,
        "slimes": slimes,
        "swords": swords,
        "stop": stop
    }
    json_data = json.dumps(var_dict)
    return json_data.encode()


def decode_frame_data(frame_data):
    """ Decode and parse the data received from the teammate for the current frame, using a custom protocol.

    Parameters:
        frame_data (bytes): Data received through the custom protocol.

    Returns:
        tuple of:
            anim_key (string): Dictionary key for the list of the animation used by the player.
            anim_index (int): Frame index for the animation list used by the player.
            flipped (boolean): Whether the rendered frame was flipped horizontally.
            pos (tuple of floats): The position of the frame on the screen.
            attacks (int): The number of available hits left.
            hp (int): Health points of the team.
            slimes (list of tuples): Data for each enemy currently in-game. Could be empty.
            swords (list of ints): Indexes of sword spawns of swords currently in-game. Could be empty.
            stop (boolean): Whether the gameplay must stop and the screen mode to change.
    """

    json_data = frame_data.decode()
    var_dict = json.loads(json_data)
    anim_key = var_dict["anim_key"]
    anim_index = var_dict["anim_index"]
    flipped = var_dict["flipped"]
    pos = var_dict["pos"]
    attacks = var_dict["attacks"]
    hp = var_dict["hp"]
    slimes = var_dict["slimes"]
    swords = var_dict["swords"]
    stop = var_dict["stop"]
    return anim_key, anim_index, flipped, pos, attacks, hp, slimes, swords, stop


def draw_teammate(anim_key, anim_index, role, pos, flipped, screen):
    """ Render the specified frame of the specified animation.

    Parameters:
        anim_key (string): Dictionary key for the list of the animation used by the teammate.
        anim_index (int): Frame index for the animation list used by the teammate.
        role (string): Role of the teammate. Either "s" or "z".
        pos (tuple of floats): The position of the frame on the screen.
        flipped (boolean): Whether the frame is intended to be flipped horizontally.
        screen (pygame.Surface): Surface where the sprite will be rendered.

    Returns:
        rect (pygame.Rect): The rectangle of the rendered spite. Useful for collision handling.
    """

    if role == "s":
        teammate_anim = skeleton_anim[anim_key]
    else:
        teammate_anim = zombie_anim[anim_key]
    frame = teammate_anim[anim_index]
    transformed_frame = pygame.transform.scale(frame, (frame.get_width() * PLAYER_SCALE,
                                                       frame.get_height() * PLAYER_SCALE))
    if flipped:
        transformed_frame = pygame.transform.flip(transformed_frame, True, False)
    # Compensate for the horizontal offset of the attacking animation.
    if anim_key == "attack" and not flipped:
        new_pos = (pos[0] - 60, pos[1])
    else:
        new_pos = pos
    screen.blit(transformed_frame, new_pos)
    rect = transformed_frame.get_rect(topleft=new_pos)
    return rect


def draw_slimes(slimes, screen):
    """ Draw the specified animation frame at the specified position, repeatedly for all enemies.

    Parameters:
        slimes (list of tuples): Data for each enemy currently in-game. Could be empty.
        screen (pygame.Surface): Surface where the sprite will be rendered.

    Returns:
        rects (list of pygame.Rect): The rectangles of the rendered spites. Useful for collision handling.
    """

    rects = []
    for slime in slimes:
        frame = slime_walk[floor(slime[1])]
        frame = pygame.transform.scale(frame, (frame.get_width() * ENEMY_SCALE, frame.get_height() * ENEMY_SCALE))
        if slime[2]:
            frame = pygame.transform.flip(frame, True, False)
        screen.blit(frame, slime[0])
        rects.append(frame.get_rect(topleft=slime[0]))
    return rects


def draw_swords(swords, level_index, screen):
    """ Draw a sword at the specified position, repeatedly for all active swords.

    Parameters:
        swords (list of ints): Indexes of sword spawns of swords currently in-game. Could be empty.
        level_index (int): Index of the current level in the Levels[] list. Used to get the positions of sword spawns.
        screen (pygame.Surface): Surface where the sprite will be rendered.

    Returns:
        rects (list of pygame.Rect): The rectangles of the rendered spites. Useful for collision handling.
    """

    rects = []
    for sword in swords:
        pos = levels[level_index].sword_spawns[sword]
        screen.blit(sword_big, pos)
        rects.append(sword_big.get_rect(topleft=pos))
    return rects


def draw_leaderboard(top_teams, team_stats, victorious, screen):
    """ Draw the ranks, names and scores of the top teams and the playing team.

    Parameters:
        top_teams (list of tuples): Names (strings) and scores (ints) of the best teams, sorted by rank.
            The list should contain between one and three teams.
        team_stats (tuple): Rank (int), name (string) and score (int) of the playing team.
        victorious (boolean): Whether the game ended with a victory.
        screen (pygame.Surface): Surface where the text will be rendered.
    """
    x_coords = [530, 760, 1300]
    # Render window title.
    if victorious:
        end_title = "Victory!!!"
    else:
        end_title = "Game Over!"
    board_text = dosis_font_large.render(end_title, 1, WHITE)
    board_text_rect = board_text.get_rect(center=(width_center, 450))
    screen.blit(board_text, board_text_rect)
    # Render table titles.
    board_text = dosis_font.render("Rank", 1, WHITE)
    board_text_rect = board_text.get_rect(topleft=(x_coords[0], 520))
    screen.blit(board_text, board_text_rect)
    board_text = dosis_font.render("Team name", 1, WHITE)
    board_text_rect = board_text.get_rect(topleft=(x_coords[1], 520))
    screen.blit(board_text, board_text_rect)
    board_text = dosis_font.render("Score", 1, WHITE)
    board_text_rect = board_text.get_rect(topleft=(x_coords[2], 520))
    screen.blit(board_text, board_text_rect)
    # Render top teams.
    offset_y = 0
    rank = 1
    for team in top_teams:
        board_text = dosis_font.render("#" + str(rank), 1, PINK)
        board_text_rect = board_text.get_rect(topleft=(x_coords[0], 590 + offset_y))
        screen.blit(board_text, board_text_rect)
        board_text = dosis_font.render(team[0], 1, PINK)
        board_text_rect = board_text.get_rect(topleft=(x_coords[1], 590 + offset_y))
        screen.blit(board_text, board_text_rect)
        board_text = dosis_font.render(str(team[1]), 1, PINK)
        board_text_rect = board_text.get_rect(topleft=(x_coords[2], 590 + offset_y))
        screen.blit(board_text, board_text_rect)
        offset_y += 60
        rank += 1
    # Render playing team.
    board_text = dosis_font.render("#" + str(team_stats[0]), 1, WHITE)
    board_text_rect = board_text.get_rect(topleft=(x_coords[0], 830))
    screen.blit(board_text, board_text_rect)
    board_text = dosis_font.render(team_stats[1], 1, WHITE)
    board_text_rect = board_text.get_rect(topleft=(x_coords[1], 830))
    screen.blit(board_text, board_text_rect)
    board_text = dosis_font.render(str(team_stats[2]), 1, WHITE)
    board_text_rect = board_text.get_rect(topleft=(x_coords[2], 830))
    screen.blit(board_text, board_text_rect)


def encode_db_data(top_teams, team_rank):
    """ Compose and encode the database data to send to the client, using a custom protocol.

    Parameters:
        top_teams (list of tuples): Names (strings) and scores (ints) of the best teams, sorted by rank.
        team_rank (int): Rank of the playing team.

    Returns:
        (bytes): Data ready to be sent through the custom protocol.
    """

    var_dict = {
        "top_teams": top_teams,
        "team_rank": team_rank
    }
    json_data = json.dumps(var_dict)
    return json_data.encode()


def decode_db_data(db_data):
    """ Decode and parse the database data received from the server, using a custom protocol.

    Parameters:
        db_data (bytes): Data received through the custom protocol.

    Returns:
        tuple of:
            top_teams (list of tuples): Names (strings) and scores (ints) of the best teams, sorted by rank.
            team_rank (int): Rank of the playing team.
    """

    json_data = db_data.decode()
    var_dict = json.loads(json_data)
    top_teams = var_dict["top_teams"]
    team_rank = var_dict["team_rank"]
    return top_teams, team_rank


# Initialize and load assets.
pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    print("Error with sound. Does your system have an audio output device connected?")
    raise SystemExit
jo_screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), vsync=1)
dosis_font = pygame.font.Font(FONTS_DIR + "AkaAcidDosisRegular.otf", FONT_SIZE_MEDIUM)
dosis_font_large = pygame.font.Font(FONTS_DIR + "AkaAcidDosisRegular.otf", FONT_SIZE_LARGE)
skeleton_portrait = pygame.image.load(GRAPHICS_DIR + "skeleton_head.png").convert_alpha()
zombie_portrait = pygame.image.load(GRAPHICS_DIR + "zombie_head.png").convert_alpha()
ding_sound = pygame.mixer.Sound(SOUNDS_DIR + "ding.mp3")
hit_miss_sound = pygame.mixer.Sound(SOUNDS_DIR + "hit_miss.mp3")
hit_kill_sound = pygame.mixer.Sound(SOUNDS_DIR + "hit_kill.mp3")
full_heart = pygame.image.load(GRAPHICS_DIR + "full_heart.png").convert_alpha()
broken_heart = pygame.image.load(GRAPHICS_DIR + "broken_heart.png").convert_alpha()
sword_small = pygame.image.load(GRAPHICS_DIR + "sword_small.png").convert_alpha()
sword_big = pygame.image.load(GRAPHICS_DIR + "sword_big.png").convert_alpha()
low_hp_fx = pygame.image.load(GRAPHICS_DIR + "low_fx.png").convert_alpha()
sword_sound = pygame.mixer.Sound(SOUNDS_DIR + "sword.mp3")
damage_sound = pygame.mixer.Sound(SOUNDS_DIR + "damage.mp3")
victory_sound = pygame.mixer.Sound(SOUNDS_DIR + "victory.mp3")
defeat_sound = pygame.mixer.Sound(SOUNDS_DIR + "defeat.mp3")
level_cleared_text = dosis_font_large.render("Level cleared!", 1, WHITE)
level_cleared_text_rect = level_cleared_text.get_rect(center=(width_center, 500))
# Load the frames of the animations.
skeleton_num_frames = {"idle": 6, "walk": 8, "attack": 8}
zombie_num_frames = {"idle": 6, "walk": 10, "attack": 7}
slime_num_frames = {"walk": 12}      # Currently a single entry, but still a dictionary for consistency.
skeleton_idle = [pygame.image.load(GRAPHICS_DIR + f"skeleton/idle/idle_{i}.png").convert_alpha() for i in
                 range(1, skeleton_num_frames["idle"])]
skeleton_walk = [pygame.image.load(GRAPHICS_DIR + f"skeleton/walk/go_{i}.png").convert_alpha() for i in
                 range(1, skeleton_num_frames["walk"])]
skeleton_attack = [pygame.image.load(GRAPHICS_DIR + f"skeleton/attack/hit_{i}.png").convert_alpha() for i in
                   range(1, skeleton_num_frames["attack"])]
zombie_idle = [pygame.image.load(GRAPHICS_DIR + f"zombie/idle/idle_{i}.png").convert_alpha() for i in
               range(1, zombie_num_frames["idle"])]
zombie_walk = [pygame.image.load(GRAPHICS_DIR + f"zombie/walk/go_{i}.png").convert_alpha() for i in
               range(1, zombie_num_frames["walk"])]
zombie_attack = [pygame.image.load(GRAPHICS_DIR + f"zombie/attack/hit_{i}.png").convert_alpha() for i in
                 range(1, zombie_num_frames["attack"])]
slime_walk = [pygame.image.load(GRAPHICS_DIR + f"slime/go_{i}.png").convert_alpha() for i in
              range(1, slime_num_frames["walk"])]
skeleton_anim = {"idle": skeleton_idle, "walk": skeleton_walk, "attack": skeleton_attack}
zombie_anim = {"idle": zombie_idle, "walk": zombie_walk, "attack": zombie_attack}
