import math
import random
from dataclasses import dataclass, field

import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError:
    mp = None


WIDTH = 1100
HEIGHT = 720
FPS = 30
LANE_Y = HEIGHT // 2
BASE_RADIUS = 44
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

BLUE = (227, 120, 55)
RED = (64, 82, 230)
GOLD = (56, 191, 236)
GREEN = (96, 205, 110)
WHITE = (232, 236, 240)
DARK = (22, 27, 35)
CYAN = (238, 211, 94)
VIOLET = (205, 106, 190)
STONE = (92, 92, 104)
SHADOW = (10, 12, 16)
START_BUTTON = (730, 565, 1000, 635)
SELECT_BUTTON = (420, 628, 680, 680)
RESTART_BUTTON = (410, 430, 690, 500)
PLAY_AGAIN_BUTTON = (320, 430, 540, 500)
EXIT_BUTTON = (600, 430, 820, 500)
APP_STATE = {
    "screen": "start",
    "start_clicked": False,
    "restart_clicked": False,
    "exit_clicked": False,
    "selected_hero": 0,
}
STATIC_ARENA = None
START_SCREEN_CACHE = None
SELECT_SCREEN_CACHE = {}

HERO_OPTIONS = [
    {
        "name": "Aiko",
        "title": "Blade Dancer",
        "role": "Fast assassin",
        "hp": 205,
        "damage": 34,
        "range": 78,
        "speed": 7.2,
        "primary": (232, 96, 92),
        "accent": (70, 225, 245),
        "hair": (248, 232, 150),
        "weapon": "blade",
    },
    {
        "name": "Ren",
        "title": "Crystal Mage",
        "role": "Long range skill",
        "hp": 185,
        "damage": 28,
        "range": 112,
        "speed": 5.5,
        "primary": (190, 96, 238),
        "accent": (96, 225, 255),
        "hair": (92, 214, 255),
        "weapon": "staff",
    },
    {
        "name": "Mika",
        "title": "Sun Guardian",
        "role": "Tank fighter",
        "hp": 285,
        "damage": 24,
        "range": 82,
        "speed": 4.9,
        "primary": (80, 158, 245),
        "accent": (74, 232, 132),
        "hair": (62, 78, 94),
        "weapon": "shield",
    },
    {
        "name": "Sora",
        "title": "Storm Archer",
        "role": "Mobile marksman",
        "hp": 215,
        "damage": 31,
        "range": 122,
        "speed": 6.5,
        "primary": (74, 202, 160),
        "accent": (246, 214, 84),
        "hair": (234, 132, 222),
        "weapon": "bow",
    },
    {
        "name": "Kuro",
        "title": "Shadow Ronin",
        "role": "Burst duelist",
        "hp": 235,
        "damage": 38,
        "range": 74,
        "speed": 5.9,
        "primary": (96, 86, 128),
        "accent": (235, 72, 108),
        "hair": (34, 36, 48),
        "weapon": "katana",
    },
]


def clamp(value, low, high):
    return max(low, min(high, value))


def mix(color, amount):
    return tuple(int(clamp(c + (255 - c) * amount, 0, 255)) for c in color)


def shade(color, amount):
    return tuple(int(clamp(c * amount, 0, 255)) for c in color)


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def norm(dx, dy):
    length = math.hypot(dx, dy)
    if length <= 0.0001:
        return 0.0, 0.0
    return dx / length, dy / length


