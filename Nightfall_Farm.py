# =============================================================================
# Nightfall Farm — A 3D OpenGL Farm Game
# =============================================================================

# ---------------------------------------------------------------------------
# 1. IMPORTS
# ---------------------------------------------------------------------------
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import os

# ---------------------------------------------------------------------------
# 2. GLOBAL CONSTANTS
# ---------------------------------------------------------------------------
WINDOW_W = 1000
WINDOW_H = 800
GRID_LENGTH = 800
GRID_SIZE = 12
PLOT_SIZE = 60
DAY_SPEED = 0.001
ENEMY_SPAWN_INTERVAL = 300
POND_POS = [250, 0, 250]
POND_RADIUS = 150
FARM_OFFSET_X = 250
FARM_OFFSET_Z = -250

MENU_ITEMS = ["Farm", "Inventory", "Crafting", "Quit"]

RECIPES = {
    "bread":  {"ingredients": {"wheat": 3}, "produces": "bread", "food_value": 20},
    "stew":   {"ingredients": {"corn": 2, "berry": 1}, "produces": "stew", "food_value": 35},
}

WEATHER_TRANSITIONS = {
    "clear": ["clear", "rain"],
    "rain":  ["rain", "clear"],
}

# ---------------------------------------------------------------------------
# 3. GLOBAL STATE VARIABLES
# ---------------------------------------------------------------------------
# Cached quadric — created once in main()
QUADRIC = None

# Camera
camera_angle = 0.0
camera_radius = 300.0
camera_height = 250.0
fovY = 60
first_person = False

# Day-Night
game_time = 8.0
is_night = False
night_factor = 1.0

# Weather
weather_state = "clear"
weather_timer = 2000.0
rain_particles = []

# Player
player_pos = [0.0, 0.0, -350.0]
player_angle = 0.0
player_speed = 15.0
player_dead = False
player_health = 100
player_currency = 0

# Weapon
weapon_level = 1
weapon_angle = 0.0
bullets = []

# Farm
farm_plots = []
farm_expansion_level = 1
carrot_plots = [{"x": -350 + (i - 1) * PLOT_SIZE, "z": -350 + (j - 1) * PLOT_SIZE, "active": True, "timer": 0} 
                for i in range(3) for j in range(3)]

# Enemies
enemies = []
enemy_spawn_timer = 0.0

# Villagers
villagers = [
    {"pos": [-300, 0, -200], "trade_active": False, "name": "Mira",
     "trade": ("5 wheat -> 3 corn", "wheat", 5, "corn", 3)},
    {"pos": [150, 0, -200], "trade_active": False, "name": "Bram",
     "trade": ("3 corn -> 1 fire_stone", "corn", 3, "fire_stone", 1)},
    {"pos": [-150, 0, 100], "trade_active": False, "name": "Lena",
     "trade": ("5 berry -> 1 water_crystal", "berry", 5, "water_crystal", 1)},
]
current_trader = None

# Fishing
fishing_active = False
fishing_line_cast = False
fishing_timer = 0.0
fish_caught = 0
fish_on = False

# Crafting
inventory = {"wheat": 0, "corn": 0, "berry": 0, "wood": 0,
             "water_crystal": 0, "fire_stone": 0, "plank": 0, "bow": 0}
cooked_food = {"bread": 0, "stew": 0}

# Auto-fire
auto_fire = False
auto_fire_timer = 0

# Menu
menu_open = False
menu_selected = 0
game_state = "play" 
hud_message = ""
hud_message_timer = 0
crafting_selected = 0
trading_selected = 0
inventory_selected = 0
death_selected = 0  

# Stars
STAR_POSITIONS = []
for _i in range(300):
    angle = random.uniform(0, 2 * math.pi)
    height = random.uniform(100, 1000)
    radius = random.uniform(1000, 1500)
    sx = math.cos(angle) * radius
    sz = math.sin(angle) * radius
    STAR_POSITIONS.append((sx, height, sz))

# Clouds
clouds = []
for _i in range(30):
    clouds.append({
        "x": random.uniform(-1500, 1500),
        "y": random.uniform(300, 600),
        "z": random.uniform(-1500, 1500),
        "size": random.uniform(40, 100)
    })

# Rain particles init
for _i in range(500):
    rain_particles.append([random.uniform(-GRID_LENGTH, GRID_LENGTH), random.uniform(0, 500), random.uniform(-GRID_LENGTH, GRID_LENGTH)])

# Storm flash
storm_flash_timer = 0

# ---------------------------------------------------------------------------
# 4. HELPER / UTILITY FUNCTIONS
# ---------------------------------------------------------------------------

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def get_sky_color():
    t = game_time
    if 6.0 <= t < 8.0:
        f = (t - 6.0) / 2.0
        return (1.0 - 0.6 * f, 0.5 + 0.1 * f, 0.2 + 0.7 * f)
    elif 8.0 <= t < 18.0:
        return (0.4, 0.6, 0.9)
    elif 18.0 <= t < 20.0:
        f = (t - 18.0) / 2.0
        return (1.0 - 0.98 * f, 0.4 - 0.38 * f, 0.1 - 0.0 * f)
    else:
        return (0.02, 0.02, 0.1)


def weapon_damage():
    if weapon_level == 1:
        return 5
    elif weapon_level == 2:
        return 8
    return 15


def distance(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)


def hut_wall_collision(px, pz):
    """Returns True if position (px, pz) collides with hut walls (not the door)."""
    hx, hz = -350, 350
    half = 50
    margin = 10  # player radius
    # Check if inside hut bounds (expanded by margin)
    in_x = (hx - half - margin) < px < (hx + half + margin)
    in_z = (hz - half - margin) < pz < (hz + half + margin)
    if not in_x or not in_z:
        return False
    # Already fully inside the hut — allow movement
    if (hx - half + margin) < px < (hx + half - margin) and (hz - half + margin) < pz < (hz + half - margin):
        return False
    # Near the door opening (+Z face, x between -15 and 15) — allow entry
    if pz > (hz + half - margin) and (hx - 15) < px < (hx + 15):
        return False
    # Otherwise colliding with a wall
    return True


def get_night_factor():
    t = game_time
    if 8.0 <= t < 18.0:
        return 1.0
    elif 18.0 <= t < 20.0:
        f = (t - 18.0) / 2.0
        return 1.0 - 0.7 * f
    elif 6.0 <= t < 8.0:
        f = (t - 6.0) / 2.0
        return 0.3 + 0.7 * f
    else:
        return 0.3


# ---------------------------------------------------------------------------
# 5. DRAW FUNCTIONS
# ---------------------------------------------------------------------------

def draw_sky():
    # Draws a background sky quad
    r, g, b = get_sky_color()
    glPushMatrix()
    glBegin(GL_QUADS)
    glColor3f(r, g, b)
    glVertex3f(-1500, -200, -1400)
    glVertex3f(1500, -200, -1400)
    glVertex3f(1500, 1000, -1400)
    glVertex3f(-1500, 1000, -1400)
    glEnd()
    glPopMatrix()


def draw_sun_moon():
    # Draws sun during day, moon at night
    angle = (game_time / 24.0) * 360.0
    sx = 800 * math.cos(math.radians(angle))
    sy = 800 * math.sin(math.radians(angle))
    glPushMatrix()
    if sy > 0:
        glTranslatef(sx, sy, -600)
        glColor3f(1.0, 0.9, 0.2)
        gluSphere(QUADRIC, 40, 10, 10)
    else:
        glTranslatef(-sx, -sy, -600)
        glColor3f(0.85, 0.85, 0.9)
        gluSphere(QUADRIC, 30, 10, 10)
    glPopMatrix()


def draw_stars():
    # Draws stars when is_night
    if not is_night:
        return
    glPointSize(2.0)
    glBegin(GL_POINTS)
    glColor3f(1.0, 1.0, 1.0)
    for sx, sy, sz in STAR_POSITIONS:
        glVertex3f(sx, sy, sz)
    glEnd()


def draw_clouds():
    # Draws drifting clouds
    nf = night_factor
    # White during day, grey during night
    c_val = 1.0 * max(0.4, nf)
    glColor3f(c_val, c_val, c_val)
    
    for c in clouds:
        # Drift slowly
        cx = c["x"] + (game_time * 15.0) % 3000
        if cx > 1500: cx -= 3000
        
        glPushMatrix()
        glTranslatef(cx, c["y"], c["z"])
        glScalef(1.5, 0.5, 1.0)
        gluSphere(QUADRIC, c["size"], 8, 8)
        
        glTranslatef(c["size"]*0.5, c["size"]*0.2, 0)
        gluSphere(QUADRIC, c["size"]*0.8, 8, 8)
        
        glTranslatef(-c["size"], 0, 0)
        gluSphere(QUADRIC, c["size"]*0.7, 8, 8)
        glPopMatrix()


def draw_weather():
    # Draws rain/storm/fog particles
    global storm_flash_timer
    nf = night_factor
    if weather_state == "rain" or weather_state == "storm":
        count = 300 if weather_state == "rain" else 500
        glLineWidth(1.5)
        glBegin(GL_LINES)
        glColor3f(0.5 * nf, 0.7 * nf, 1.0 * nf)
        for i in range(min(count, len(rain_particles))):
            p = rain_particles[i]
            glVertex3f(p[0], p[1], p[2])
            glVertex3f(p[0], p[1] - 15, p[2])
        glEnd()
        if weather_state == "storm":
            storm_flash_timer += 1
            if storm_flash_timer % 500 < 5:
                glClearColor(1.0, 1.0, 1.0, 1.0)


def draw_ground():
    gnf = max(night_factor, 0.5)
    glColor3f(0.2 * gnf, 0.55 * gnf, 0.15 * gnf)
    glBegin(GL_QUADS)
    glVertex3f(-GRID_LENGTH * 1.5, -0.5, -GRID_LENGTH * 1.5)
    glVertex3f(GRID_LENGTH * 1.5, -0.5, -GRID_LENGTH * 1.5)
    glVertex3f(GRID_LENGTH * 1.5, -0.5, GRID_LENGTH * 1.5)
    glVertex3f(-GRID_LENGTH * 1.5, -0.5, GRID_LENGTH * 1.5)
    glEnd()


def draw_pond():
    nf = night_factor
    glPushMatrix()
    glTranslatef(POND_POS[0], 0.0, POND_POS[2])
    
    # Outer Bank Dirt
    glColor3f(0.35 * nf, 0.25 * nf, 0.15 * nf)
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(0, 0.2, 0)
    for i in range(37):
        ang = math.radians(i * 10)
        glVertex3f(math.cos(ang) * (POND_RADIUS + 20), 0.2, math.sin(ang) * (POND_RADIUS + 20))
    glEnd()

    # Outer Deep Blue
    glColor3f(0.1 * nf, 0.3 * nf, 0.8 * nf)
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(0, 0.6, 0)
    for i in range(37):
        ang = math.radians(i * 10)
        glVertex3f(math.cos(ang) * POND_RADIUS, 0.6, math.sin(ang) * POND_RADIUS)
    glEnd()

    # Inner Lighter blue
    glColor3f(0.2 * nf, 0.5 * nf, 0.9 * nf)
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(0, 0.8, 0)
    for i in range(37):
        ang = math.radians(i * 10)
        glVertex3f(math.cos(ang) * (POND_RADIUS * 0.7), 0.8, math.sin(ang) * (POND_RADIUS * 0.7))
    glEnd()

    # Drawing fishes
    for f in range(5):
        fang = game_time * (2 + f * 0.5) + f * 1.2
        fx = math.cos(fang) * (POND_RADIUS * 0.6)
        fz = math.sin(fang) * (POND_RADIUS * 0.6)
        glPushMatrix()
        glTranslatef(fx, 1.0, fz)
        glRotatef(math.degrees(-fang), 0, 1, 0)
        glColor3f(1.0 * nf, 0.5 * nf, 0.1 * nf) # Orange fish
        glScalef(1, 0.5, 2)
        gluSphere(QUADRIC, 3, 6, 6)
        glPopMatrix()
    glPopMatrix()


def draw_scenery():
    nf = night_factor
    state = random.getstate()
    random.seed(42)
    
    # Edge Trees and Bushes
    for _ in range(80):
        tx = random.uniform(-GRID_LENGTH, GRID_LENGTH)
        tz = random.uniform(-GRID_LENGTH, GRID_LENGTH)
        # Push towards the edges
        if abs(tx) < 700 and abs(tz) < 700:
            if random.random() > 0.5:
                tx = math.copysign(random.uniform(700, GRID_LENGTH), tx)
            else:
                tz = math.copysign(random.uniform(700, GRID_LENGTH), tz)
        
        glPushMatrix()
        glTranslatef(tx, 0, tz)
        if random.random() > 0.5:
            # Tree trunk
            glColor3f(0.4 * nf, 0.25 * nf, 0.1 * nf)
            glRotatef(-90, 1, 0, 0)
            gluCylinder(QUADRIC, 10, 8, 80, 8, 1)
            # Tree leaves
            glTranslatef(0, 0, 80)
            glColor3f(0.15 * nf, 0.5 * nf, 0.2 * nf)
            gluSphere(QUADRIC, 40, 8, 8)
        else:
            # Bush
            glColor3f(0.2 * nf, 0.6 * nf, 0.2 * nf)
            glTranslatef(0, 15, 0)
            gluSphere(QUADRIC, 20, 8, 8)
            glTranslatef(10, -5, 10)
            gluSphere(QUADRIC, 15, 8, 8)
        glPopMatrix()
        
    # Rocks
    for _ in range(40):
        rx = random.uniform(-GRID_LENGTH, GRID_LENGTH)
        rz = random.uniform(-GRID_LENGTH, GRID_LENGTH)
        glPushMatrix()
        glTranslatef(rx, 5, rz)
        glColor3f(0.5 * nf, 0.5 * nf, 0.5 * nf)
        glScalef(1, 0.5, 1)
        gluSphere(QUADRIC, random.uniform(5, 15), 6, 6)
        glPopMatrix()
        
    # Spiky Grasses
    for _ in range(150):
        gx = random.uniform(-GRID_LENGTH, GRID_LENGTH)
        gz = random.uniform(-GRID_LENGTH, GRID_LENGTH)
        if abs(gx) < 150 or abs(gz) < 150: continue 
        if gx > 100 and gz < -100: continue 
        if gx < -100 and gz < -100: continue 
        
        glPushMatrix()
        glTranslatef(gx, 0, gz)
        glColor3f(0.2 * nf, 0.7 * nf, 0.2 * nf)
        glRotatef(-90, 1, 0, 0)
        for i in range(3):
            glPushMatrix()
            glTranslatef(random.uniform(-3, 3), random.uniform(-3, 3), 0)
            glRotatef(random.uniform(-15, 15), 0, 1, 0)
            gluCylinder(QUADRIC, 0.5, 0, 8, 4, 1)
            glPopMatrix()
        glPopMatrix()
    
    random.setstate(state)