@dataclass
class Entity:
    x: float
    y: float
    team: int
    hp: float
    max_hp: float
    radius: int
    damage: float
    attack_range: float
    attack_cd: int
    speed: float = 0.0
    cooldown: int = 0
    alive: bool = True

    def hurt(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False


@dataclass
class Hero(Entity):
    level: int = 1
    xp: int = 0
    gold: int = 0
    kills: int = 0
    regen_cd: int = 0
    skill_q_cd: int = 0
    skill_e_cd: int = 0
    dash_cd: int = 0
    facing_x: float = 1.0
    facing_y: float = 0.0
    style: int = 0


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    team: int
    damage: float
    radius: int
    ttl: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: tuple
    ttl: int = 28


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple
    radius: int
    ttl: int


@dataclass
class Pickup:
    x: float
    y: float
    kind: str
    ttl: int = FPS * 16


@dataclass
class Controls:
    dx: float = 0.0
    dy: float = 0.0
    attack: bool = False
    skill_q: bool = False
    skill_e: bool = False
    dash: bool = False
    heal: bool = False
    label: str = "Keyboard"
    camera_frame: np.ndarray | None = None
    target_x: float | None = None
    target_y: float | None = None
    hand_visible: bool = False


@dataclass
class GameState:
    hero: Hero = field(default_factory=lambda: make_hero(0, 160, LANE_Y, 0))
    enemy_hero: Hero = field(default_factory=lambda: make_hero(4, WIDTH - 190, LANE_Y, 1, facing_x=-1.0))
    allied_base: Entity = field(default_factory=lambda: Entity(70, LANE_Y, 0, 700, 700, BASE_RADIUS, 22, 125, 25))
    enemy_base: Entity = field(default_factory=lambda: Entity(WIDTH - 70, LANE_Y, 1, 700, 700, BASE_RADIUS, 22, 125, 25))
    towers: list = field(default_factory=list)
    minions: list = field(default_factory=list)
    projectiles: list = field(default_factory=list)
    texts: list = field(default_factory=list)
    particles: list = field(default_factory=list)
    pickups: list = field(default_factory=list)
    frame: int = 0
    spawn_timer: int = 0
    pickup_timer: int = FPS * 8
    paused: bool = False
    won: bool = False
    lost: bool = False
    hero_respawn_timer: int = 0
    enemy_respawn_timer: int = 0


def make_hero(style, x, y, team, facing_x=1.0):
    option = HERO_OPTIONS[style % len(HERO_OPTIONS)]
    hp = option["hp"] + (28 if team == 1 else 0)
    damage = option["damage"] - (4 if team == 1 else 0)
    return Hero(
        x,
        y,
        team,
        hp,
        hp,
        22,
        damage,
        option["range"],
        14,
        option["speed"],
        facing_x=facing_x,
        style=style % len(HERO_OPTIONS),
    )


class HandController:
    def __init__(self, camera_id=0):
        self.available = False
        self.cap = None
        self.hands = None
        self.mp_draw = None
        self.camera_id = camera_id
        self.smooth_target = None
        self.label = "Webcam off"

        if mp is None:
            self.label = "Install mediapipe for webcam controls"
            return

        self.cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.label = "Webcam not found"
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.hands = mp.solutions.hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.65,
            min_tracking_confidence=0.55,
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.available = True
        self.label = "Show hand to camera"

    def read(self):
        controls = Controls(label=self.label)
        if not self.available:
            return controls

        ok, frame = self.cap.read()
        if not ok:
            controls.label = "Camera read failed"
            return controls

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        cv2.rectangle(frame, (center_x - 48, center_y - 48), (center_x + 48, center_y + 48), (90, 110, 125), 1)
        cv2.circle(frame, (center_x, center_y), 4, GOLD, -1)

        if not result.multi_hand_landmarks:
            controls.label = "No hand"
            controls.camera_frame = frame
            return controls

        controls.hand_visible = True
        landmarks = result.multi_hand_landmarks[0]
        self.mp_draw.draw_landmarks(frame, landmarks, mp.solutions.hands.HAND_CONNECTIONS)
        lm = landmarks.landmark

        index_tip = lm[8]
        ix = int(index_tip.x * w)
        iy = int(index_tip.y * h)
        cv2.circle(frame, (ix, iy), 9, GOLD, -1)

        target_x = clamp(index_tip.x * WIDTH, 35, WIDTH - 35)
        target_y = clamp(index_tip.y * HEIGHT, 80, HEIGHT - 65)
        if self.smooth_target is None:
            self.smooth_target = [target_x, target_y]
        else:
            self.smooth_target[0] = self.smooth_target[0] * 0.72 + target_x * 0.28
            self.smooth_target[1] = self.smooth_target[1] * 0.72 + target_y * 0.28
        controls.target_x = self.smooth_target[0]
        controls.target_y = self.smooth_target[1]

        dx = (ix - center_x) / 120
        dy = (iy - center_y) / 100
        if abs(dx) < 0.30:
            dx = 0
        if abs(dy) < 0.30:
            dy = 0
        controls.dx = clamp(dx, -1, 1)
        controls.dy = clamp(dy, -1, 1)

        fingers = self._fingers_up(lm)
        thumb_index_distance = math.hypot((lm[4].x - lm[8].x) * w, (lm[4].y - lm[8].y) * h)
        controls.attack = thumb_index_distance < 34
        controls.skill_q = fingers[1] and fingers[2] and not fingers[3] and not fingers[4]
        controls.skill_e = fingers[1] and fingers[2] and fingers[3] and not fingers[4]
        controls.dash = fingers[0] and fingers[1] and fingers[2] and fingers[3] and fingers[4]
        controls.heal = not any(fingers)

        if controls.attack:
            controls.label = "Pinch: attack"
        elif controls.dash:
            controls.label = "Open palm: dash"
        elif controls.skill_q:
            controls.label = "Two fingers: Q"
        elif controls.skill_e:
            controls.label = "Three fingers: E"
        elif controls.heal:
            controls.label = "Fist: heal"
        else:
            controls.label = "Index finger: move"

        cv2.putText(frame, controls.label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.68, WHITE, 2, cv2.LINE_AA)
        cv2.putText(frame, "Move index. Pinch attack. Open palm dash.", (12, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)
        controls.camera_frame = frame
        return controls

    @staticmethod
    def _fingers_up(lm):
        thumb = lm[4].x < lm[3].x
        index = lm[8].y < lm[6].y
        middle = lm[12].y < lm[10].y
        ring = lm[16].y < lm[14].y
        pinky = lm[20].y < lm[18].y
        return [thumb, index, middle, ring, pinky]

    def release(self):
        if self.cap is not None:
            self.cap.release()
        if self.hands is not None:
            self.hands.close()


def open_hand_controller(camera_id):
    controller = HandController(camera_id)
    if controller.available:
        return controller

    for fallback_id in range(3):
        if fallback_id == camera_id:
            continue
        controller.release()
        controller = HandController(fallback_id)
        if controller.available:
            return controller
    return controller


def make_game(selected_hero=0):
    game = GameState()
    game.hero = make_hero(selected_hero, 160, LANE_Y, 0)
    enemy_style = (selected_hero + 2) % len(HERO_OPTIONS)
    game.enemy_hero = make_hero(enemy_style, WIDTH - 190, LANE_Y, 1, facing_x=-1.0)
    game.towers = [
        Entity(330, LANE_Y - 115, 0, 360, 360, 27, 32, 175, 34),
        Entity(330, LANE_Y + 115, 0, 360, 360, 27, 32, 175, 34),
        Entity(WIDTH - 330, LANE_Y - 115, 1, 360, 360, 27, 32, 175, 34),
        Entity(WIDTH - 330, LANE_Y + 115, 1, 360, 360, 27, 32, 175, 34),
    ]
    return game


def spawn_wave(game):
    for i in range(4):
        game.minions.append(Entity(105 - i * 24, LANE_Y + random.randint(-22, 22), 0, 70, 70, 11, 10, 44, 22, 2.1))
        game.minions.append(Entity(WIDTH - 105 + i * 24, LANE_Y + random.randint(-22, 22), 1, 70, 70, 11, 10, 44, 22, 2.1))


def enemies_for(game, team):
    pool = []
    if game.hero.team != team and game.hero.alive:
        pool.append(game.hero)
    if game.enemy_hero.team != team and game.enemy_hero.alive:
        pool.append(game.enemy_hero)
    for entity in game.towers + game.minions:
        if entity.team != team and entity.alive:
            pool.append(entity)
    enemy_base = game.enemy_base if team == 0 else game.allied_base
    if enemy_base.alive and team_defenses_destroyed(game, enemy_base.team):
        pool.append(enemy_base)
    return pool


def team_defenses_destroyed(game, team):
    return all(not tower.alive for tower in game.towers if tower.team == team)


def team_eliminated(game, team):
    base = game.allied_base if team == 0 else game.enemy_base
    return team_defenses_destroyed(game, team) and not base.alive


def lane_objective(game, team):
    enemy_team = 1 - team
    towers = [tower for tower in game.towers if tower.team == enemy_team and tower.alive]
    if towers:
        return min(towers, key=lambda tower: tower.x if team == 0 else -tower.x)
    base = game.enemy_base if team == 0 else game.allied_base
    return base if base.alive else None


def nearest_enemy(game, entity, max_distance=None):
    enemies = enemies_for(game, entity.team)
    if not enemies:
        return None
    target = min(enemies, key=lambda other: dist(entity, other))
    if max_distance is not None and dist(entity, target) > max_distance:
        return None
    return target


def attack_if_ready(game, attacker, target):
    if attacker.cooldown > 0 or not target:
        return
    if dist(attacker, target) <= attacker.attack_range + attacker.radius + target.radius:
        target.hurt(attacker.damage)
        attacker.cooldown = attacker.attack_cd
        game.texts.append(FloatingText(target.x, target.y - 20, f"-{int(attacker.damage)}", RED if target.team else BLUE))
        for _ in range(5):
            game.particles.append(Particle(target.x, target.y, random.uniform(-1.5, 1.5), random.uniform(-2.1, 0.3), GOLD, 3, 16))


def update_minion(game, minion):
    if minion.cooldown > 0:
        minion.cooldown -= 1

    nearby_enemies = [
        enemy for enemy in enemies_for(game, minion.team)
        if math.hypot(enemy.x - minion.x, enemy.y - minion.y) <= 150
    ]
    target = min(nearby_enemies, key=lambda enemy: dist(minion, enemy), default=None)
    if target is None:
        target = lane_objective(game, minion.team)

    if target is None:
        return

    if target and dist(minion, target) <= minion.attack_range + minion.radius + target.radius:
        attack_if_ready(game, minion, target)
        return

    ux, uy = norm(target.x - minion.x, target.y - minion.y)
    minion.x += ux * minion.speed
    minion.y += uy * minion.speed
    minion.y += clamp(LANE_Y - minion.y, -0.45, 0.45)


def update_tower_or_base(game, entity):
    if entity.cooldown > 0:
        entity.cooldown -= 1
    target = nearest_enemy(game, entity, entity.attack_range)
    attack_if_ready(game, entity, target)


def update_enemy_hero(game):
    enemy = game.enemy_hero
    if not enemy.alive:
        if game.enemy_respawn_timer <= 0:
            return
        game.enemy_respawn_timer -= 1
        if game.enemy_respawn_timer <= 0:
            enemy.x = WIDTH - 190
            enemy.y = LANE_Y
            enemy.hp = enemy.max_hp
            enemy.alive = True
            game.texts.append(FloatingText(enemy.x - 45, enemy.y - 58, "Enemy revived", RED, 38))
        return

    if enemy.cooldown > 0:
        enemy.cooldown -= 1

    if game.enemy_base.alive and dist(enemy, game.enemy_base) <= BASE_RADIUS + 60:
        enemy.hp = min(enemy.max_hp, enemy.hp + 2.2)

    target = nearest_enemy(game, enemy, 420)
    if target is None:
        target = lane_objective(game, enemy.team)

    distance = dist(enemy, target)
    if distance <= enemy.attack_range + enemy.radius + target.radius:
        attack_if_ready(game, enemy, target)
        return

    ux, uy = norm(target.x - enemy.x, target.y - enemy.y)
    enemy.facing_x, enemy.facing_y = ux, uy
    enemy.x = clamp(enemy.x + ux * enemy.speed, 40, WIDTH - 40)
    enemy.y = clamp(enemy.y + uy * enemy.speed, 85, HEIGHT - 70)


def update_player_respawn(game):
    hero = game.hero
    if hero.alive:
        return
    if game.hero_respawn_timer <= 0:
        game.hero_respawn_timer = FPS * 5
        game.texts.append(FloatingText(game.allied_base.x + 18, game.allied_base.y - 82, "Reviving...", GOLD, 50))
    game.hero_respawn_timer -= 1
    if game.hero_respawn_timer <= 0:
        hero.x = 160
        hero.y = LANE_Y
        hero.hp = hero.max_hp
        hero.alive = True
        hero.cooldown = 0
        hero.skill_q_cd = 0
        hero.skill_e_cd = 0
        hero.regen_cd = 0
        game.texts.append(FloatingText(hero.x - 24, hero.y - 58, "Revived", GREEN, 42))


def update_base_healing(game):
    hero = game.hero
    if hero.alive and game.allied_base.alive and dist(hero, game.allied_base) <= BASE_RADIUS + 72:
        if hero.hp < hero.max_hp:
            hero.hp = hero.max_hp
            game.texts.append(FloatingText(hero.x - 20, hero.y - 58, "Base heal", GREEN, 34))

    enemy = game.enemy_hero
    if enemy.alive and game.enemy_base.alive and dist(enemy, game.enemy_base) <= BASE_RADIUS + 72:
        enemy.hp = min(enemy.max_hp, enemy.hp + 4.0)


def update_projectiles(game):
    for projectile in game.projectiles:
        projectile.x += projectile.vx
        projectile.y += projectile.vy
        projectile.ttl -= 1
        for target in enemies_for(game, projectile.team):
            if math.hypot(projectile.x - target.x, projectile.y - target.y) <= projectile.radius + target.radius:
                target.hurt(projectile.damage)
                projectile.ttl = 0
                game.texts.append(FloatingText(target.x, target.y - 24, f"-{int(projectile.damage)}", GOLD))
                break
    game.projectiles = [p for p in game.projectiles if p.ttl > 0 and 0 <= p.x <= WIDTH and 0 <= p.y <= HEIGHT]


def add_xp(game, amount):
    hero = game.hero
    hero.xp += amount
    needed = hero.level * 100
    while hero.xp >= needed:
        hero.xp -= needed
        hero.level += 1
        hero.max_hp += 18
        hero.hp = min(hero.max_hp, hero.hp + 45)
        hero.damage += 3
        game.texts.append(FloatingText(hero.x - 24, hero.y - 58, f"LEVEL {hero.level}", GOLD, 44))
        for _ in range(22):
            game.particles.append(Particle(hero.x, hero.y - 18, random.uniform(-2.8, 2.8), random.uniform(-3.2, 1.2), HERO_OPTIONS[hero.style]["accent"], 4, 30))
        needed = hero.level * 100


def spawn_pickup(game):
    kind = random.choice(["heal", "gold", "boost"])
    x = random.randint(250, WIDTH - 250)
    y = random.choice([random.randint(170, 270), random.randint(455, 610), random.randint(LANE_Y - 38, LANE_Y + 38)])
    game.pickups.append(Pickup(x, y, kind))


def update_pickups(game):
    game.pickup_timer -= 1
    if game.pickup_timer <= 0 and len(game.pickups) < 3:
        spawn_pickup(game)
        game.pickup_timer = FPS * 9

    hero = game.hero
    kept = []
    for pickup in game.pickups:
        pickup.ttl -= 1
        if pickup.ttl <= 0:
            continue
        if math.hypot(hero.x - pickup.x, hero.y - pickup.y) <= hero.radius + 22:
            if pickup.kind == "heal":
                hero.hp = min(hero.max_hp, hero.hp + 70)
                game.texts.append(FloatingText(hero.x, hero.y - 40, "+70 HP", GREEN, 34))
            elif pickup.kind == "gold":
                hero.gold += 55
                add_xp(game, 35)
                game.texts.append(FloatingText(hero.x, hero.y - 40, "+55 GOLD", GOLD, 34))
            else:
                hero.cooldown = 0
                hero.skill_q_cd = max(0, hero.skill_q_cd - FPS)
                hero.skill_e_cd = max(0, hero.skill_e_cd - FPS)
                game.texts.append(FloatingText(hero.x, hero.y - 40, "ENERGY", CYAN, 34))
            for _ in range(16):
                game.particles.append(Particle(pickup.x, pickup.y, random.uniform(-2.3, 2.3), random.uniform(-2.6, 0.8), pickup_color(pickup.kind), 4, 24))
            continue
        kept.append(pickup)
    game.pickups = kept


def update_hero(game, key, controls):
    hero = game.hero
    if not hero.alive:
        return

    if hero.cooldown > 0:
        hero.cooldown -= 1
    if hero.skill_q_cd > 0:
        hero.skill_q_cd -= 1
    if hero.skill_e_cd > 0:
        hero.skill_e_cd -= 1
    if hero.dash_cd > 0:
        hero.dash_cd -= 1
    if hero.regen_cd > 0:
        hero.regen_cd -= 1

    dx = controls.dx
    dy = controls.dy
    if key in (ord("a"), ord("A")):
        dx -= 1
    if key in (ord("d"), ord("D")):
        dx += 1
    if key in (ord("w"), ord("W")):
        dy -= 1
    if key in (ord("s"), ord("S")):
        dy += 1

    if controls.target_x is not None and controls.target_y is not None:
        tx = controls.target_x - hero.x
        ty = controls.target_y - hero.y
        distance = math.hypot(tx, ty)
        if distance > 8:
            tux, tuy = norm(tx, ty)
            hero.facing_x, hero.facing_y = tux, tuy
            step = min(hero.speed * 1.25, distance * 0.20)
            hero.x = clamp(hero.x + tux * step, 35, WIDTH - 35)
            hero.y = clamp(hero.y + tuy * step, 80, HEIGHT - 65)
    elif dx or dy:
        ux, uy = norm(dx, dy)
        hero.facing_x, hero.facing_y = ux, uy
        hero.x = clamp(hero.x + ux * hero.speed, 35, WIDTH - 35)
        hero.y = clamp(hero.y + uy * hero.speed, 80, HEIGHT - 65)

    if (key in (ord("f"), ord("F")) or controls.dash) and hero.dash_cd == 0:
        hero.x = clamp(hero.x + hero.facing_x * 82, 35, WIDTH - 35)
        hero.y = clamp(hero.y + hero.facing_y * 82, 80, HEIGHT - 65)
        hero.dash_cd = FPS * 4
        for _ in range(18):
            game.particles.append(Particle(hero.x, hero.y, random.uniform(-3.0, 3.0), random.uniform(-2.2, 2.2), HERO_OPTIONS[hero.style]["accent"], 4, 20))

    if key == 32 or controls.attack:
        target = nearest_enemy(game, hero, hero.attack_range + 60)
        attack_if_ready(game, hero, target)

    if (key in (ord("q"), ord("Q")) or controls.skill_q) and hero.skill_q_cd == 0:
        game.projectiles.append(Projectile(hero.x, hero.y, hero.facing_x * 13, hero.facing_y * 13, hero.team, 54, 9, 42))
        hero.skill_q_cd = 32
        for _ in range(8):
            game.particles.append(Particle(hero.x, hero.y, random.uniform(-1.7, 1.7), random.uniform(-1.7, 1.7), CYAN, 3, 18))

    if (key in (ord("e"), ord("E")) or controls.skill_e) and hero.skill_e_cd == 0:
        for target in enemies_for(game, hero.team):
            if dist(hero, target) <= 112:
                target.hurt(42)
                game.texts.append(FloatingText(target.x, target.y - 30, "-42", GOLD))
        hero.skill_e_cd = 78
        for angle in range(0, 360, 15):
            vx = math.cos(math.radians(angle)) * 2.7
            vy = math.sin(math.radians(angle)) * 2.7
            game.particles.append(Particle(hero.x, hero.y, vx, vy, VIOLET, 4, 26))

    if (key in (ord("r"), ord("R")) or controls.heal) and hero.regen_cd == 0:
        hero.hp = min(hero.max_hp, hero.hp + 58)
        hero.regen_cd = 130
        game.texts.append(FloatingText(hero.x, hero.y - 34, "+58", GREEN))


def cleanup_and_rewards(game):
    removed = []
    for entity in game.minions + game.towers + [game.enemy_hero, game.enemy_base, game.allied_base]:
        if not entity.alive and entity not in removed:
            if entity is game.enemy_hero and game.enemy_respawn_timer > 0:
                continue
            removed.append(entity)
            if entity.team == 1:
                reward = 10 if entity.radius <= 12 else 130 if entity is game.enemy_hero else 80
                game.hero.gold += reward
                add_xp(game, 18 if entity.radius <= 12 else 85)
                game.texts.append(FloatingText(entity.x, entity.y - 34, f"+{reward}g", GOLD))
                if entity is game.enemy_hero:
                    game.enemy_respawn_timer = FPS * 10

    game.minions = [m for m in game.minions if m.alive and -30 < m.x < WIDTH + 30]
    if team_eliminated(game, 1):
        game.won = True
    if team_eliminated(game, 0):
        game.lost = True


def update_texts(game):
    for text in game.texts:
        text.y -= 0.6
        text.ttl -= 1
    game.texts = [text for text in game.texts if text.ttl > 0]


def update_particles(game):
    for particle in game.particles:
        particle.x += particle.vx
        particle.y += particle.vy
        particle.vx *= 0.94
        particle.vy *= 0.94
        particle.ttl -= 1
    game.particles = [particle for particle in game.particles if particle.ttl > 0]


def update_game(game, key, controls):
    if game.paused or game.won or game.lost:
        return

    game.frame += 1
    game.spawn_timer -= 1
    if game.spawn_timer <= 0:
        spawn_wave(game)
        game.spawn_timer = FPS * 7

    update_player_respawn(game)
    update_base_healing(game)
    update_hero(game, key, controls)
    for minion in list(game.minions):
        update_minion(game, minion)
    update_enemy_hero(game)
    for entity in game.towers + [game.allied_base, game.enemy_base]:
        if entity.alive:
            update_tower_or_base(game, entity)
    update_projectiles(game)
    update_pickups(game)
    cleanup_and_rewards(game)
    update_texts(game)
    update_particles(game)


def draw_bar(img, x, y, width, height, value, max_value, fill):
    cv2.rectangle(img, (int(x), int(y)), (int(x + width), int(y + height)), (52, 58, 68), -1)
    ratio = 0 if max_value <= 0 else clamp(value / max_value, 0, 1)
    cv2.rectangle(img, (int(x), int(y)), (int(x + width * ratio), int(y + height)), fill, -1)
    cv2.rectangle(img, (int(x), int(y)), (int(x + width), int(y + height)), (12, 15, 20), 1)


def team_color(team):
    return BLUE if team == 0 else RED


def hero_profile(hero):
    option = HERO_OPTIONS[hero.style % len(HERO_OPTIONS)]
    if hero.team == 1:
        option = dict(option)
        option["primary"] = shade(RED, 0.95)
        option["accent"] = HERO_OPTIONS[hero.style % len(HERO_OPTIONS)]["accent"]
    return option


def pickup_color(kind):
    if kind == "heal":
        return GREEN
    if kind == "gold":
        return GOLD
    return CYAN


def add_glow(img, center, radius, color, alpha=0.20):
    return


def fill_poly(img, points, color, outline=(14, 17, 22)):
    pts = np.array(points, dtype=np.int32)
    cv2.fillConvexPoly(img, pts, color, cv2.LINE_AA)
    cv2.polylines(img, [pts], True, outline, 1, cv2.LINE_AA)


def draw_prism(img, x, y, w, h, depth, color):
    top = [(x, y - h), (x + w, y - h - depth), (x + w * 2, y - h), (x + w, y - h + depth)]
    left = [(x, y - h), (x + w, y - h + depth), (x + w, y + depth), (x, y)]
    right = [(x + w, y - h + depth), (x + w * 2, y - h), (x + w * 2, y), (x + w, y + depth)]
    fill_poly(img, left, shade(color, 0.58))
    fill_poly(img, right, shade(color, 0.76))
    fill_poly(img, top, mix(color, 0.28))


def draw_diamond(img, x, y, size, color, outline=(15, 18, 24)):
    points = np.array([
        [x, y - size],
        [x + size, y],
        [x, y + size],
        [x - size, y],
    ], dtype=np.int32)
    cv2.fillConvexPoly(img, points, color, cv2.LINE_AA)
    cv2.polylines(img, [points], True, outline, 2, cv2.LINE_AA)


def draw_entity(img, entity):
    if not entity.alive:
        return
    if isinstance(entity, Hero):
        draw_hero(img, entity)
    else:
        draw_minion(img, entity)


def draw_minion(img, minion):
    color = team_color(minion.team)
    x = int(minion.x)
    y = int(minion.y)
    cv2.ellipse(img, (x + 6, y + 17), (24, 9), 0, 0, 360, SHADOW, -1, cv2.LINE_AA)
    add_glow(img, (x, y), 24, color, 0.10)
    draw_prism(img, x - 15, y + 10, 15, 18, 8, shade(color, 0.90))
    cv2.circle(img, (x, y - 14), 12, shade(color, 0.70), -1, cv2.LINE_AA)
    cv2.circle(img, (x - 3, y - 18), 7, mix(color, 0.36), -1, cv2.LINE_AA)
    cv2.line(img, (x + 6, y - 5), (x + 22, y - 15), mix(GOLD, 0.15), 3, cv2.LINE_AA)
    cv2.circle(img, (x + 24, y - 16), 4, GOLD, -1, cv2.LINE_AA)
    draw_bar(img, minion.x - 26, minion.y - minion.radius - 18, 52, 5, minion.hp, minion.max_hp, GREEN)


def draw_hero(img, hero):
    profile = hero_profile(hero)
    color = profile["primary"]
    accent = profile["accent"]
    hair = profile["hair"]
    weapon = profile["weapon"]
    x = int(hero.x)
    y = int(hero.y)
    pulse = 1.0 + 0.08 * math.sin(cv2.getTickCount() / cv2.getTickFrequency() * 5)
    add_glow(img, (x, y - 10), int(62 * pulse), accent, 0.14)
    cv2.ellipse(img, (x + 9, y + 33), (34, 11), 0, 0, 360, SHADOW, -1, cv2.LINE_AA)
    cv2.ellipse(img, (x, y), (int(hero.attack_range), int(hero.attack_range * 0.45)), 0, 0, 360, shade(accent, 0.85), 1, cv2.LINE_AA)

    cape = [(x - 24, y - 14), (x + 24, y - 14), (x + 31, y + 34), (x - 29, y + 34)]
    fill_poly(img, cape, shade(color, 0.62), outline=shade(color, 0.42))
    torso = [(x - 19, y - 18), (x + 19, y - 18), (x + 15, y + 26), (x - 15, y + 26)]
    fill_poly(img, torso, color, outline=shade(color, 0.45))
    fill_poly(img, [(x - 13, y - 14), (x, y - 23), (x + 13, y - 14), (x + 9, y + 8), (x - 9, y + 8)], mix(accent, 0.15), outline=shade(accent, 0.65))

    cv2.circle(img, (x, y - 37), 17, (224, 183, 154), -1, cv2.LINE_AA)
    cv2.circle(img, (x - 6, y - 38), 2, (22, 27, 35), -1, cv2.LINE_AA)
    cv2.circle(img, (x + 6, y - 38), 2, (22, 27, 35), -1, cv2.LINE_AA)
    cv2.ellipse(img, (x, y - 33), (7, 4), 0, 0, 180, (122, 64, 72), 1, cv2.LINE_AA)

    if hero.style == 0:
        fill_poly(img, [(x - 22, y - 45), (x - 4, y - 63), (x + 23, y - 47), (x + 14, y - 29), (x - 18, y - 30)], hair, outline=shade(hair, 0.55))
    elif hero.style == 1:
        cv2.circle(img, (x, y - 48), 19, hair, -1, cv2.LINE_AA)
        cv2.circle(img, (x - 10, y - 39), 10, hair, -1, cv2.LINE_AA)
        draw_diamond(img, x, y - 65, 6, accent)
    elif hero.style == 2:
        fill_poly(img, [(x - 25, y - 42), (x, y - 61), (x + 25, y - 42), (x + 17, y - 30), (x - 17, y - 30)], (52, 58, 70), outline=shade(accent, 0.55))
        cv2.line(img, (x - 21, y - 43), (x + 21, y - 43), accent, 3, cv2.LINE_AA)
    elif hero.style == 3:
        fill_poly(img, [(x - 23, y - 46), (x - 5, y - 62), (x + 24, y - 45), (x + 12, y - 29), (x - 19, y - 30)], hair, outline=shade(hair, 0.55))
        cv2.circle(img, (x + 23, y - 52), 6, accent, -1, cv2.LINE_AA)
    else:
        fill_poly(img, [(x - 24, y - 44), (x, y - 64), (x + 24, y - 44), (x + 15, y - 29), (x - 15, y - 29)], hair, outline=shade(hair, 0.55))
        cv2.line(img, (x - 15, y - 43), (x + 15, y - 43), accent, 3, cv2.LINE_AA)

    cv2.line(img, (x - 16, y + 24), (x - 25, y + 47), shade(color, 0.72), 5, cv2.LINE_AA)
    cv2.line(img, (x + 16, y + 24), (x + 24, y + 47), shade(color, 0.72), 5, cv2.LINE_AA)
    cv2.line(img, (x - 18, y - 6), (x - 37, y + 10), shade(accent, 0.92), 5, cv2.LINE_AA)
    cv2.line(img, (x + 18, y - 6), (x + 37, y + 10), shade(accent, 0.92), 5, cv2.LINE_AA)

    fx = int(x + hero.facing_x * 38)
    fy = int(y + hero.facing_y * 38)
    if weapon == "blade":
        cv2.line(img, (x + 24, y - 11), (x + 56, y - 38), WHITE, 4, cv2.LINE_AA)
        cv2.line(img, (x + 28, y - 6), (x + 58, y - 34), accent, 2, cv2.LINE_AA)
    elif weapon == "staff":
        cv2.line(img, (x + 30, y + 0), (x + 48, y - 62), GOLD, 4, cv2.LINE_AA)
        add_glow(img, (x + 48, y - 62), 18, accent, 0.24)
        cv2.circle(img, (x + 48, y - 62), 7, accent, -1, cv2.LINE_AA)
    elif weapon == "shield":
        cv2.ellipse(img, (x - 37, y + 2), (17, 24), 0, 0, 360, accent, -1, cv2.LINE_AA)
        cv2.ellipse(img, (x - 37, y + 2), (17, 24), 0, 0, 360, WHITE, 2, cv2.LINE_AA)
    elif weapon == "bow":
        cv2.ellipse(img, (x + 38, y - 10), (10, 34), 0, -80, 80, GOLD, 3, cv2.LINE_AA)
        cv2.line(img, (x + 38, y - 42), (x + 38, y + 22), WHITE, 1, cv2.LINE_AA)
    else:
        cv2.line(img, (x - 26, y - 1), (x + 52, y - 43), WHITE, 4, cv2.LINE_AA)
        cv2.line(img, (x - 17, y - 2), (x + 56, y - 37), accent, 2, cv2.LINE_AA)
    cv2.line(img, (x, y - 10), (fx, fy - 10), accent, 2, cv2.LINE_AA)
    draw_diamond(img, x, y - 72, 9, accent)
    draw_bar(img, hero.x - 45, hero.y - 78, 90, 8, hero.hp, hero.max_hp, GREEN)


def draw_tower(img, tower):
    if not tower.alive:
        return
    color = team_color(tower.team)
    x = int(tower.x)
    y = int(tower.y)
    add_glow(img, (x, y), 70, color, 0.16)
    cv2.ellipse(img, (x + 8, y + 48), (51, 15), 0, 0, 360, SHADOW, -1, cv2.LINE_AA)
    draw_prism(img, x - 34, y + 38, 34, 46, 15, STONE)
    draw_prism(img, x - 24, y - 2, 24, 42, 12, shade(STONE, 0.80))
    fill_poly(img, [(x - 35, y - 43), (x, y - 73), (x + 35, y - 43), (x + 25, y - 19), (x - 25, y - 19)], color)
    draw_diamond(img, x, y - 41, 14, GOLD)
    cv2.circle(img, (x, y - 41), 5, WHITE, -1, cv2.LINE_AA)
    draw_bar(img, tower.x - 42, tower.y + 60, 84, 7, tower.hp, tower.max_hp, GREEN)


def draw_base(img, base):
    if not base.alive:
        return
    color = team_color(base.team)
    x = int(base.x)
    y = int(base.y)
    add_glow(img, (x, y), 110, color, 0.22)
    cv2.ellipse(img, (x + 10, y + 54), (74, 20), 0, 0, 360, SHADOW, -1, cv2.LINE_AA)
    draw_prism(img, x - 58, y + 40, 58, 36, 20, shade(STONE, 0.86))
    cv2.circle(img, (x, y - 5), BASE_RADIUS + 12, shade(color, 0.72), -1, cv2.LINE_AA)
    cv2.circle(img, (x, y - 5), BASE_RADIUS + 12, mix(color, 0.18), 3, cv2.LINE_AA)
    crystal = GOLD if base.team == 0 else VIOLET
    fill_poly(img, [(x, y - 82), (x + 32, y - 22), (x, y + 16), (x - 32, y - 22)], crystal)
    fill_poly(img, [(x, y - 82), (x + 11, y - 24), (x, y + 16), (x - 11, y - 24)], mix(crystal, 0.35), outline=shade(crystal, 0.55))
    draw_bar(img, base.x - 60, base.y + 72, 120, 10, base.hp, base.max_hp, GREEN)


def draw_arena(img):
    top = np.linspace(np.array([35, 72, 60]), np.array([26, 47, 55]), HEIGHT).astype(np.uint8)
    img[:] = top[:, None, :]
    cv2.rectangle(img, (0, 0), (WIDTH, HEIGHT), DARK, 18)
    fill_poly(img, [(24, 92), (WIDTH - 24, 92), (WIDTH - 34, HEIGHT - 24), (34, HEIGHT - 24)], (42, 91, 70), outline=(58, 72, 66))

    cv2.ellipse(img, (WIDTH // 2, 90), (360, 70), 0, 0, 360, (45, 72, 78), -1, cv2.LINE_AA)
    for tower_x in (330, 440, 560, 670):
        draw_prism(img, tower_x - 28, 128, 28, 70, 14, (86, 86, 102))
        fill_poly(img, [(tower_x - 36, 50), (tower_x, 22), (tower_x + 36, 50), (tower_x + 27, 72), (tower_x - 27, 72)], (92, 84, 112))
        draw_diamond(img, tower_x, 46, 7, GOLD)
    cv2.rectangle(img, (300, 86), (700, 140), (82, 82, 96), -1)
    cv2.rectangle(img, (300, 86), (700, 140), (39, 42, 52), 2)
    cv2.putText(img, "ROYAL ARENA", (420, 122), cv2.FONT_HERSHEY_SIMPLEX, 0.62, GOLD, 2, cv2.LINE_AA)

    for x in range(58, WIDTH - 20, 72):
        draw_prism(img, x - 16, 112, 16, 28, 8, (94, 94, 106))
        cv2.rectangle(img, (x - 22, 72), (x + 20, 112), (82, 82, 96), -1)
        cv2.rectangle(img, (x - 22, 72), (x + 20, 112), (42, 44, 54), 1)
        if x % 144 == 58:
            flag_color = BLUE if x < WIDTH // 2 else RED
            fill_poly(img, [(x - 5, 78), (x + 32, 88), (x - 5, 98)], flag_color)

    for x in range(70, WIDTH - 60, 78):
        ty = 138 + (x % 4) * 17
        by = HEIGHT - 112 - (x % 3) * 18
        cv2.line(img, (x - 10, ty + 18), (x - 10, ty + 52), (58, 53, 42), 7, cv2.LINE_AA)
        cv2.circle(img, (x, ty), 28, (31, 106, 62), -1, cv2.LINE_AA)
        cv2.circle(img, (x - 19, ty + 7), 19, (47, 135, 78), -1, cv2.LINE_AA)
        cv2.circle(img, (x + 18, ty + 8), 20, (24, 88, 55), -1, cv2.LINE_AA)
        add_glow(img, (x + 18, ty - 12), 18, (82, 230, 154), 0.08)
        cv2.line(img, (x + 26, by + 18), (x + 26, by + 48), (58, 53, 42), 7, cv2.LINE_AA)
        cv2.circle(img, (x + 32, by), 26, (28, 92, 58), -1, cv2.LINE_AA)
        cv2.circle(img, (x + 14, by + 7), 17, (43, 126, 72), -1, cv2.LINE_AA)

    cv2.ellipse(img, (WIDTH // 2, 184), (178, 42), 0, 0, 360, (36, 88, 102), -1, cv2.LINE_AA)
    cv2.ellipse(img, (WIDTH // 2, 184), (178, 42), 0, 0, 360, (71, 137, 150), 2, cv2.LINE_AA)
    for x in range(395, 720, 36):
        cv2.line(img, (x, 150), (x - 28, 210), (117, 126, 118), 3, cv2.LINE_AA)

    for x in range(120, WIDTH - 120, 110):
        for y in (260, 505):
            cv2.circle(img, (x, y), 8, (74, 142, 86), -1, cv2.LINE_AA)
            cv2.circle(img, (x + 10, y + 3), 6, (210, 92, 148), -1, cv2.LINE_AA)
            cv2.circle(img, (x - 9, y + 2), 5, (236, 204, 92), -1, cv2.LINE_AA)

    cv2.line(img, (72, LANE_Y), (WIDTH - 72, LANE_Y), (62, 69, 72), 96, cv2.LINE_AA)
    cv2.line(img, (72, LANE_Y), (WIDTH - 72, LANE_Y), (118, 124, 118), 64, cv2.LINE_AA)
    for x in range(92, WIDTH - 86, 60):
        pts = [(x, LANE_Y - 25), (x + 38, LANE_Y - 17), (x + 35, LANE_Y + 18), (x - 4, LANE_Y + 25)]
        fill_poly(img, pts, (138, 139, 130), outline=(72, 75, 76))
    cv2.line(img, (72, LANE_Y), (WIDTH - 72, LANE_Y), shade(GOLD, 0.82), 2, cv2.LINE_AA)
    add_glow(img, (WIDTH // 2, LANE_Y), 100, GOLD, 0.10)
    cv2.ellipse(img, (WIDTH // 2, LANE_Y), (91, 54), 0, 0, 360, (47, 84, 82), -1, cv2.LINE_AA)
    cv2.ellipse(img, (WIDTH // 2, LANE_Y), (91, 54), 0, 0, 360, GOLD, 2, cv2.LINE_AA)
    for angle in range(0, 360, 45):
        px = int(WIDTH // 2 + math.cos(math.radians(angle)) * 72)
        py = int(LANE_Y + math.sin(math.radians(angle)) * 42)
        draw_diamond(img, px, py, 7, shade(GOLD, 0.85), outline=(60, 54, 30))
    for x, y, color in [(150, 205, BLUE), (950, 515, RED), (210, 560, CYAN), (890, 170, VIOLET)]:
        add_glow(img, (x, y), 42, color, 0.12)
        draw_diamond(img, x, y, 16, color)
    for x, y in [(118, 330), (230, 410), (870, 300), (1010, 430)]:
        add_glow(img, (x, y), 28, GOLD, 0.13)
        cv2.line(img, (x, y + 24), (x, y - 6), (54, 48, 42), 4, cv2.LINE_AA)
        cv2.circle(img, (x, y - 12), 8, GOLD, -1, cv2.LINE_AA)
    cv2.rectangle(img, (0, 0), (WIDTH, 72), (20, 25, 35), -1)
    cv2.line(img, (0, 72), (WIDTH, 72), GOLD, 2, cv2.LINE_AA)


def get_static_arena():
    global STATIC_ARENA
    if STATIC_ARENA is None:
        STATIC_ARENA = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        draw_arena(STATIC_ARENA)
    return STATIC_ARENA.copy()


def draw_hud(img, game, controls):
    hero = game.hero
    cv2.putText(img, "OpenCV MOBA Arena", (22, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.82, WHITE, 2, cv2.LINE_AA)
    draw_bar(img, 315, 17, 235, 18, hero.hp, hero.max_hp, GREEN)
    cv2.putText(img, f"HP {int(hero.hp)}/{int(hero.max_hp)}", (323, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (18, 22, 26), 1, cv2.LINE_AA)
    draw_bar(img, 315, 41, 235, 9, hero.xp, hero.level * 100, CYAN)
    cv2.putText(img, f"Lv {hero.level}", (560, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.45, CYAN, 1, cv2.LINE_AA)
    cv2.putText(img, f"Gold {hero.gold}", (620, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.62, GOLD, 2, cv2.LINE_AA)
    cv2.putText(img, "Finger follow | pinch attack | Q/E skills | F dash | pickups | Esc quit", (710, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.44, WHITE, 1, cv2.LINE_AA)
    cv2.putText(img, controls.label, (710, 57), cv2.FONT_HERSHEY_SIMPLEX, 0.45, GOLD, 1, cv2.LINE_AA)

    skills = [("Q", hero.skill_q_cd), ("E", hero.skill_e_cd), ("R", hero.regen_cd), ("F", hero.dash_cd)]
    for index, (label, cd) in enumerate(skills):
        x = 34 + index * 58
        y = HEIGHT - 55
        cv2.rectangle(img, (x, y), (x + 44, y + 44), (40, 46, 56), -1)
        cv2.rectangle(img, (x, y), (x + 44, y + 44), GOLD if cd == 0 else (85, 91, 99), 2)
        cv2.putText(img, label, (x + 13, y + 29), cv2.FONT_HERSHEY_SIMPLEX, 0.75, WHITE, 2, cv2.LINE_AA)
        if cd > 0:
            cv2.putText(img, str(math.ceil(cd / FPS)), (x + 14, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, RED, 1, cv2.LINE_AA)


def draw_pickup(img, pickup, frame):
    color = pickup_color(pickup.kind)
    x = int(pickup.x)
    y = int(pickup.y + math.sin(frame * 0.12) * 4)
    add_glow(img, (x, y), 30, color, 0.18)
    draw_diamond(img, x, y, 14, color)
    symbol = "+" if pickup.kind == "heal" else "$" if pickup.kind == "gold" else "*"
    cv2.putText(img, symbol, (x - 6, y + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (18, 22, 28), 2, cv2.LINE_AA)


def draw_particle(img, particle):
    fade = clamp(particle.ttl / 30, 0.2, 1.0)
    color = shade(particle.color, fade)
    cv2.circle(img, (int(particle.x), int(particle.y)), max(1, int(particle.radius * fade)), color, -1, cv2.LINE_AA)


def draw_camera_preview(img, controls):
    if controls.camera_frame is None:
        return
    preview = cv2.resize(controls.camera_frame, (220, 156))
    x = WIDTH - 242
    y = HEIGHT - 178
    cv2.rectangle(img, (x - 4, y - 4), (x + 224, y + 160), (31, 36, 45), -1)
    img[y:y + 156, x:x + 220] = preview
    cv2.rectangle(img, (x, y), (x + 220, y + 156), GOLD, 1)


def draw_minimap(img, game):
    x = WIDTH - 210
    y = 86
    w = 178
    h = 116
    cv2.rectangle(img, (x - 5, y - 5), (x + w + 5, y + h + 5), (20, 24, 32), -1)
    cv2.rectangle(img, (x, y), (x + w, y + h), (41, 74, 58), -1)
    cv2.line(img, (x + 10, y + h // 2), (x + w - 10, y + h // 2), (132, 138, 124), 7, cv2.LINE_AA)
    cv2.rectangle(img, (x, y), (x + w, y + h), GOLD, 1)

    def plot(entity, radius=3):
        if not entity.alive:
            return
        px = x + int(entity.x / WIDTH * w)
        py = y + int(entity.y / HEIGHT * h)
        cv2.circle(img, (px, py), radius, team_color(entity.team), -1, cv2.LINE_AA)

    for entity in [game.allied_base, game.enemy_base] + game.towers + game.minions:
        plot(entity, 4 if entity.radius > 20 else 2)
    plot(game.hero, 5)
    plot(game.enemy_hero, 5)


def draw_target_marker(img, controls):
    if controls.target_x is None or controls.target_y is None:
        return
    x = int(controls.target_x)
    y = int(controls.target_y)
    cv2.circle(img, (x, y), 17, GOLD, 2)
    cv2.line(img, (x - 23, y), (x + 23, y), GOLD, 1)
    cv2.line(img, (x, y - 23), (x, y + 23), GOLD, 1)


def render(game, controls):
    img = get_static_arena()
    draw_base(img, game.allied_base)
    draw_base(img, game.enemy_base)
    for tower in game.towers:
        draw_tower(img, tower)
    for minion in game.minions:
        draw_entity(img, minion)
    draw_entity(img, game.enemy_hero)
    draw_entity(img, game.hero)

    for projectile in game.projectiles:
        add_glow(img, (projectile.x, projectile.y), projectile.radius * 4, GOLD, 0.20)
        cv2.circle(img, (int(projectile.x), int(projectile.y)), projectile.radius, GOLD, -1, cv2.LINE_AA)
        cv2.circle(img, (int(projectile.x), int(projectile.y)), projectile.radius + 4, WHITE, 1, cv2.LINE_AA)

    for pickup in game.pickups:
        draw_pickup(img, pickup, game.frame)

    for particle in game.particles:
        draw_particle(img, particle)

    for text in game.texts:
        cv2.putText(img, text.text, (int(text.x), int(text.y)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, text.color, 2, cv2.LINE_AA)

    draw_target_marker(img, controls)
    draw_minimap(img, game)
    draw_camera_preview(img, controls)
    draw_hud(img, game, controls)

    if game.paused:
        draw_overlay(img, "PAUSED", "Press P to continue")
    if game.won:
        draw_victory_overlay(img)
    if game.lost:
        draw_defeat_overlay(img)
    return img


def draw_overlay(img, title, subtitle):
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.46, img, 0.54, 0, img)
    cv2.putText(img, title, (WIDTH // 2 - 130, HEIGHT // 2 - 18), cv2.FONT_HERSHEY_SIMPLEX, 1.6, WHITE, 3, cv2.LINE_AA)
    cv2.putText(img, subtitle, (WIDTH // 2 - 245, HEIGHT // 2 + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.65, GOLD, 2, cv2.LINE_AA)


def draw_defeat_overlay(img):
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.58, img, 0.42, 0, img)
    cv2.putText(img, "DEFEAT", (WIDTH // 2 - 122, HEIGHT // 2 - 92), cv2.FONT_HERSHEY_SIMPLEX, 1.7, RED, 4, cv2.LINE_AA)
    cv2.putText(img, "Your hero or base was destroyed.", (WIDTH // 2 - 205, HEIGHT // 2 - 38), cv2.FONT_HERSHEY_SIMPLEX, 0.70, WHITE, 2, cv2.LINE_AA)
    x1, y1, x2, y2 = RESTART_BUTTON
    cv2.rectangle(img, (x1 + 8, y1 + 9), (x2 + 8, y2 + 9), SHADOW, -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (206, 166, 76), -1)
    cv2.rectangle(img, (x1 + 5, y1 + 5), (x2 - 5, y2 - 5), (246, 222, 132), 2)
    cv2.putText(img, "RESTART", (x1 + 67, y1 + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.88, (22, 24, 30), 2, cv2.LINE_AA)
    cv2.putText(img, "Click Restart or press Enter / R", (WIDTH // 2 - 173, y2 + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.58, WHITE, 1, cv2.LINE_AA)


def draw_victory_overlay(img):
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.58, img, 0.42, 0, img)
    cv2.putText(img, "VICTORY", (WIDTH // 2 - 142, HEIGHT // 2 - 102), cv2.FONT_HERSHEY_SIMPLEX, 1.7, GOLD, 4, cv2.LINE_AA)
    cv2.putText(img, "Enemy towers and starting base destroyed.", (WIDTH // 2 - 270, HEIGHT // 2 - 48), cv2.FONT_HERSHEY_SIMPLEX, 0.70, WHITE, 2, cv2.LINE_AA)

    x1, y1, x2, y2 = PLAY_AGAIN_BUTTON
    cv2.rectangle(img, (x1 + 8, y1 + 9), (x2 + 8, y2 + 9), SHADOW, -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (206, 166, 76), -1)
    cv2.rectangle(img, (x1 + 5, y1 + 5), (x2 - 5, y2 - 5), (246, 222, 132), 2)
    cv2.putText(img, "PLAY AGAIN", (x1 + 31, y1 + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (22, 24, 30), 2, cv2.LINE_AA)

    x1, y1, x2, y2 = EXIT_BUTTON
    cv2.rectangle(img, (x1 + 8, y1 + 9), (x2 + 8, y2 + 9), SHADOW, -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (72, 78, 92), -1)
    cv2.rectangle(img, (x1 + 5, y1 + 5), (x2 - 5, y2 - 5), (180, 188, 198), 2)
    cv2.putText(img, "EXIT", (x1 + 72, y1 + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.82, WHITE, 2, cv2.LINE_AA)
    cv2.putText(img, "Click a button, or press Enter to play again / Esc to exit", (WIDTH // 2 - 294, y2 + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.54, WHITE, 1, cv2.LINE_AA)


def draw_start_screen():
    global START_SCREEN_CACHE
    if START_SCREEN_CACHE is not None:
        return START_SCREEN_CACHE.copy()
    img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    sky = np.linspace(np.array([58, 79, 91]), np.array([22, 29, 40]), HEIGHT).astype(np.uint8)
    img[:] = sky[:, None, :]

    cv2.rectangle(img, (0, 0), (WIDTH, HEIGHT), (14, 18, 26), 14)
    cv2.rectangle(img, (0, HEIGHT - 170), (WIDTH, HEIGHT), (39, 78, 55), -1)
    cv2.ellipse(img, (WIDTH // 2, HEIGHT - 150), (620, 105), 0, 0, 360, (47, 94, 62), -1, cv2.LINE_AA)
    cv2.line(img, (0, HEIGHT - 170), (WIDTH, HEIGHT - 170), (111, 117, 101), 3, cv2.LINE_AA)

    for x in range(70, 1060, 90):
        trunk = (82, 62, 45)
        leaf = (34, 86, 56) if x % 180 else (42, 103, 65)
        cv2.line(img, (x, 560), (x, 505), trunk, 7, cv2.LINE_AA)
        cv2.circle(img, (x, 494), 28, leaf, -1, cv2.LINE_AA)
        cv2.circle(img, (x - 20, 505), 20, shade(leaf, 0.86), -1, cv2.LINE_AA)
        cv2.circle(img, (x + 22, 508), 20, shade(leaf, 0.78), -1, cv2.LINE_AA)

    castle_color = (92, 93, 108)
    cv2.rectangle(img, (250, 180), (620, 390), castle_color, -1)
    cv2.rectangle(img, (250, 180), (620, 390), (37, 40, 52), 2)
    for tx in (230, 330, 520, 640):
        cv2.rectangle(img, (tx, 135), (tx + 72, 390), shade(castle_color, 0.86), -1)
        fill_poly(img, [(tx - 10, 135), (tx + 36, 88), (tx + 82, 135)], (76, 68, 91))
        cv2.rectangle(img, (tx + 24, 260), (tx + 48, 390), (34, 38, 52), -1)
    for x in range(270, 600, 48):
        cv2.rectangle(img, (x, 170), (x + 24, 198), shade(castle_color, 0.74), -1)
    cv2.rectangle(img, (392, 270), (480, 390), (41, 35, 42), -1)
    cv2.ellipse(img, (436, 270), (44, 32), 180, 0, 180, (41, 35, 42), -1, cv2.LINE_AA)

    cv2.rectangle(img, (55, 72), (520, 274), (18, 24, 34), -1)
    cv2.rectangle(img, (55, 72), (520, 274), (120, 124, 132), 1)
    cv2.putText(img, "FINGER", (82, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.45, GOLD, 3, cv2.LINE_AA)
    cv2.putText(img, "MOBA ARENA", (82, 190), cv2.FONT_HERSHEY_SIMPLEX, 1.45, WHITE, 3, cv2.LINE_AA)
    cv2.putText(img, "A webcam controlled kingdom battle", (86, 232), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (204, 211, 218), 1, cv2.LINE_AA)

    panel_x, panel_y, panel_w, panel_h = 680, 120, 360, 360
    cv2.rectangle(img, (panel_x + 8, panel_y + 10), (panel_x + panel_w + 8, panel_y + panel_h + 10), (9, 12, 18), -1)
    cv2.rectangle(img, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (24, 31, 43), -1)
    cv2.rectangle(img, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (112, 118, 130), 1)
    cv2.putText(img, "HOW TO PLAY", (panel_x + 34, panel_y + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.82, GOLD, 2, cv2.LINE_AA)
    rules = [
        "Move index finger to guide hero",
        "Pinch thumb + index to attack",
        "Two fingers: Q skill",
        "Three fingers: E burst",
        "Open palm: Dash",
        "Destroy towers and enemy crystal",
    ]
    for index, rule in enumerate(rules):
        y = panel_y + 96 + index * 42
        cv2.circle(img, (panel_x + 36, y - 5), 9, GOLD, -1, cv2.LINE_AA)
        cv2.putText(img, rule, (panel_x + 58, y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, WHITE, 1, cv2.LINE_AA)

    hero_left = make_hero(0, 170, 520, 0)
    hero_right = make_hero(4, 595, 520, 1, facing_x=-1.0)
    draw_hero(img, hero_left)
    draw_hero(img, hero_right)
    cv2.line(img, (210, 548), (552, 548), (119, 114, 101), 8, cv2.LINE_AA)
    cv2.putText(img, "Choose a hero after starting", (70, 650), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (220, 225, 230), 1, cv2.LINE_AA)

    x1, y1, x2, y2 = START_BUTTON
    cv2.rectangle(img, (x1 + 8, y1 + 9), (x2 + 8, y2 + 9), (9, 12, 18), -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (206, 166, 76), -1)
    cv2.rectangle(img, (x1 + 5, y1 + 5), (x2 - 5, y2 - 5), (246, 222, 132), 2)
    cv2.putText(img, "START GAME", (x1 + 42, y1 + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.82, (22, 24, 30), 2, cv2.LINE_AA)
    cv2.putText(img, "Click button or press Enter", (736, 664), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)
    START_SCREEN_CACHE = img.copy()
    return img


def hero_card_rect(index):
    card_w = 190
    gap = 22
    start_x = 44
    return start_x + index * (card_w + gap), 210, start_x + index * (card_w + gap) + card_w, 552


def draw_stat_bar(img, x, y, label, value, max_value, color):
    cv2.putText(img, label, (x, y + 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, WHITE, 1, cv2.LINE_AA)
    cv2.rectangle(img, (x + 62, y), (x + 154, y + 10), (45, 50, 60), -1)
    width = int(92 * clamp(value / max_value, 0, 1))
    cv2.rectangle(img, (x + 62, y), (x + 62 + width, y + 10), color, -1)
    cv2.rectangle(img, (x + 62, y), (x + 154, y + 10), (10, 12, 18), 1)


def draw_select_screen(selected):
    cached = SELECT_SCREEN_CACHE.get(selected)
    if cached is not None:
        return cached.copy()

    img = get_static_arena()
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), (7, 9, 15), -1)
    cv2.addWeighted(overlay, 0.58, img, 0.42, 0, img)
    add_glow(img, (WIDTH // 2, 116), 180, HERO_OPTIONS[selected]["accent"], 0.13)
    cv2.putText(img, "CHOOSE YOUR HERO", (318, 86), cv2.FONT_HERSHEY_SIMPLEX, 1.18, WHITE, 3, cv2.LINE_AA)
    cv2.putText(img, "Five anime-inspired fighters with different stats and weapons", (288, 126), cv2.FONT_HERSHEY_SIMPLEX, 0.58, GOLD, 1, cv2.LINE_AA)

    for index, option in enumerate(HERO_OPTIONS):
        x1, y1, x2, y2 = hero_card_rect(index)
        is_selected = index == selected
        card_color = (27, 33, 45) if not is_selected else (34, 44, 62)
        border = option["accent"] if is_selected else (91, 96, 112)
        cv2.rectangle(img, (x1 + 8, y1 + 10), (x2 + 8, y2 + 10), SHADOW, -1)
        cv2.rectangle(img, (x1, y1), (x2, y2), card_color, -1)
        cv2.rectangle(img, (x1, y1), (x2, y2), border, 2 if is_selected else 1)
        cv2.rectangle(img, (x1 + 8, y1 + 8), (x2 - 8, y1 + 172), shade(option["primary"], 0.34), -1)
        add_glow(img, ((x1 + x2) // 2, y1 + 120), 58, option["accent"], 0.16)
        preview = make_hero(index, (x1 + x2) // 2, y1 + 143, 0)
        draw_hero(img, preview)
        cv2.putText(img, option["name"], (x1 + 18, y1 + 209), cv2.FONT_HERSHEY_SIMPLEX, 0.70, WHITE, 2, cv2.LINE_AA)
        cv2.putText(img, option["title"], (x1 + 18, y1 + 233), cv2.FONT_HERSHEY_SIMPLEX, 0.43, option["accent"], 1, cv2.LINE_AA)
        cv2.putText(img, option["role"], (x1 + 18, y1 + 257), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (205, 212, 220), 1, cv2.LINE_AA)
        draw_stat_bar(img, x1 + 18, y1 + 286, "HP", option["hp"], 285, GREEN)
        draw_stat_bar(img, x1 + 18, y1 + 311, "DMG", option["damage"], 38, RED)
        draw_stat_bar(img, x1 + 18, y1 + 336, "SPD", option["speed"], 7.2, CYAN)

    x1, y1, x2, y2 = SELECT_BUTTON
    cv2.rectangle(img, (x1 + 7, y1 + 8), (x2 + 7, y2 + 8), SHADOW, -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), shade(HERO_OPTIONS[selected]["accent"], 0.88), -1)
    cv2.rectangle(img, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4), WHITE, 1)
    cv2.putText(img, "PLAY AS " + HERO_OPTIONS[selected]["name"].upper(), (x1 + 24, y1 + 36), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (18, 22, 28), 2, cv2.LINE_AA)
    cv2.putText(img, "Click a hero card, then click Play or press Enter", (344, 700), cv2.FONT_HERSHEY_SIMPLEX, 0.48, WHITE, 1, cv2.LINE_AA)
    SELECT_SCREEN_CACHE[selected] = img.copy()
    return img


def handle_mouse(event, x, y, flags, param):
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    x1, y1, x2, y2 = START_BUTTON
    if APP_STATE["screen"] == "start" and x1 <= x <= x2 and y1 <= y <= y2:
        APP_STATE["start_clicked"] = True
    if APP_STATE["screen"] == "select":
        for index in range(len(HERO_OPTIONS)):
            cx1, cy1, cx2, cy2 = hero_card_rect(index)
            if cx1 <= x <= cx2 and cy1 <= y <= cy2:
                APP_STATE["selected_hero"] = index
        sx1, sy1, sx2, sy2 = SELECT_BUTTON
        if sx1 <= x <= sx2 and sy1 <= y <= sy2:
            APP_STATE["start_clicked"] = True
    if APP_STATE["screen"] == "game":
        rx1, ry1, rx2, ry2 = RESTART_BUTTON
        if rx1 <= x <= rx2 and ry1 <= y <= ry2:
            APP_STATE["restart_clicked"] = True
        px1, py1, px2, py2 = PLAY_AGAIN_BUTTON
        if px1 <= x <= px2 and py1 <= y <= py2:
            APP_STATE["restart_clicked"] = True
        ex1, ey1, ex2, ey2 = EXIT_BUTTON
        if ex1 <= x <= ex2 and ey1 <= y <= ey2:
            APP_STATE["exit_clicked"] = True


def main():
    game = None
    camera_id = 0
    hand_controller = None
    cv2.namedWindow("OpenCV MOBA Legends", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("OpenCV MOBA Legends", WIDTH, HEIGHT)
    cv2.setMouseCallback("OpenCV MOBA Legends", handle_mouse)

    while True:
        if APP_STATE["screen"] == "start":
            frame = draw_start_screen()
            cv2.imshow("OpenCV MOBA Legends", frame)
            key = cv2.waitKey(int(1000 / FPS)) & 0xFF
            if key == 27:
                break
            if key in (13, 10) or APP_STATE["start_clicked"]:
                APP_STATE["screen"] = "select"
                APP_STATE["start_clicked"] = False
            continue

        if APP_STATE["screen"] == "select":
            frame = draw_select_screen(APP_STATE["selected_hero"])
            cv2.imshow("OpenCV MOBA Legends", frame)
            key = cv2.waitKey(int(1000 / FPS)) & 0xFF
            if key == 27:
                break
            if key in (ord("1"), ord("2"), ord("3"), ord("4"), ord("5")):
                APP_STATE["selected_hero"] = key - ord("1")
            if key in (13, 10) or APP_STATE["start_clicked"]:
                APP_STATE["screen"] = "game"
                APP_STATE["start_clicked"] = False
                game = make_game(APP_STATE["selected_hero"])
                hand_controller = open_hand_controller(camera_id)
                cv2.namedWindow("Hand Control Camera", cv2.WINDOW_NORMAL)
                cv2.resizeWindow("Hand Control Camera", 640, 480)
            continue

        controls = hand_controller.read() if hand_controller is not None else Controls(label="Keyboard")
        frame = render(game, controls)
        cv2.imshow("OpenCV MOBA Legends", frame)
        if controls.camera_frame is not None:
            cv2.imshow("Hand Control Camera", controls.camera_frame)
        key = cv2.waitKey(int(1000 / FPS)) & 0xFF

        if APP_STATE["exit_clicked"]:
            break
        if key == 27:
            break
        if game.won and (key in (13, 10, ord("r"), ord("R")) or APP_STATE["restart_clicked"]):
            APP_STATE["restart_clicked"] = False
            APP_STATE["exit_clicked"] = False
            game = make_game(APP_STATE["selected_hero"])
            continue
        if game.lost and (key in (13, 10, ord("r"), ord("R")) or APP_STATE["restart_clicked"]):
            APP_STATE["restart_clicked"] = False
            game = make_game(APP_STATE["selected_hero"])
            continue
        if key in (ord("c"), ord("C")):
            if hand_controller is not None:
                hand_controller.release()
            camera_id = (camera_id + 1) % 3
            hand_controller = open_hand_controller(camera_id)
        if key in (ord("p"), ord("P")):
            game.paused = not game.paused
        update_game(game, key, controls)

    if hand_controller is not None:
        hand_controller.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