def draw_farm():
    # Grid of plots and crops
    nf = night_factor
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            px = (i - GRID_SIZE // 2) * PLOT_SIZE + FARM_OFFSET_X
            pz = (j - GRID_SIZE // 2) * PLOT_SIZE + FARM_OFFSET_Z
            plot = farm_plots[i][j]
            glPushMatrix()
            # Ground tile
            if plot["owned"]:
                glColor3f(0.5 * nf, 0.3 * nf, 0.1 * nf)
            else:
                gnf = max(nf, 0.5)
                glColor3f(0.2 * gnf, 0.55 * gnf, 0.15 * gnf)
            glBegin(GL_QUADS)
            glVertex3f(px, 0, pz)
            glVertex3f(px + PLOT_SIZE, 0, pz)
            glVertex3f(px + PLOT_SIZE, 0, pz + PLOT_SIZE)
            glVertex3f(px, 0, pz + PLOT_SIZE)
            glEnd()
            # Fence 
            if plot["owned"]:
                glColor3f(0.6 * nf, 0.4 * nf, 0.15 * nf)
                for fx, fz in [(px, pz), (px + PLOT_SIZE, pz), (px, pz + PLOT_SIZE), (px + PLOT_SIZE, pz + PLOT_SIZE)]:
                    glPushMatrix()
                    glTranslatef(fx, 0, fz)
                    glRotatef(-90, 1, 0, 0)
                    gluCylinder(QUADRIC, 3, 3, 40, 6, 1)
                    glPopMatrix()
            # Crop
            if plot["owned"] and plot["crop_type"] != "none":
                draw_crop(px + PLOT_SIZE // 2, pz + PLOT_SIZE // 2, plot)
            glPopMatrix()


def draw_crop(px, pz, plot):
    # Draws a crop
    nf = night_factor
    ct = plot["crop_type"]
    if ct == "wheat":
        cr, cg, cb = 1.0, 0.9, 0.2
    elif ct == "corn":
        cr, cg, cb = 1.0, 0.7, 0.0
    else:
        cr, cg, cb = 0.8, 0.1, 0.5
    glColor3f(cr * nf, cg * nf, cb * nf)
    stage = plot["growth_stage"]
    glPushMatrix()
    glTranslatef(px, 0, pz)
    if stage == 0:
        glPushMatrix()
        glTranslatef(0, 3, 0)
        gluSphere(QUADRIC, 3, 6, 6)
        glPopMatrix()
    elif stage == 1:
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        glColor3f(0.3 * nf, 0.6 * nf, 0.1 * nf)
        gluCylinder(QUADRIC, 2, 2, 15, 6, 1)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(0, 15, 0)
        glColor3f(cr * nf, cg * nf, cb * nf)
        gluSphere(QUADRIC, 8, 6, 6)
        glPopMatrix()
    elif stage == 2:
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        glColor3f(0.3 * nf, 0.6 * nf, 0.1 * nf)
        gluCylinder(QUADRIC, 3, 3, 25, 6, 1)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(0, 25, 0)
        glColor3f(cr * nf, cg * nf, cb * nf)
        gluSphere(QUADRIC, 14, 8, 8)
        glPopMatrix()
    elif stage == 3:
        if plot["is_tree"]:
            glPushMatrix()
            glRotatef(-90, 1, 0, 0)
            glColor3f(0.4 * nf, 0.25 * nf, 0.1 * nf)
            gluCylinder(QUADRIC, 8, 6, 60, 8, 1)
            glPopMatrix()
            glPushMatrix()
            glTranslatef(0, 60, 0)
            glColor3f(cr * nf, cg * nf, cb * nf)
            gluSphere(QUADRIC, 30, 10, 10)
            glPopMatrix()
        else:
            glPushMatrix()
            glRotatef(-90, 1, 0, 0)
            glColor3f(0.3 * nf, 0.6 * nf, 0.1 * nf)
            gluCylinder(QUADRIC, 3, 3, 30, 6, 1)
            glPopMatrix()
            glPushMatrix()
            glTranslatef(0, 30, 0)
            glColor3f(cr * nf, cg * nf, cb * nf)
            gluSphere(QUADRIC, 14, 8, 8)
            glPopMatrix()
    glPopMatrix()


def draw_carrot_farm():
    nf = night_factor
    gnf = max(nf, 0.5)
    for plot in carrot_plots:
        px, pz = plot["x"], plot["z"]
        glPushMatrix()
        # Farmland
        glColor3f(0.5 * nf, 0.3 * nf, 0.1 * nf)
        glBegin(GL_QUADS)
        glVertex3f(px, 0.1, pz)
        glVertex3f(px + PLOT_SIZE, 0.1, pz)
        glVertex3f(px + PLOT_SIZE, 0.1, pz + PLOT_SIZE)
        glVertex3f(px, 0.1, pz + PLOT_SIZE)
        glEnd()
        # Carrot
        if plot["active"]:
            glPushMatrix()
            glTranslatef(px + PLOT_SIZE // 2, 0, pz + PLOT_SIZE // 2)
            glRotatef(-90, 1, 0, 0)
            glColor3f(0.9 * nf, 0.5 * nf, 0.1 * nf)
            gluCylinder(QUADRIC, 4, 0, 20, 6, 1)
            # Leaves
            glTranslatef(0, 0, 20)
            glColor3f(0.2 * nf, 0.8 * nf, 0.2 * nf)
            gluCylinder(QUADRIC, 0, 6, 10, 4, 1)
            glPopMatrix()
        glPopMatrix()


def draw_hut():
    # Healing Hut
    nf = night_factor
    hx, hz = -350, 350
    half = 50  # half-width of the cube base
    wall_h = 80  # top of the walls
    peak_h = 140  # peak of roof
    
    glPushMatrix()
    glTranslatef(hx, 0, hz)
    
    # Floor
    glColor3f(0.45 * nf, 0.35 * nf, 0.25 * nf)
    glBegin(GL_QUADS)
    glVertex3f(-half, 0.5, -half)
    glVertex3f(half, 0.5, -half)
    glVertex3f(half, 0.5, half)
    glVertex3f(-half, 0.5, half)
    glEnd()
    
    # Walls
    wall_c = (0.6 * nf, 0.5 * nf, 0.4 * nf)
    
    # Back wall 
    glColor3f(*wall_c)
    glBegin(GL_QUADS)
    glVertex3f(-half, 0, -half)
    glVertex3f(half, 0, -half)
    glVertex3f(half, wall_h, -half)
    glVertex3f(-half, wall_h, -half)
    glEnd()
    
    # Left wall
    glBegin(GL_QUADS)
    glVertex3f(-half, 0, -half)
    glVertex3f(-half, 0, half)
    glVertex3f(-half, wall_h, half)
    glVertex3f(-half, wall_h, -half)
    glEnd()
    
    # Right wall
    glBegin(GL_QUADS)
    glVertex3f(half, 0, -half)
    glVertex3f(half, 0, half)
    glVertex3f(half, wall_h, half)
    glVertex3f(half, wall_h, -half)
    glEnd()
    
    # Front wall 
    # Left of door
    glBegin(GL_QUADS)
    glVertex3f(-half, 0, half)
    glVertex3f(-15, 0, half)
    glVertex3f(-15, wall_h, half)
    glVertex3f(-half, wall_h, half)
    glEnd()
    # Right of door
    glBegin(GL_QUADS)
    glVertex3f(15, 0, half)
    glVertex3f(half, 0, half)
    glVertex3f(half, wall_h, half)
    glVertex3f(15, wall_h, half)
    glEnd()
    # Above door
    glBegin(GL_QUADS)
    glVertex3f(-15, 50, half)
    glVertex3f(15, 50, half)
    glVertex3f(15, wall_h, half)
    glVertex3f(-15, wall_h, half)
    glEnd()
    
    # Interior walls
    in_c = (0.5 * nf, 0.4 * nf, 0.3 * nf)
    inset = 1.0
    glColor3f(*in_c)
    # Back interior
    glBegin(GL_QUADS)
    glVertex3f(-half+inset, 0, -half+inset)
    glVertex3f(half-inset, 0, -half+inset)
    glVertex3f(half-inset, wall_h, -half+inset)
    glVertex3f(-half+inset, wall_h, -half+inset)
    glEnd()
    # Left interior
    glBegin(GL_QUADS)
    glVertex3f(-half+inset, 0, -half+inset)
    glVertex3f(-half+inset, 0, half-inset)
    glVertex3f(-half+inset, wall_h, half-inset)
    glVertex3f(-half+inset, wall_h, -half+inset)
    glEnd()
    # Right interior
    glBegin(GL_QUADS)
    glVertex3f(half-inset, 0, -half+inset)
    glVertex3f(half-inset, 0, half-inset)
    glVertex3f(half-inset, wall_h, half-inset)
    glVertex3f(half-inset, wall_h, -half+inset)
    glEnd()
    
    # Roof
    roof_c = (0.8 * nf, 0.2 * nf, 0.2 * nf)
    glColor3f(*roof_c)
    peak = [0, peak_h, 0]
    corners = [
        (-half, wall_h, -half),
        (half, wall_h, -half),
        (half, wall_h, half),
        (-half, wall_h, half),
    ]
    # 4 triangular faces
    for i in range(4):
        c1 = corners[i]
        c2 = corners[(i + 1) % 4]
        glBegin(GL_TRIANGLES)
        glVertex3f(*peak)
        glVertex3f(*c1)
        glVertex3f(*c2)
        glEnd()
    
    # Healing glow
    glPushMatrix()
    glTranslatef(0, 30, 0)
    glColor3f(0.2 * nf, 0.8 * nf, 0.3 * nf)
    gluSphere(QUADRIC, 8, 8, 8)
    glPopMatrix()
    
    glPopMatrix()


def draw_crossroad():
    gnf = max(night_factor, 0.5)
    glColor3f(0.4 * gnf, 0.35 * gnf, 0.3 * gnf)
    path_width = 100
    L = GRID_LENGTH
    glBegin(GL_QUADS)

    glVertex3f(-path_width/2, 0.2, -L)
    glVertex3f(path_width/2, 0.2, -L)
    glVertex3f(path_width/2, 0.2, L)
    glVertex3f(-path_width/2, 0.2, L)

    glVertex3f(-L, 0.2, -path_width/2)
    glVertex3f(L, 0.2, -path_width/2)
    glVertex3f(L, 0.2, path_width/2)
    glVertex3f(-L, 0.2, path_width/2)
    glEnd()


def draw_player():
    nf = night_factor
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    glRotatef(player_angle, 0, 1, 0)
    if player_dead:
        glRotatef(90, 0, 0, 1)  
        
    glScalef(34.0, 34.0, 34.0)
    
    # HEAD
    glColor3f(1.0 * nf, 0.8 * nf, 0.6 * nf)
    glPushMatrix()
    glTranslatef(0.0, 1.05, 0.0) 
    glutSolidSphere(0.35, 40, 40) 
    glPopMatrix()

    # EYES
    glColor3f(0.0, 0.0, 0.0)
    for x_pos in [-0.14, 0.14]: 
        glPushMatrix()
        glTranslatef(x_pos, 1.1, 0.32) 
        glutSolidSphere(0.05, 20, 20) 
        glPopMatrix()

    # BLUSH
    glColor3f(1.0 * nf, 0.6 * nf, 0.6 * nf)
    for x_pos in [-0.18, 0.18]:
        glPushMatrix()
        glTranslatef(x_pos, 0.95, 0.28) 
        glScalef(1.0, 0.5, 1.0) 
        glutSolidSphere(0.04, 10, 10)
        glPopMatrix()

    # BODY
    glColor3f(0.2 * nf, 0.4 * nf, 0.8 * nf)
    glPushMatrix()
    glTranslatef(0.0, 0.6, 0.0) 
    glScalef(0.45, 0.4, 0.3) 
    glutSolidCube(1.0)
    glPopMatrix()
    
    # RIGHT ARM & WEAPON
    glPushMatrix()
    glTranslatef(-0.28, 0.7, 0.0) 
    glRotatef(15, 0, 0, 1)  
    glRotatef(90, 1, 0, 0)    
       
        
    glColor3f(1.0 * nf, 0.8 * nf, 0.6 * nf)
    gluCylinder(QUADRIC, 0.07, 0.06, 0.4, 10, 10) 
    
    # Hand
    glTranslatef(0, 0, 0.4)
    glutSolidSphere(0.1, 10, 10) 

    glPopMatrix()
    
    # LEFT ARM
    glPushMatrix()
    glTranslatef(0.28, 0.7, 0.0) 
    glRotatef(-15, 0, 0, 1)  
    if fishing_active:
        glRotatef(-60, 1, 0, 0)
    else:
        glRotatef(90, 1, 0, 0)      
    
    glColor3f(1.0 * nf, 0.8 * nf, 0.6 * nf)
    gluCylinder(QUADRIC, 0.07, 0.06, 0.4, 10, 10) 
    
    # Hand
    glTranslatef(0, 0, 0.4)
    glutSolidSphere(0.1, 10, 10) 
    
    # Staff in Left Hand
    if not fishing_active:
        glColor3f(0.6 * nf, 0.3 * nf, 0.1 * nf)
        glRotatef(-90, 1, 0, 0)  
        glTranslatef(0, 0, -0.5) 
        gluCylinder(QUADRIC, 0.04, 0.03, 1.5, 8, 1) 
        # Magic Gem on top
        glTranslatef(0, 0, 1.5) 
        glColor3f(0.2 * nf, 0.8 * nf, 1.0 * nf)
        glutSolidSphere(0.15, 10, 10) 

    glPopMatrix()
    
    # LEFT LEG
    glPushMatrix()
    glTranslatef(-0.12, 0.45, 0.0) 
    glRotatef(90, 1, 0, 0)        
    glColor3f(0.15 * nf, 0.15 * nf, 0.4 * nf)
    gluCylinder(QUADRIC, 0.09, 0.09, 0.45, 10, 10) 
    
    # LEFT BOOT
    glTranslatef(0, 0, 0.45) 
    glColor3f(0.1 * nf, 0.1 * nf, 0.1 * nf)
    gluCylinder(QUADRIC, 0.11, 0.11, 0.2, 10, 10) 
    glPopMatrix()
    
    # RIGHT LEG
    glPushMatrix()
    glTranslatef(0.12, 0.45, 0.0)
    glRotatef(90, 1, 0, 0)
    glColor3f(0.15 * nf, 0.15 * nf, 0.4 * nf)
    gluCylinder(QUADRIC, 0.09, 0.09, 0.45, 10, 10)
    
    # RIGHT BOOT
    glTranslatef(0, 0, 0.45)
    glColor3f(0.1 * nf, 0.1 * nf, 0.1 * nf)
    gluCylinder(QUADRIC, 0.11, 0.11, 0.2, 10, 10)
    glPopMatrix()

    # CROWN
    glColor3f(1.0 * nf, 0.84 * nf, 0.0)
    glPushMatrix()
    glTranslatef(0.0, 1.48, 0.0) 
    glRotatef(90, 1, 0, 0)
    glutSolidTorus(0.04, 0.2, 20, 20) 
    for angle in [0, 120, 240]:       
        glPushMatrix()
        glRotatef(angle, 0, 0, 1)
        glTranslatef(0.15, 0, 0)      
        glRotatef(-90, 1, 0, 0)       
        glutSolidCone(0.08, 0.25, 10, 10) 
        glPopMatrix()
    glPopMatrix()
    
    glPopMatrix()

def draw_bullets():
    # Draws bullets
    for b in bullets:
        glPushMatrix()
        glTranslatef(b["pos"][0], b["pos"][1], b["pos"][2])
        glColor3f(1.0, 0.9, 0.0)
        gluSphere(QUADRIC, 5, 6, 6)
        glPopMatrix()


def draw_enemy(enemy):
    # Draws a humanoid enemy 
    nf = night_factor
    glPushMatrix()
    glTranslatef(enemy["pos"][0], enemy["pos"][1], enemy["pos"][2])
    etype = enemy["type"]
    if etype == "phantom":
        body_c = (0.5 * nf, 0.3 * nf, 0.1 * nf)
        skin_c = (0.4 * nf, 0.25 * nf, 0.08 * nf)
    else:  # shade
        body_c = (0.15, 0.0, 0.3)
        skin_c = (0.2, 0.05, 0.35)
    # Torso
    glPushMatrix()
    glTranslatef(0, 22, 0)
    glColor3f(*body_c)
    glScalef(1.0, 1.4, 0.6)
    glutSolidCube(20)
    glPopMatrix()
    # Head
    glPushMatrix()
    glTranslatef(0, 40, 0)
    glColor3f(*skin_c)
    gluSphere(QUADRIC, 9, 8, 8)
    # Draw horns 
    if etype == "shade":
        glColor3f(0.8, 0.1, 0.1)
        for side in [1, -1]:
            glPushMatrix()
            glTranslatef(side * 8, 5, 0)
            glRotatef(90 * side, 0, 1, 0)
            glRotatef(45 * side, 1, 0, 0)
            glutSolidTorus(1.5, 4, 10, 10)
            glPopMatrix()
    glPopMatrix()
    # Arms 
    for side in [12, -12]:
        glPushMatrix()
        glTranslatef(side, 26, 0)
        glRotatef(-60, 1, 0, 0)
        glColor3f(*skin_c)
        gluCylinder(QUADRIC, 3, 2.5, 16, 6, 1)
        glPopMatrix()
    # Legs
    for side in [5, -5]:
        glPushMatrix()
        glTranslatef(side, 8, 0)
        glRotatef(90, 1, 0, 0)
        glColor3f(*body_c)
        gluCylinder(QUADRIC, 4, 3.5, 14, 6, 1)
        glPopMatrix()
    draw_3d_healthbar(enemy)
    glPopMatrix()


def draw_3d_healthbar(enemy):
    glPushMatrix()
    glTranslatef(0, 55, 0) 
    ratio = enemy["health"] / enemy["max_health"]
    bar_w = 30
    # Background
    glColor3f(0.3, 0.3, 0.3)
    glBegin(GL_QUADS)
    glVertex3f(-bar_w / 2, 0, 0)
    glVertex3f(bar_w / 2, 0, 0)
    glVertex3f(bar_w / 2, 4, 0)
    glVertex3f(-bar_w / 2, 4, 0)
    glEnd()
    # Health fill
    glColor3f(1.0, 0.0, 0.0)
    glBegin(GL_QUADS)
    glVertex3f(-bar_w / 2, 0, 0)
    glVertex3f(-bar_w / 2 + bar_w * ratio, 0, 0)
    glVertex3f(-bar_w / 2 + bar_w * ratio, 4, 0)
    glVertex3f(-bar_w / 2, 4, 0)
    glEnd()
    glPopMatrix()


def draw_villagers():
    nf = night_factor
    for v in villagers:
        glPushMatrix()
        glTranslatef(v["pos"][0], v["pos"][1], v["pos"][2])
        # Torso
        glPushMatrix()
        glTranslatef(0, 22, 0)
        glColor3f(0.8 * nf, 0.55 * nf, 0.3 * nf)
        glScalef(1.0, 1.4, 0.6)
        glutSolidCube(20)
        glPopMatrix()
        # Head
        glPushMatrix()
        glTranslatef(0, 40, 0)
        glColor3f(0.95 * nf, 0.8 * nf, 0.65 * nf)
        gluSphere(QUADRIC, 9, 8, 8)
        glPopMatrix()
        # Hat 
        glPushMatrix()
        glTranslatef(0, 48, 0)
        glRotatef(-90, 1, 0, 0)
        glColor3f(0.6 * nf, 0.3 * nf, 0.1 * nf)
        gluCylinder(QUADRIC, 12, 0, 15, 8, 1) 
        # Hat brim
        glRotatef(0, 0, 0, 0)
        gluCylinder(QUADRIC, 14, 12, 2, 10, 1)
        glPopMatrix()
        # Right arm
        glPushMatrix()
        glTranslatef(12, 26, 0)
        glRotatef(10, 0, 0, 1)
        glRotatef(90, 1, 0, 0)
        glColor3f(0.95 * nf, 0.8 * nf, 0.65 * nf)
        gluCylinder(QUADRIC, 3, 2.5, 16, 6, 1)
        glPopMatrix()
        # Left arm 
        glPushMatrix()
        glTranslatef(-12, 26, 0)
        glRotatef(-10, 0, 0, 1)
        glRotatef(90, 1, 0, 0)
        glColor3f(0.95 * nf, 0.8 * nf, 0.65 * nf)
        gluCylinder(QUADRIC, 3, 2.5, 16, 6, 1)
        glPopMatrix()
        # Right leg
        glPushMatrix()
        glTranslatef(5, 8, 0)
        glRotatef(90, 1, 0, 0)
        glColor3f(0.4 * nf, 0.25 * nf, 0.1 * nf)
        gluCylinder(QUADRIC, 4, 3.5, 14, 6, 1)
        glPopMatrix()
        # Left leg
        glPushMatrix()
        glTranslatef(-5, 8, 0)
        glRotatef(90, 1, 0, 0)
        glColor3f(0.4 * nf, 0.25 * nf, 0.1 * nf)
        gluCylinder(QUADRIC, 4, 3.5, 14, 6, 1)
        glPopMatrix()
        # Trade ring
        if v["trade_active"]:
            glColor3f(1.0, 0.85, 0.0)
            glLineWidth(2.0)
            glBegin(GL_LINE_LOOP)
            for a in range(36):
                ang = math.radians(a * 10)
                glVertex3f(20 * math.cos(ang), 1, 20 * math.sin(ang))
            glEnd()
        glPopMatrix()
        # Name label
        if v["trade_active"]:
            glColor3f(1.0, 1.0, 1.0)
            draw_text(WINDOW_W // 2, 60, v["name"], GLUT_BITMAP_HELVETICA_12)


def draw_fishing_scene():
    # Draws fishing rod
    if not fishing_active:
        return
    nf = night_factor
    # Rod held in player's left hand
    rod_base_x = player_pos[0] + 12 * math.cos(math.radians(player_angle))
    rod_base_y = player_pos[1] + 26
    rod_base_z = player_pos[2] - 12 * math.sin(math.radians(player_angle))
    glPushMatrix()
    glTranslatef(rod_base_x, rod_base_y, rod_base_z)
    glRotatef(player_angle, 0, 1, 0)
    glRotatef(-45, 1, 0, 0)
    glColor3f(0.5 * nf, 0.3 * nf, 0.1 * nf)
    gluCylinder(QUADRIC, 2, 1, 80, 6, 1)
    glPopMatrix()
    if fishing_line_cast:
        # Rod tip position 
        rod_tip_x = rod_base_x + 56 * math.sin(math.radians(player_angle))
        rod_tip_y = rod_base_y + 56  # rod goes up
        rod_tip_z = rod_base_z + 56 * math.cos(math.radians(player_angle))
        # Bobber position 
        bob_x = POND_POS[0] + random.uniform(-5, 5) * 0.01
        bob_z = POND_POS[2] + random.uniform(-5, 5) * 0.01
        bob_y = 2.0
        if fish_on:
            bob_y += math.sin(game_time * 10) * 3
        # Line
        glLineWidth(1.0)
        glColor3f(0.8, 0.8, 0.8)
        glBegin(GL_LINES)
        glVertex3f(rod_tip_x, rod_tip_y, rod_tip_z)
        glVertex3f(bob_x, bob_y, bob_z)
        glEnd()
        # Bobber
        glPushMatrix()
        glTranslatef(bob_x, bob_y, bob_z)
        glColor3f(1.0, 0.0, 0.0)
        gluSphere(QUADRIC, 4, 6, 6)
        glPopMatrix()


def draw_hud():
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    # HP bar bg
    glColor3f(0.1, 0.1, 0.15)
    glBegin(GL_QUADS)
    glVertex2f(5, 755); glVertex2f(220, 755); glVertex2f(220, 785); glVertex2f(5, 785)
    glEnd()
    glColor3f(0.3, 0.3, 0.3)
    glBegin(GL_QUADS)
    glVertex2f(10, 760); glVertex2f(210, 760); glVertex2f(210, 778); glVertex2f(10, 778)
    glEnd()
    hp_ratio = max(0, player_health) / 100.0
    glColor3f(0.9, 0.1, 0.1)
    glBegin(GL_QUADS)
    glVertex2f(10, 760); glVertex2f(10 + 200 * hp_ratio, 760)
    glVertex2f(10 + 200 * hp_ratio, 778); glVertex2f(10, 778)
    glEnd()
    # Time bg
    glColor3f(0.1, 0.1, 0.15)
    glBegin(GL_QUADS)
    glVertex2f(WINDOW_W // 2 - 110, 755); glVertex2f(WINDOW_W // 2 + 110, 755)
    glVertex2f(WINDOW_W // 2 + 110, 785); glVertex2f(WINDOW_W // 2 - 110, 785)
    glEnd()
    # Stats bg
    glColor3f(0.1, 0.1, 0.15)
    glBegin(GL_QUADS)
    glVertex2f(WINDOW_W - 195, 710); glVertex2f(WINDOW_W - 5, 710)
    glVertex2f(WINDOW_W - 5, 785); glVertex2f(WINDOW_W - 195, 785)
    glEnd()
    # Bottom bar bg
    glColor3f(0.1, 0.1, 0.15)
    glBegin(GL_QUADS)
    glVertex2f(0, 0); glVertex2f(WINDOW_W, 0); glVertex2f(WINDOW_W, 30); glVertex2f(0, 30)
    glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    # Text
    glColor3f(1, 1, 1)
    draw_text(15, 762, "HP: %d" % player_health)
    hour = int(game_time) % 24
    time_str = "Day 1  %02d:00" % hour
    if is_night:
        time_str += "  [NIGHT]"
    draw_text(WINDOW_W // 2 - 80, 762, time_str)
    glColor3f(1.0, 0.9, 0.2)
    inv_crops = inventory.get("wheat", 0) + inventory.get("corn", 0) + inventory.get("carrot", 0) + inventory.get("berry", 0)
    draw_text(WINDOW_W - 185, 762, "Crops: %d" % inv_crops)
    glColor3f(0.7, 0.85, 1.0)
    draw_text(WINDOW_W - 185, 742, "Weather: %s" % weather_state.upper())
    glColor3f(0.5, 0.8, 1.0)
    draw_text(WINDOW_W - 185, 722, "Fish: %d" % fish_caught)
    glColor3f(0.8, 0.8, 0.8)
    draw_text(40, 10, "E:Interact  F:Fish  T:Trade  C:Craft  Q:Auto  LMB:Fire  V:Camera  ESC:Menu", GLUT_BITMAP_HELVETICA_12)
    # Low HP warning
    if 0 < player_health <= 25:
        glColor3f(1.0, 0.2, 0.2)
        draw_text(WINDOW_W // 2 - 140, WINDOW_H // 2 + 40, "WARNING: Low HP! Eat food (Inventory)!", GLUT_BITMAP_HELVETICA_18)
    if hud_message and hud_message_timer > 0:
        glColor3f(1.0, 1.0, 0.3)
        draw_text(WINDOW_W // 2 - 100, WINDOW_H // 2, hud_message, GLUT_BITMAP_TIMES_ROMAN_24)
    glEnable(GL_DEPTH_TEST)


def draw_inventory_ui():
    if game_state != "inventory":
        return
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(0.08, 0.08, 0.15)
    glBegin(GL_QUADS)
    glVertex2f(200, 100); glVertex2f(800, 100); glVertex2f(800, 700); glVertex2f(200, 700)
    glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glColor3f(1.0, 0.85, 0.2)
    draw_text(430, 660, "INVENTORY", GLUT_BITMAP_TIMES_ROMAN_24)
    items = []
    for k, v in inventory.items():
        if v > 0:
            items.append(("  %s: %d" % (k, v), False))
    for k, v in cooked_food.items():
        if v > 0:
            items.append(("  [EAT] %s: %d" % (k, v), True))
    if not items:
        glColor3f(0.6, 0.6, 0.6)
        draw_text(350, 450, "Inventory is empty.", GLUT_BITMAP_HELVETICA_18)
    else:
        for idx, (text, is_food) in enumerate(items):
            if idx == inventory_selected:
                glColor3f(1.0, 1.0, 0.0)
            elif is_food:
                glColor3f(0.3, 1.0, 0.3)
            else:
                glColor3f(0.7, 0.7, 0.7)
            draw_text(250, 600 - idx * 35, text, GLUT_BITMAP_HELVETICA_18)
    glColor3f(0.6, 0.6, 0.6)
    draw_text(250, 130, "UP/DOWN: Select  ENTER: Eat Food  ESC: Close", GLUT_BITMAP_HELVETICA_12)
    glEnable(GL_DEPTH_TEST)


def draw_death_screen():
    if game_state != "dead":
        return
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(0.15, 0.0, 0.0)
    glBegin(GL_QUADS)
    glVertex2f(300, 250); glVertex2f(700, 250); glVertex2f(700, 550); glVertex2f(300, 550)
    glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glColor3f(1.0, 0.2, 0.2)
    draw_text(380, 500, "YOU DIED", GLUT_BITMAP_TIMES_ROMAN_24)
    glColor3f(1.0, 1.0, 1.0)
    draw_text(370, 430, "START OVER?", GLUT_BITMAP_HELVETICA_18)
    for i, label in enumerate(["Yes", "No (Quit)"]):
        glColor3f(1.0, 1.0, 0.0) if death_selected == i else glColor3f(0.6, 0.6, 0.6)
        draw_text(420, 370 - i * 40, label, GLUT_BITMAP_HELVETICA_18)
    glEnable(GL_DEPTH_TEST)


def draw_menu():
    if not menu_open:
        return
    glDisable(GL_DEPTH_TEST)
    # Dark panel
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(0.1, 0.1, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(300, 150)
    glVertex2f(700, 150)
    glVertex2f(700, 650)
    glVertex2f(300, 650)
    glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    # Title
    glColor3f(1.0, 0.85, 0.2)
    draw_text(380, 610, "NIGHTFALL FARM", GLUT_BITMAP_TIMES_ROMAN_24)
    # Menu 
    for idx, item in enumerate(MENU_ITEMS):
        if idx == menu_selected:
            glColor3f(1.0, 1.0, 0.0)
        else:
            glColor3f(0.8, 0.8, 0.8)
        draw_text(420, 550 - idx * 50, item, GLUT_BITMAP_HELVETICA_18)
    glEnable(GL_DEPTH_TEST)


def draw_trading_ui():
    if game_state != "trading" or current_trader is None:
        return
    glDisable(GL_DEPTH_TEST)
    v = current_trader
    desc, need_item, need_amt, give_item, give_amt = v["trade"]
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(0.08, 0.08, 0.18)
    glBegin(GL_QUADS)
    glVertex2f(250, 250); glVertex2f(750, 250); glVertex2f(750, 550); glVertex2f(250, 550)
    glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glColor3f(1.0, 0.85, 0.2)
    draw_text(370, 510, "TRADE - %s" % v["name"], GLUT_BITMAP_TIMES_ROMAN_24)
    has = inventory.get(need_item, 0)
    if has >= need_amt:
        glColor3f(0.3, 1.0, 0.3)
    else:
        glColor3f(0.7, 0.4, 0.4)
    draw_text(290, 420, "%s (have: %d)" % (desc, has), GLUT_BITMAP_HELVETICA_18)
    glColor3f(0.7, 0.7, 0.7)
    draw_text(290, 300, "ENTER: Confirm  T: Close", GLUT_BITMAP_HELVETICA_12)
    glEnable(GL_DEPTH_TEST)


def draw_crafting_ui():
    if game_state != "crafting":
        return
    glDisable(GL_DEPTH_TEST)
    # Panel
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(0.08, 0.12, 0.08)
    glBegin(GL_QUADS)
    glVertex2f(250, 100)
    glVertex2f(750, 100)
    glVertex2f(750, 700)
    glVertex2f(250, 700)
    glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glColor3f(0.2, 1.0, 0.4)
    draw_text(410, 660, "CRAFTING", GLUT_BITMAP_TIMES_ROMAN_24)
    recipe_names = list(RECIPES.keys())
    for idx, rname in enumerate(recipe_names):
        recipe = RECIPES[rname]
        ingredients = recipe["ingredients"]
        can_craft = all(inventory.get(k, 0) >= v for k, v in ingredients.items())
        parts = []
        for k, v in ingredients.items():
            parts.append("%s:%d/%d" % (k, inventory.get(k, 0), v))
        line = "%s <- %s" % (rname, ", ".join(parts))
        if idx == crafting_selected:
            glColor3f(1.0, 1.0, 0.0)
        elif can_craft:
            glColor3f(0.3, 1.0, 0.3)
        else:
            glColor3f(0.5, 0.5, 0.5)
        draw_text(275, 600 - idx * 45, line, GLUT_BITMAP_HELVETICA_18)
    glColor3f(0.7, 0.7, 0.7)
    draw_text(275, 140, "UP/DOWN: Select  ENTER: Craft  C: Close", GLUT_BITMAP_HELVETICA_12)
    glEnable(GL_DEPTH_TEST)




# ---------------------------------------------------------------------------
# 6. UPDATE FUNCTIONS
# ---------------------------------------------------------------------------

def update_day_night():
    global game_time, is_night, night_factor
    game_time += DAY_SPEED
    if game_time >= 24.0:
        game_time -= 24.0
    is_night = (game_time >= 20.0 or game_time < 6.0)
    night_factor = get_night_factor()


def update_crops():
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            plot = farm_plots[i][j]
            if not plot["owned"] or plot["crop_type"] == "none":
                continue
            plot["growth_timer"] += 1
            stage = plot["growth_stage"]
            if stage == 0 and plot["growth_timer"] >= 500:
                plot["growth_stage"] = 1
                plot["growth_timer"] = 0
            elif stage == 1 and plot["growth_timer"] >= 1000:
                plot["growth_stage"] = 2
                plot["growth_timer"] = 0
            elif stage == 2 and plot["growth_timer"] >= 2000:
                plot["growth_stage"] = 3
                plot["growth_timer"] = 0
                if plot["crop_type"] == "berry":
                    plot["is_tree"] = True


def update_enemies():
    global enemy_spawn_timer, player_health, player_currency
    if not is_night and len(enemies) > 0:
        enemies.clear()
        return
    if is_night:
        enemy_spawn_timer += 1
        if enemy_spawn_timer >= ENEMY_SPAWN_INTERVAL:
            spawn_enemy()
            enemy_spawn_timer = 0
    to_remove = []
    for idx, e in enumerate(enemies):
        dx = player_pos[0] - e["pos"][0]
        dz = player_pos[2] - e["pos"][2]
        dist = math.sqrt(dx * dx + dz * dz)
        if dist > 1:
            e["pos"][0] += (dx / dist) * e["speed"]
            e["pos"][2] += (dz / dist) * e["speed"]
        if dist < 30:
            # Damage cooldown
            e["damage_cd"] = e.get("damage_cd", 0) + 1
            if e["damage_cd"] >= 60:
                player_health = max(0, player_health - 2)
                e["damage_cd"] = 0
        if e["health"] <= 0:
            to_remove.append(idx)
    for idx in reversed(to_remove):
        enemies.pop(idx)
        player_currency += 2



def update_bullets():
    to_remove_b = []
    for bi, b in enumerate(bullets):
        b["pos"][0] += b["dir"][0]
        b["pos"][1] += b["dir"][1]
        b["pos"][2] += b["dir"][2]
        b["ttl"] -= 1
        if b["ttl"] <= 0:
            to_remove_b.append(bi)
            continue
        for e in enemies:
            if distance(b["pos"], e["pos"]) < 25:
                e["health"] -= weapon_damage()
                to_remove_b.append(bi)
                break
    for idx in reversed(sorted(set(to_remove_b))):
        if idx < len(bullets):
            bullets.pop(idx)


def update_fishing():
    global fishing_timer, fish_on, fishing_line_cast, fish_caught, inventory, hud_message, hud_message_timer
    if not fishing_active:
        return
    if fishing_line_cast:
        fishing_timer += 1
        threshold = 200 + (hash(str(fishing_timer)) % 400)
        if not fish_on and fishing_timer > abs(threshold):
            fish_caught += 1
            inventory["wheat"] += 1
            fishing_timer = 0
            hud_message = "Caught a fish!"
            hud_message_timer = 120


def update_weather():
    global weather_state, weather_timer
    weather_timer -= 1
    if weather_timer <= 0:
        weather_state = random.choice(WEATHER_TRANSITIONS[weather_state])
        weather_timer = random.uniform(1000, 4000)
    # Update rain 
    for p in rain_particles:
        p[1] -= 5
        if p[1] < 0:
            p[0] = player_pos[0] + random.uniform(-GRID_LENGTH, GRID_LENGTH)
            p[1] = random.uniform(300, 500)
            p[2] = player_pos[2] + random.uniform(-GRID_LENGTH, GRID_LENGTH)




def check_villager_proximity():
    for v in villagers:
        v["trade_active"] = distance(player_pos, v["pos"]) < 60


def spawn_enemy():
    etype = random.choice(["phantom", "shade"])
    side = random.choice([-1, 1])
    axis = random.choice([0, 2])
    pos = [0.0, 0.0, 0.0]
    pos[axis] = side * (GRID_LENGTH + 50)
    pos[2 if axis == 0 else 0] = random.uniform(-GRID_LENGTH, GRID_LENGTH)
    pos[1] = 0.0
    
    if etype == "phantom":
        enemies.append({"pos": pos, "health": 10, "max_health": 10, "type": "phantom",
                         "angle": 0.0, "speed": 0.5})
    else:
        enemies.append({"pos": pos, "health": 10, "max_health": 10, "type": "shade",
                         "angle": 0.0, "speed": 0.25})


def craft_item(recipe_name):
    global hud_message, hud_message_timer
    if recipe_name not in RECIPES:
        return
    recipe = RECIPES[recipe_name]
    ingredients = recipe["ingredients"]
    if not all(inventory.get(k, 0) >= v for k, v in ingredients.items()):
        hud_message = "Not enough ingredients!"
        hud_message_timer = 120
        return
    for k, v in ingredients.items():
        inventory[k] -= v
    produces = recipe["produces"]
    if produces in cooked_food:
        cooked_food[produces] += 1
    elif produces in inventory:
        inventory[produces] += 1
    hud_message = "Crafted %s!" % produces
    hud_message_timer = 120


def upgrade_weapon():
    global weapon_level, player_currency, hud_message, hud_message_timer
    if weapon_level >= 3:
        hud_message = "Weapon already max level!"
        hud_message_timer = 120
        return
    if weapon_level == 1 and player_currency >= 15:
        player_currency -= 15
        weapon_level = 2
        hud_message = "Weapon upgraded to Level 2!"
        hud_message_timer = 120
    elif weapon_level == 2 and player_currency >= 30 and inventory.get("fire_stone", 0) >= 1 and inventory.get("water_crystal", 0) >= 1:
        player_currency -= 30
        inventory["fire_stone"] -= 1
        inventory["water_crystal"] -= 1
        weapon_level = 3
        hud_message = "Weapon upgraded to Level 3!"
        hud_message_timer = 120
    else:
        hud_message = "Not enough resources!"
        hud_message_timer = 120



# ---------------------------------------------------------------------------
# 7. INIT FUNCTIONS
# ---------------------------------------------------------------------------

def init_farm():
    # Initializes the farm_plots 2D grid
    global farm_plots
    farm_plots = []
    cx, cz = GRID_SIZE // 2, GRID_SIZE // 2
    for i in range(GRID_SIZE):
        row = []
        for j in range(GRID_SIZE):
            owned = (abs(i - cx) < 2 and abs(j - cz) < 2)
            crop = "none"
            if owned:
                crop = random.choice(["wheat", "corn", "berry"])
            row.append({
                "owned": owned,
                "crop_type": crop,
                "growth_stage": 0,
                "growth_timer": 0.0,
                "is_tree": False,
                "has_water": False,
            })
        farm_plots.append(row)


# ---------------------------------------------------------------------------
# 8. INPUT HANDLER FUNCTIONS
# ---------------------------------------------------------------------------

def keyboardListener(key, x, y):
    global player_pos, player_angle, game_state, menu_open, fishing_active
    global fishing_line_cast, fishing_timer, fish_on, fish_caught
    global hud_message, hud_message_timer, player_health, player_dead
    global crafting_selected, trading_selected, player_currency
    global first_person, current_trader, inventory_selected, death_selected
    global auto_fire

    # Dead state
    if game_state == "dead":
        if key == b'\r':
            if death_selected == 0:  # Yes — restart
                player_health = 100
                player_pos[:] = [0.0, 0.0, -350.0]
                player_dead = False
                enemies.clear()
                game_state = "play"
            else:
                os._exit(0)
        glutPostRedisplay()
        return

    # ESC toggles menu
    if key == b'\x1b':
        if game_state == "menu":
            game_state = "play"
            menu_open = False
        elif game_state in ("crafting", "trading", "inventory"):
            game_state = "play"
        else:
            game_state = "menu"
            menu_open = True
        glutPostRedisplay()
        return

    # Menu mode
    if game_state == "menu":
        global menu_selected
        if key == b'\r':
            item = MENU_ITEMS[menu_selected]
            if item == "Farm":
                game_state = "play"
                menu_open = False
            elif item == "Inventory":
                game_state = "inventory"
                menu_open = False
                inventory_selected = 0
            elif item == "Crafting":
                game_state = "crafting"
                menu_open = False
            elif item == "Upgrade":
                upgrade_weapon()
            elif item == "Quit":
                os._exit(0)
            else:
                game_state = "play"
                menu_open = False
        glutPostRedisplay()
        return

    # Inventory mode
    if game_state == "inventory":
        if key == b'\r':
            # Try to eat 
            items = []
            for k, v in inventory.items():
                if v > 0:
                    items.append((k, False))
            for k, v in cooked_food.items():
                if v > 0:
                    items.append((k, True))
            if items and 0 <= inventory_selected < len(items):
                name, is_food = items[inventory_selected]
                if is_food:
                    food_values = {"bread": 20, "stew": 35, "roast": 50}
                    val = food_values.get(name, 20)
                    cooked_food[name] -= 1
                    player_health = min(100, player_health + val)
                    hud_message = "Ate %s! +%d HP" % (name, val)
                    hud_message_timer = 120
                else:
                    hud_message = "Can't eat that!"
                    hud_message_timer = 80
        glutPostRedisplay()
        return

    # Crafting mode
    if game_state == "crafting":
        if key == b'c':
            game_state = "play"
        elif key == b'\r':
            recipe_names = list(RECIPES.keys())
            if 0 <= crafting_selected < len(recipe_names):
                craft_item(recipe_names[crafting_selected])
        glutPostRedisplay()
        return

    # Trading mode
    if game_state == "trading":
        if key == b't':
            game_state = "play"
            current_trader = None
        elif key == b'\r':
            if current_trader is not None:
                desc, need_item, need_amt, give_item, give_amt = current_trader["trade"]
                if inventory.get(need_item, 0) >= need_amt:
                    inventory[need_item] -= need_amt
                    if give_item in inventory:
                        inventory[give_item] += give_amt
                    else:
                        inventory[give_item] = give_amt
                    hud_message = "Traded!"
                    hud_message_timer = 120
                else:
                    hud_message = "Not enough %s!" % need_item
                    hud_message_timer = 120
        glutPostRedisplay()
        return

    # Play mode
    if key == b'w' and not fishing_active:
        nx = player_pos[0] + player_speed * math.sin(math.radians(player_angle))
        nz = player_pos[2] + player_speed * math.cos(math.radians(player_angle))
        nx = max(-GRID_LENGTH, min(GRID_LENGTH, nx))
        nz = max(-GRID_LENGTH, min(GRID_LENGTH, nz))
        if not hut_wall_collision(nx, nz):
            player_pos[0] = nx
            player_pos[2] = nz
    elif key == b's' and not fishing_active:
        nx = player_pos[0] - player_speed * math.sin(math.radians(player_angle))
        nz = player_pos[2] - player_speed * math.cos(math.radians(player_angle))
        nx = max(-GRID_LENGTH, min(GRID_LENGTH, nx))
        nz = max(-GRID_LENGTH, min(GRID_LENGTH, nz))
        if not hut_wall_collision(nx, nz):
            player_pos[0] = nx
            player_pos[2] = nz
    elif key == b'a' and not fishing_active:
        player_angle += 5.0
    elif key == b'd' and not fishing_active:
        player_angle -= 5.0
    elif key == b'v':
        first_person = not first_person
        hud_message = "First Person" if first_person else "Third Person"
        hud_message_timer = 80
    elif key == b'f':
        # Fishing only near pond
        pond_dist = distance(player_pos, POND_POS)
        if pond_dist > POND_RADIUS + 50 and not fishing_active:
            hud_message = "Go near the pond to fish!"
            hud_message_timer = 80
        else:
            fishing_active = not fishing_active
            if fishing_active:
                fishing_line_cast = True
                fishing_timer = 0
                fish_on = False
                hud_message = "Fishing started!"
                hud_message_timer = 80
            else:
                fishing_line_cast = False
                hud_message = "Stopped fishing."
                hud_message_timer = 80
    elif key == b'e':
        # Harvest crops
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                plot = farm_plots[i][j]
                if not plot["owned"] or plot["crop_type"] == "none":
                    continue
                px = (i - GRID_SIZE // 2) * PLOT_SIZE + PLOT_SIZE // 2 + FARM_OFFSET_X
                pz = (j - GRID_SIZE // 2) * PLOT_SIZE + PLOT_SIZE // 2 + FARM_OFFSET_Z
                if distance(player_pos, [px, 0, pz]) < 50 and plot["growth_stage"] == 3:
                    ct = plot["crop_type"]
                    if ct in inventory:
                        inventory[ct] += 1
                    player_currency += 1
                    plot["growth_stage"] = 0
                    plot["growth_timer"] = 0.0
                    plot["is_tree"] = False
                    hud_message = "Harvested %s!" % ct
                    hud_message_timer = 80
                    break
        # Harvest carrots
        for plot in carrot_plots:
            if plot["active"]:
                px = plot["x"] + PLOT_SIZE // 2
                pz = plot["z"] + PLOT_SIZE // 2
                if distance(player_pos, [px, 0, pz]) < 50:
                    plot["active"] = False
                    plot["timer"] = 2000
                    inventory["carrot"] = inventory.get("carrot", 0) + 1
                    hud_message = "Harvested carrot!"
                    hud_message_timer = 80
                    break
        # Check villager trade
        for v in villagers:
            if v["trade_active"]:
                current_trader = v
                game_state = "trading"
                break
    elif key == b' ':
        pass
    elif key == b'c':
        game_state = "crafting"
    elif key == b't':
        for v in villagers:
            if v["trade_active"]:
                current_trader = v
                game_state = "trading"
                break
    elif key == b'h':
        for food, val in [("roast", 50), ("stew", 35), ("bread", 20)]:
            if cooked_food.get(food, 0) > 0:
                cooked_food[food] -= 1
                player_health = min(100, player_health + val)
                hud_message = "Ate %s! +%d HP" % (food, val)
                hud_message_timer = 120
                break
    elif key == b'q':
        auto_fire = not auto_fire
        hud_message = "Auto-Fire ON" if auto_fire else "Auto-Fire OFF"
        hud_message_timer = 80

    glutPostRedisplay()


def specialKeyListener(key, x, y):
    global camera_height, camera_angle, menu_selected, crafting_selected, trading_selected
    global inventory_selected, death_selected

    if game_state == "dead":
        if key == GLUT_KEY_UP:
            death_selected = max(0, death_selected - 1)
        elif key == GLUT_KEY_DOWN:
            death_selected = min(1, death_selected + 1)
        glutPostRedisplay()
        return

    if game_state == "menu":
        if key == GLUT_KEY_UP:
            menu_selected = (menu_selected - 1) % len(MENU_ITEMS)
        elif key == GLUT_KEY_DOWN:
            menu_selected = (menu_selected + 1) % len(MENU_ITEMS)
        glutPostRedisplay()
        return

    if game_state == "inventory":
        items = []
        for k, v in inventory.items():
            if v > 0:
                items.append(k)
        for k, v in cooked_food.items():
            if v > 0:
                items.append(k)
        if key == GLUT_KEY_UP:
            inventory_selected = max(0, inventory_selected - 1)
        elif key == GLUT_KEY_DOWN:
            inventory_selected = min(max(0, len(items) - 1), inventory_selected + 1)
        glutPostRedisplay()
        return

    if game_state == "crafting":
        if key == GLUT_KEY_UP:
            crafting_selected = max(0, crafting_selected - 1)
        elif key == GLUT_KEY_DOWN:
            crafting_selected = min(len(RECIPES) - 1, crafting_selected + 1)
        glutPostRedisplay()
        return

    if key == GLUT_KEY_UP:
        camera_height = min(900, camera_height + 20)
    elif key == GLUT_KEY_DOWN:
        camera_height = max(100, camera_height - 20)
    elif key == GLUT_KEY_LEFT:
        camera_angle += 3.0
    elif key == GLUT_KEY_RIGHT:
        camera_angle -= 3.0

    glutPostRedisplay()


def mouseListener(button, state, x, y):
    global fish_caught, hud_message, hud_message_timer, game_state, menu_open, fish_on, fishing_timer
    if game_state in ("dead", "menu", "crafting", "trading", "inventory"):
        glutPostRedisplay()
        return
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        if fishing_active and fish_on:
            fish_caught += 1
            inventory["wheat"] += 1
            fish_on = False
            fishing_timer = 0
            hud_message = "Caught a fish!"
            hud_message_timer = 120
        else:
            speed = 15.0
            bdir = [speed * math.sin(math.radians(player_angle)),
                    0,
                    speed * math.cos(math.radians(player_angle))]
            bpos = [player_pos[0], player_pos[1] + 15, player_pos[2]]
            bullets.append({"pos": bpos, "dir": bdir, "ttl": 100})
    glutPostRedisplay()


# ---------------------------------------------------------------------------
# 9. showScreen()
# ---------------------------------------------------------------------------

def showScreen():
    r, g, b = get_sky_color()
    glClearColor(r, g, b, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glEnable(GL_DEPTH_TEST)
    glLoadIdentity()
    glViewport(0, 0, WINDOW_W, WINDOW_H)

    setupCamera()

    # 3D world
    draw_sky()
    draw_sun_moon()
    draw_stars()
    draw_clouds()
    draw_weather()
    draw_ground()
    draw_crossroad()
    draw_pond()
    draw_hut()
    draw_farm()
    draw_carrot_farm()
    draw_scenery()
    draw_villagers()
    for e in enemies:
        draw_enemy(e)
    draw_bullets()
    if not first_person:
        draw_player()
    draw_fishing_scene()

    # 2D overlays
    draw_hud()
    draw_menu()
    draw_trading_ui()
    draw_crafting_ui()
    draw_inventory_ui()
    draw_death_screen()


    glutSwapBuffers()


# ---------------------------------------------------------------------------
# 10. idle()
# ---------------------------------------------------------------------------

def idle():
    global hud_message, hud_message_timer, game_state, player_dead
    global auto_fire_timer, player_angle, player_health
    if game_state == "play":
        # Heal near hut
        if distance(player_pos, [-350, 0, 350]) < 100:
            player_health = min(100, player_health + 0.05)
        update_day_night()
        update_crops()
        update_enemies()
        update_bullets()
        update_fishing()
        update_weather()
        check_villager_proximity()
        
        # Submerge player
        dist_to_pond = math.hypot(player_pos[0] - POND_POS[0], player_pos[2] - POND_POS[2])
        if dist_to_pond < POND_RADIUS * 0.7:
            target_y = -12.0
        elif dist_to_pond < POND_RADIUS:
            target_y = -6.0 
        else:
            target_y = 0.0    # On land
            
        player_pos[1] += (target_y - player_pos[1]) * 0.1
        
        # Auto-fire
        if auto_fire and enemies:
            auto_fire_timer += 1
            if auto_fire_timer >= 15:
                auto_fire_timer = 0
                closest = None
                closest_dist = 99999
                for e in enemies:
                    d = distance(player_pos, e["pos"])
                    if d < closest_dist:
                        closest_dist = d
                        closest = e
                if closest and closest_dist < 300:
                    dx = closest["pos"][0] - player_pos[0]
                    dz = closest["pos"][2] - player_pos[2]
                    b_angle = math.degrees(math.atan2(dx, dz))
                    speed = 15.0
                    bdir = [speed * math.sin(math.radians(b_angle)),
                            0,
                            speed * math.cos(math.radians(b_angle))]
                    bpos = [player_pos[0], player_pos[1] + 15, player_pos[2]]
                    bullets.append({"pos": bpos, "dir": bdir, "ttl": 100})
        # Carrot respawn
        for plot in carrot_plots:
            if not plot["active"]:
                plot["timer"] -= 1
                if plot["timer"] <= 0:
                    plot["active"] = True
        # Death check
        if player_health <= 0 and not player_dead:
            player_dead = True
            game_state = "dead"
    if hud_message_timer > 0:
        hud_message_timer -= 1
    else:
        hud_message = ""
    glutPostRedisplay()


# ---------------------------------------------------------------------------
# 11. setupCamera()
# ---------------------------------------------------------------------------

def setupCamera():
    # Configures perspective/camera
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, WINDOW_W / WINDOW_H, 1.0, 3000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if first_person:
        # First person
        eye_x = player_pos[0]
        eye_y = player_pos[1] + 40
        eye_z = player_pos[2]
        look_x = eye_x + 100 * math.sin(math.radians(player_angle))
        look_z = eye_z + 100 * math.cos(math.radians(player_angle))
        gluLookAt(eye_x, eye_y, eye_z, look_x, eye_y, look_z, 0, 1, 0)
    else:
        cam_x = player_pos[0] + camera_radius * math.sin(math.radians(camera_angle))
        cam_z = player_pos[2] + camera_radius * math.cos(math.radians(camera_angle))
        cam_y = camera_height
        gluLookAt(cam_x, cam_y, cam_z,
                  player_pos[0], player_pos[1], player_pos[2],
                  0, 1, 0)


# ---------------------------------------------------------------------------
# 12. main()
# ---------------------------------------------------------------------------

def main():
    """Entry point. Sets up GLUT window, initializes game state, starts main loop."""
    global QUADRIC
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Nightfall Farm")

    # Enable depth testing
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)

    # Cache quadric
    QUADRIC = gluNewQuadric()

    # Initialize game systems
    init_farm()

    # Register callbacks
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()


# ---------------------------------------------------------------------------
# 13. Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
