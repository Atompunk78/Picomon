from machine import Pin, SPI
import st7789
import vga2_16x32 as font16
import vga2_8x16 as font8
from time import sleep, ticks_us
from random import random, randint, choice, uniform
import os
import framebuf

from atomic import graphics, tileutils, utilities
from atomic import Pressed

#Copyright (c) 2025 Henry Gurney
#Licensed under CC BY-NC-ND 4.0

version = "v1.4" #with Atomic Engine version 1.2

spi = SPI(1, baudrate=60000000, polarity=1, phase=1,
          sck=Pin(10), mosi=Pin(11))

display = st7789.ST7789(
    spi, 240, 240,
    reset=Pin(12, Pin.OUT),
    dc=Pin(8, Pin.OUT),
    cs=Pin(9, Pin.OUT),
    rotation=1
)

Pin(13, Pin.OUT).value(1) #backlight on
display.init()

iUp     = Pin(2,  Pin.IN, Pin.PULL_UP)
iDown   = Pin(18, Pin.IN, Pin.PULL_UP)
iLeft   = Pin(16, Pin.IN, Pin.PULL_UP)
iRight  = Pin(20, Pin.IN, Pin.PULL_UP)
iCentre = Pin(3,  Pin.IN, Pin.PULL_UP)
iA      = Pin(15, Pin.IN, Pin.PULL_UP)
iB      = Pin(17, Pin.IN, Pin.PULL_UP)
iX      = Pin(19, Pin.IN, Pin.PULL_UP)
iY      = Pin(21, Pin.IN, Pin.PULL_UP)

BLACK = graphics.RGBto565(0, 0, 0)
WHITE = graphics.RGBto565(255, 255, 255)
GRASS = graphics.RGBto565(111, 191, 79)

bufferArray = bytearray(32 * 32 * 2)

def LoadBiome(path):
    with open(path, "r") as f:
        return [list(line.strip()) for line in f if line.strip()]

def LoadTile(path):
    with open(path, "rb") as f:
        return bytearray(f.read())

def BlitTile(tile, x, y, slow=False):
    display.blit_buffer(tile, x, y, 16, 16)
    if slow:
        sleep(0.01)

def DrawTilemap(tilemap, slow=False):
    tileSize = 16
    for row in range(15):
        for col in range(15):
            if 0 <= row < len(tilemap) and 0 <= col < len(tilemap[0]):
                char = tilemap[row][col]
                tile = tileset.get(char)
                if tile:
                    drawX = col * tileSize
                    drawY = row * tileSize
                    BlitTile(tile, drawX, drawY, slow)

def GetPlayerTile(tilemap, x, y):
    tx, ty = tileutils.GetTileCoords(x, y, 16)
    if 0 <= ty < len(tilemap) and 0 <= tx < len(tilemap[0]):
        return tilemap[ty][tx]
    return None

def GetCoveredTileCoords(x, y, radius):
    left   = (x - radius) // 16
    top    = (y - radius) // 16
    right  = (x + radius - 1) // 16
    bottom = (y + radius - 1) // 16

    return set((tx, ty) for tx in (left, right) for ty in (top, bottom))

def DrawPlayerBuffered(x, y, tilemap):
    buf = memoryview(bufferArray)

    offsetX = x % 16
    offsetY = y % 16

    tileLeft = x // 16
    tileTop  = y // 16

    for dy in range(2):
        for dx in range(2):
            tx = tileLeft + dx
            ty = tileTop + dy
            if 0 <= ty < len(tilemap) and 0 <= tx < len(tilemap[0]):
                tileChar = tilemap[ty][tx]
                tile = preRenderedTiles.get(tileChar)
                if tile:
                    graphics.BlitTileToBuffer(tile, buf, dx * 16, dy * 16)

    with open("assets/other/player.tile", "rb") as f:
        spriteData = f.read()

    graphics.BlitTransparentSprite(spriteData, buf, 32, offsetX, offsetY, 16, 16, WHITE)

    display.blit_buffer(bufferArray, x - offsetX, y - offsetY, 32, 32)

tileset = {}

for filename in os.listdir("assets/tiles"):
    if filename.endswith(".tile"):
        name = filename[:-5] #remove '.tile'
        tileData = LoadTile("assets/tiles/" + filename)
        if name == "grass":
            tileset["."] = tileData
        else:
            tileset[name] = tileData

fieldTilemap = LoadBiome("assets/tilemaps/field.tm")

preRenderedTiles = {}
for char, tile in tileset.items():
    preRenderedTiles[char] = tile

baseLvl = 10
types = ("Fire", "Grass", "Electric", "Water", "Dark")
typeEffect = (
    ("Fire",     "Grass"),
    ("Grass",    "Electric"),
    ("Electric", "Water"),
    ("Water",    "Fire"),

    ("Dark",     "Fire"),
    ("Dark",     "Grass"),
    ("Dark",     "Electric"),
    ("Dark",     "Water")
)

typeColour = {
    "Fire": graphics.HEXto565("DF5F17"),
    "Grass": graphics.HEXto565("4FBF37"),
    "Electric": graphics.HEXto565("F7CF00"),
    "Water": graphics.HEXto565("2F7FEF"),
    "Dark": graphics.HEXto565("370F7F")
}

"""tileChances = { #this is for later when there are multiple biomes
    ".": [0.001, [1, 1, 1, 1]],
    "g": [0.005, [1, 2, 0.5, 1]],
    "G": [0.02, [1, 5, 0.5, 1]],
    "r": [0.05, [0.5, 0.5, 2, 5]],
    "c": [0.001, [2, 0.25, 2, 0.25]],
    "X": [1, [0,0,0,0]]
}"""

tileChances = {
    ".": [0.001, [1, 1, 1, 1]],
    "g": [0.01, [1, 1, 1, 1]],
    "G": [0.025, [1, 1, 1, 1]],
    "r": [0.05, [1, 1, 1, 1]],
    "c": [0.001, [1, 1, 1, 1]],
    "X": [1, [0,0,0,0]]
}

class Picomon:
    def __init__(self, name, desc, pType, hp, moves, level):
        self.name    = name
        self.desc    = desc
        self.type    = pType
        self.level   = level
        self.maxHp   = int(hp * level / baseLvl)
        self.hp      = self.maxHp
        self.moves   = moves
    
    def __repr__(self):
        return (f"{self.name}: Level: {self.level}, Type: {self.type}, HP: {self.hp}, Moves: {len(self.moves)}")
    
    def TakeDamage(self, dmg):
        self.hp -= dmg
        if self.hp < 0:
            self.hp = 0
    
    def LevelUp(self, amount):
        old_level = self.level
        self.level += amount
        self.maxHp = int(self.maxHp * self.level / old_level)

class Move:
    __slots__ = ("name", "power", "element")
    def __init__(self, name, power, element=None):
        self.name     = name
        self.power    = power      # “base damage” at level 10
        self.element  = element    # None = neutral

    def __repr__(self):
        return f"<Move {self.name} {self.power} {self.element or 'neutral'}>"

class PlayerTeam:
    def __init__(self):
        self.teamList = []
        self.activeIndex = 0

    def GetActive(self):
        return self.teamList[self.activeIndex]

    def SwitchTo(self, index):
        if 0 <= index < len(self.teamList):
            self.activeIndex = index

    def AddPicomon(self, newPicomon):
        if len(self.teamList) < 4:
            self.teamList.append(newPicomon)

    def ReplacePicomon(self, newPicomon):
        if Pressed(iA):
            self.teamList[0] = newPicomon
            self.activeIndex = 0
        elif Pressed(iB):
            self.teamList[1] = newPicomon
            self.activeIndex = 1
        elif Pressed(iX):
            self.teamList[2] = newPicomon
            self.activeIndex = 2
        elif Pressed(iY):
            self.teamList[3] = newPicomon
            self.activeIndex = 3

movesRegistry = {
    "Punch":        {"power": 10, "element": None},
    "Tail Whip":    {"power": 10, "element": None},
    "Crush":        {"power": 15, "element": None},
    "Slice":        {"power": 20, "element": None},

    "Burn":         {"power": 15, "element": "Fire"},
    "Flame Kick":   {"power": 20, "element": "Fire"},
    "Explode":      {"power": 20, "element": "Fire"},
    "Inferno":      {"power": 25, "element": "Fire"},

    "Buzz":         {"power": 12, "element": "Electric"},
    "Discharge":    {"power": 20, "element": "Electric"},
    "Electrocute":  {"power": 20, "element": "Electric"},

    "Leaf Slash":   {"power": 20, "element": "Grass"},
    "Poison Bite":  {"power": 30, "element": "Grass"},

    "Whirlpool":    {"power": 15, "element": "Water"},
    "Water Jet":    {"power": 20, "element": "Water"},

    "Wither":       {"power": 12, "element": "Dark"},
    "Death Tap":    {"power": 18, "element": "Dark"}
}

speciesRegistry = {
    "Embash": {
        "desc" : "Powerful flaming boar Picomon",
        "type" : "Fire",
        "hp"   : 80,
        "moves": ["Punch", "Flame Kick"],
    },
    "Cinder": {
        "desc" : "Blazing coal Picomon",
        "type" : "Fire",
        "hp"   : 55,
        "moves": ["Burn", "Inferno"],
    },
    "Hissnake": {
        "desc" : "Venomous snake Picomon",
        "type" : "Grass",
        "hp"   : 50,
        "moves": ["Tail Whip", "Poison Bite"],
    },
    "Segbug": {
        "desc" : "Electric bug Picomon",
        "type" : "Grass",
        "hp"   : 60,
        "moves": ["Buzz", "Leaf Slash"],
    },
    "Bulbomb": {
        "desc" : "Superheated lightbulb Picomon",
        "type" : "Electric",
        "hp"   : 50,
        "moves": ["Explode", "Electrocute"],
    },
    "Dynabird": {
        "desc" : "Generator bird Picomon",
        "type" : "Electric",
        "hp"   : 50,
        "moves": ["Leaf Slash", "Discharge"],
    },
    "Voltray": {
        "desc" : "Electric sting ray Picomon",
        "type" : "Water",
        "hp"   : 60,
        "moves": ["Whirlpool", "Electrocute"],
    },
    "Belugas": {
        "desc" : "Beluga whale Picomon",
        "type" : "Water",
        "hp"   : 80,
        "moves": ["Tail Whip", "Water Jet"],
    },
    "Poulter": {
        "desc" : "Picomon of death and decay",
        "type" : "Dark",
        "hp"   : 100,
        "moves": ["Wither", "Death Tap"],
    },
}

def CalculatePowerRating(speciesName):
    species = speciesRegistry[speciesName]
    type_ = species["type"]
    hp = species["hp"]
    moves = species["moves"]

    movePowers = [(move, movesRegistry[move]["power"], movesRegistry[move]["element"]) for move in moves]
    bestMoveName = max(movePowers, key=lambda x: x[1])[0]
    totalPower = 0
    elements = set()

    for moveName, basePower, element in movePowers:
        power = basePower
        if element is not None:
            power *= 1.25
            elements.add(element)
        if moveName == bestMoveName:
            power *= 1.5
        totalPower += power
    if len(elements) == 2:
        totalPower *= 1.1

    powerRating = totalPower * ((hp + 12.5) / 50)
    return int(round(powerRating, 0))

def LoadPicomonSprites():
    for filename in os.listdir("assets/picomon"):
        if filename.endswith(".tile"):
            name = filename[:-5] #remove '.tile'
            if name in speciesRegistry:
                speciesRegistry[name]["sprite"] = LoadTile("assets/picomon/" + filename)

def DrawText(font, msg, x, y, fg, bg, jx=0, jy=0):
    utilities.DrawText(display, font, msg, x, y, fg, bg, jx, jy)

def MoveTuple(name):
    m = movesRegistry[name]
    return (name, m["power"], m["element"])

def LevelUpChance(playerLevel, enemyLevel):
    diff = enemyLevel - playerLevel
    if diff < -2: 
        return 0.0
    return min(2 ** diff / 25, 1.0)

def AttemptCapture(attacker, defender):
    baseChance = 100
    levelGap = attacker.level - defender.level
    if defender.name == "Poulter": #overwrite the chance, to give the player some hope of catching it
        levelGap = max(attacker.level - defender.level, 2)
    levelBonus = (5 if levelGap > 0 else 10) * levelGap #+5% success chance for every level above them you are, and -10%/lvl if they're higher than you
    hpPenalty = 150 * (defender.hp / defender.maxHp) #-15% success chance for every 10% hp the enemy has
    chance = baseChance + levelBonus - hpPenalty
    return random() * 100 < chance

def NewPicomon(speciesName, level=None):
    data = speciesRegistry[speciesName]
    moveTuples = [MoveTuple(m) for m in data["moves"]]
    if not level:
        level = int(round(utilities.BellCurve(baseLvl, 2, 5, 15), 0))
    return Picomon(
        speciesName,
        data["desc"],
        data["type"],
        data["hp"],
        moveTuples,
        level
    )

def TypeMultiplier(attackingType, defendingType):
    if attackingType is None:
        return 1
    if (attackingType, defendingType) in typeEffect:
        return 3/2
    elif (defendingType, attackingType) in typeEffect:
        return 2/3
    else:
        return 1

def DrawBoxOutline():
    display.rect(2, 198, 236, 40, BLACK)

def ClearInfoUI():
    display.fill_rect(3, 199, 234, 38, WHITE)

def DrawUILabels():
    ClearInfoUI()
    active = playerTeam.GetActive()
    moveA = active.moves[0]
    moveB = active.moves[1]

    colourA = typeColour.get(moveA[2], BLACK)
    colourB = typeColour.get(moveB[2], BLACK)

    DrawText(font8, f"   {moveA[0]}", 8, 201, colourA, WHITE, 0, 0)
    DrawText(font8, f"A:", 8, 201, BLACK, WHITE, 0, 0)
    DrawText(font8, f"   {moveB[0]}", 8, 237, colourB, WHITE, 0, 1)
    DrawText(font8, f"B:", 8, 237, BLACK, WHITE, 0, 1)
    DrawText(font8, "X: Catch", 160, 201, BLACK, WHITE, 0, 0)
    DrawText(font8, "Y: Switch", 160, 237, BLACK, WHITE, 0, 1)

def DrawTeam():
    ClearInfoUI()
    names = []
    colours = []

    for i in range(4):
        if i < len(playerTeam.teamList):
            pico = playerTeam.teamList[i]
            names.append(pico.name)
            colours.append(typeColour.get(pico.type, BLACK))
        else:
            names.append(" --- ")
            colours.append(BLACK)

    DrawText(font8, "A:",  5, 202, BLACK, WHITE, 0, 0)
    DrawText(font8, f"   {names[0]}",  5, 202, colours[0], WHITE, 0, 0)
    DrawText(font8, "B:",  5, 236, BLACK, WHITE, 0, 1)
    DrawText(font8, f"   {names[1]}",  5, 236, colours[1], WHITE, 0, 1)
    DrawText(font8, "X:", 120, 202, BLACK, WHITE, 0, 0)
    DrawText(font8, f"   {names[2]}", 120, 202, colours[2], WHITE, 0, 0)
    DrawText(font8, "Y:", 120, 236, BLACK, WHITE, 0, 1)
    DrawText(font8, f"   {names[3]}", 120, 236, colours[3], WHITE, 0, 1)

def ClearPicoUI(x, y=5):
    DrawText(font8, f" "*15, x, y, BLACK, WHITE)
    DrawText(font8, f" "*15, x, y + 16, BLACK, WHITE)
    DrawText(font8, f" "*15, x, y + 32, BLACK, WHITE)

def DrawPicomonInfo(pico, x, y=5):
    ClearPicoUI(x, y)
    ClearPicoUI(x, y)
    DrawText(font8, f"{pico.name}", x, y, BLACK, WHITE)
    DrawText(font8, f"Lvl {pico.level}", x, y + 16, BLACK, WHITE)
    DrawText(font8, f"{pico.hp}/{pico.maxHp}hp", x, y + 32, BLACK, WHITE)

def DrawPicomon(picomon, x, flip=False, y=75, scale=6):
    path = f"assets/picomon/{picomon.name.lower()}.tile"
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return

    width = height = 16
    expectedLength = width * height * 2

    if len(data) != expectedLength:
        return

    for row in range(height):
        for col in range(width):
            # If flipping, read pixels from the mirrored column
            draw_col = width - 1 - col if flip else col
            i = 2 * (row * width + draw_col)
            color = (data[i] << 8) | data[i + 1]

            sx = x + col * scale
            sy = y + row * scale
            display.fill_rect(sx, sy, scale, scale, color)

def ConvertRGB565ToTileset(data, width, height, name):
    tile_w, tile_h = 16, 16
    tiles_x = width // tile_w
    tiles_y = height // tile_h

    os.makedirs("assets/picomon", exist_ok=True)

    def tile_id(i):
        s = ''
        while True:
            s = chr(97 + (i % 26)) + s
            i //= 26
            if i == 0:
                break
        return s

    tilemap_lines = []
    tile_count = 0

    for ty in range(tiles_y):
        line = []
        for tx in range(tiles_x):
            tile_name = tile_id(tile_count)
            tile_count += 1
            line.append(tile_name)

            tile_data = bytearray()
            for row in range(tile_h):
                for col in range(tile_w):
                    px = tx * tile_w + col
                    py = ty * tile_h + row
                    i = 2 * (py * width + px)
                    tile_data.append(data[i])
                    tile_data.append(data[i+1])

            with open(f"assets/picomon/{tile_name}.tile", "wb") as f:
                f.write(tile_data)

        tilemap_lines.append(" ".join(line))

    with open(f"assets/picomon/{name.lower()}.tm", "w") as f:
        f.write("\n".join(tilemap_lines))

def BlendRGB565Slow(original, flash, weight=0.5): #atomic engine has an optimisation for this, but I prefer the look of this slower version
    # Extract RGB565 channels
    r1 = (original >> 11) & 0x1F
    g1 = (original >> 5)  & 0x3F
    b1 = original & 0x1F

    r2 = (flash >> 11) & 0x1F
    g2 = (flash >> 5)  & 0x3F
    b2 = flash & 0x1F

    # Convert to 8-bit
    r1 = int(r1 * 255 / 31)
    g1 = int(g1 * 255 / 63)
    b1 = int(b1 * 255 / 31)

    r2 = int(r2 * 255 / 31)
    g2 = int(g2 * 255 / 63)
    b2 = int(b2 * 255 / 31)

    # Weighted average
    w = weight
    r = int(r1 * (1 - w) + r2 * w)
    g = int(g1 * (1 - w) + g2 * w)
    b = int(b1 * (1 - w) + b2 * w)

    # Back to RGB565
    return graphics.RGBto565(r, g, b)

def FlashSprite(spriteData, x, y, scale=6, flashColor=WHITE, flip=False):
    width = height = 16
    for row in range(height):
        for col in range(width):
            draw_col = width - 1 - col if flip else col
            i = 2 * (row * width + draw_col)
            color = (spriteData[i] << 8) | spriteData[i + 1]

            if color != WHITE:
                blended = BlendRGB565Slow(color, flashColor, 0.75) #intentionally not using atomic engine here because of visual preference
                sx = x + col * scale
                sy = y + row * scale
                display.fill_rect(sx, sy, scale, scale, blended)

def AnimateAttack(attacker, defender, moveType, playerAttacking, attackerX, defenderX):
    if playerAttacking:
        offset = 12
        flipped = True
    else:
        offset = -12
        flipped = False
    antiFlip = not flipped

    flashColor = typeColour.get(moveType, WHITE)

    display.fill_rect(attackerX, 75, 96, 96, WHITE)
    DrawPicomon(attacker, attackerX + offset, flipped)
    sleep(0.1)

    display.fill_rect(attackerX + offset, 75, 96, 96, WHITE)
    DrawPicomon(attacker, attackerX, flipped)
    #sleep(0.05)

    spritePath = f"assets/picomon/{defender.name.lower()}.tile"
    try:
        with open(spritePath, "rb") as f:
            spriteData = f.read()
    except:
        spriteData = None

    for _ in range(3):
        if spriteData:
            FlashSprite(spriteData, defenderX, 75, 6, flashColor, flip=antiFlip)
        else:
            display.fill_rect(defenderX, 75, 96, 96, flashColor)
        sleep(0.05)
        DrawPicomon(defender, defenderX, antiFlip)
        sleep(0.05)

def CalculateDamage(attacker, defender, move):
    basePower = move[1]
    moveType = move[2]
    levelFactor = attacker.level / baseLvl
    mult = TypeMultiplier(moveType, defender.type)
    randomMult = uniform(0.9,1.111) * uniform(0.9,1.111)
    return int(basePower * levelFactor * mult * randomMult), ("critical" if mult > 1 else "resisted" if mult < 1 else "")

def ChooseSpeciesByType(weights):
    weightedTypes = [(types[i], weights[i]) for i in range(4) if weights[i] > 0]
    totalWeight = sum(weight for _, weight in weightedTypes)
    threshold = uniform(0, totalWeight)
    cumulative = 0

    selectedType = "Dark"
    for typeName, weight in weightedTypes:
        cumulative += weight
        if threshold <= cumulative:
            selectedType = typeName
            break

    candidates = [name for name, data in speciesRegistry.items() if data["type"] == selectedType]
    return choice(candidates)

def WriteToInfoUI(msg):
    ClearInfoUI()
    DrawText(font8, msg, 120, 210, BLACK, WHITE, 0.5, 0)

def ShowFPS(lastFrameStart, fps=False):
    frametime = ticks_us() - lastFrameStart
    if fps:
        text = "{:.0f}fps".format(1000000/frametime)
    else:
        text = str("{:.2f}ms".format(frametime/1000))
    DrawText(font8, text, 236, 2, WHITE, GRASS, 1, 0)

def ShowPowers():
    for species in speciesRegistry.keys(): #just for debug; calculates how strong each picomon is (independent of level)
       print(f"{species}: {CalculatePowerRating(species)}")

def Battle(enemyPicos):
    info1X = 20
    info2X = 140
    pico1X = 15
    pico2X = 135

    playerPico = playerTeam.GetActive()
    enemyIndex = 0
    enemyPico = enemyPicos[enemyIndex]

    display.fill(WHITE)
    display.rect(2, 198, 236, 40, BLACK)
    DrawUILabels()
    DrawPicomonInfo(playerPico, info1X)
    DrawPicomonInfo(enemyPico, info2X)
    DrawPicomon(playerPico, pico1X, True)
    DrawPicomon(enemyPico, pico2X)

    while True:
        moveUsed = False
        caught = False
        fled = False

        while not moveUsed:
            if Pressed(iA):
                move = playerPico.moves[0]
                dmg, eff = CalculateDamage(playerPico, enemyPico, move)
                AnimateAttack(playerPico, enemyPico, move[2], True, pico1X, pico2X)
                enemyPico.TakeDamage(dmg)
                DrawPicomonInfo(enemyPico, info2X)
                WriteToInfoUI(f"{move[0]} was {eff}!" if eff else f"{playerPico.name} used {move[0]}!")
                sleep(2)
                DrawUILabels()
                moveUsed = True

            elif Pressed(iB):
                move = playerPico.moves[1]
                dmg, eff = CalculateDamage(playerPico, enemyPico, move)
                AnimateAttack(playerPico, enemyPico, move[2], True, pico1X, pico2X)
                enemyPico.TakeDamage(dmg)
                DrawPicomonInfo(enemyPico, info2X)
                WriteToInfoUI(f"{move[0]} was {eff}!" if eff else f"{playerPico.name} used {move[0]}!")
                sleep(2)
                DrawUILabels()
                moveUsed = True

            elif Pressed(iX):
                if AttemptCapture(playerPico, enemyPico):
                    WriteToInfoUI(f"Caught the {enemyPico.name}!")
                    sleep(2)
                    WriteToInfoUI("This reduced its level by 1")
                    sleep(2)
                    DrawUILabels()
                    caught = True
                    enemyPico.hp = 0
                    enemyPico.level -= 1

                    if len(playerTeam.teamList) < 4:
                        playerTeam.AddPicomon(enemyPico)
                    else:
                        WriteToInfoUI("Who do you replace?")
                        sleep(2)
                        DrawTeam()
                        buttons = (iA, iB, iX, iY)
                        while any(Pressed(p) for p in buttons): sleep(0.001)
                        while True:
                            pressed = [Pressed(p) for p in buttons]
                            if any(pressed):
                                idx = pressed.index(True)
                                break
                        old = playerTeam.teamList[idx]
                        playerTeam.teamList[idx] = enemyPico
                        WriteToInfoUI(f"{old.name} replaced with {enemyPico.name}")
                        sleep(2)
                        DrawUILabels()

                    sleep(1)
                    moveUsed = True
                else:
                    WriteToInfoUI("Catch failed!")
                    sleep(2)
                    DrawUILabels()
                    moveUsed = True

            elif Pressed(iY):
                WriteToInfoUI("Who do you swap with?")
                sleep(2)
                DrawTeam()
                buttons = (iA, iB, iX, iY)
                while any(Pressed(p) for p in buttons): sleep(0.001)

                while True:
                    pressed = [Pressed(p) for p in buttons]
                    if any(pressed):
                        idx = pressed.index(True)
                        if idx < len(playerTeam.teamList):
                            targetPico = playerTeam.teamList[idx]
                            if targetPico.hp > 0:
                                playerTeam.SwitchTo(idx)
                                playerPico = playerTeam.GetActive()
                                DrawPicomonInfo(playerPico, info1X)
                                DrawPicomon(playerPico, pico1X, True)
                            else:
                                WriteToInfoUI("That Picomon has fainted!")
                                sleep(2)
                                DrawTeam()
                        break

                DrawUILabels()
                while any(Pressed(p) for p in buttons): sleep(0.001)

            elif Pressed(iCentre):
                if randint(1,3) == 1:
                    WriteToInfoUI("You flee successfully")
                    sleep(2)
                    fled = True
                else:
                    WriteToInfoUI("Flee failed!")
                    sleep(2)
                    DrawUILabels()
                moveUsed = True

        if enemyPico.hp <= 0:
            if caught:
                pass
            else:
                WriteToInfoUI(f"{enemyPico.name} fainted!")
                sleep(2)
                if random() < LevelUpChance(playerPico.level, enemyPico.level):
                    playerPico.LevelUp(1)
                    WriteToInfoUI(f"{playerPico.name} levelled up!")
                    sleep(2)

            enemyIndex += 1
            if enemyIndex >= len(enemyPicos):
                WriteToInfoUI("You win the battle!")
                sleep(2)
                break

            enemyPico = enemyPicos[enemyIndex]
            DrawPicomonInfo(enemyPico, info2X)
            DrawPicomon(enemyPico, pico2X)
            WriteToInfoUI(f"{enemyPico.name} steps up!")
            sleep(2)
            DrawUILabels()
            continue

        elif fled:
            break

        sleep(0.5)
        enemyMove = choice(enemyPico.moves)
        dmg, eff = CalculateDamage(enemyPico, playerPico, enemyMove)
        AnimateAttack(enemyPico, playerPico, enemyMove[2], False, pico2X, pico1X)
        playerPico.TakeDamage(dmg)
        DrawPicomonInfo(playerPico, info1X)
        WriteToInfoUI(f"{enemyMove[0]} was {eff}!" if eff else f"{enemyPico.name} used {enemyMove[0]}!")
        sleep(2)
        DrawUILabels()

        if playerPico.hp <= 0:
            WriteToInfoUI(f"{playerPico.name} fainted!")
            sleep(2)
            WriteToInfoUI(f"{playerPico.name} lost a level!")
            sleep(2)
            playerPico.LevelUp(-1)

            aliveFound = False
            for i, pico in enumerate(playerTeam.teamList):
                if pico.hp > 0:
                    playerTeam.SwitchTo(i)
                    playerPico = playerTeam.GetActive()
                    aliveFound = True
                    DrawUILabels()
                    DrawPicomonInfo(playerPico, info1X)
                    DrawPicomon(playerPico, pico1X, True)
                    break

            if not aliveFound:
                WriteToInfoUI("You lose the battle!")
                sleep(2)
                break

    for pico in playerTeam.teamList:
        pico.hp = pico.maxHp

display.fill(BLACK)
DrawText(font8, version, 5, 5, WHITE, BLACK, 0, 0)
DrawText(font16, "Picomon", 120, 110, WHITE, BLACK, 0.5, 0.5)
DrawText(font8, "Press A to Start", 120, 148, WHITE, BLACK, 0.5, 0.5)
DrawText(font8, "by Henry Gurney", 120, 235, WHITE, BLACK, 0.5, 1)
playerTeam = PlayerTeam()

debug = False ###
if debug:
    ShowPowers()

while True: #titlescreen
    level = 10 if Pressed(iCentre) else 8
    if Pressed(iA):
        playerTeam.AddPicomon(NewPicomon("Embash", level))
        break

    elif Pressed(iB):
        playerTeam.AddPicomon(NewPicomon("Hissnake", level))
        break

    elif Pressed(iX):
        playerTeam.AddPicomon(NewPicomon("Bulbomb", level))
        break

    elif Pressed(iY):
        playerTeam.AddPicomon(NewPicomon("Belugas", level))
        break

    sleep(0.001)

playerX = 88
playerY = 216
size = 8 #player radius
speed = 1 #player speed

currentBiome = fieldTilemap
LoadPicomonSprites()
DrawTilemap(currentBiome)
DrawPlayerBuffered(playerX, playerY, currentBiome)
gameTime = ticks_us()
targetFps = 60

while True:
    frameStart = ticks_us()

    moved = False; battled = False         
    oldX, oldY = playerX, playerY
    if Pressed(iUp):    playerY -= speed; moved = True
    if Pressed(iDown):  playerY += speed; moved = True
    if Pressed(iLeft):  playerX -= speed; moved = True
    if Pressed(iRight): playerX += speed; moved = True
    playerX = min(max(playerX, 0), 240)
    playerY = min(max(playerY, 0), 240)

    if moved:
        DrawPlayerBuffered(playerX, playerY, currentBiome)

    if any(Pressed(btn) for btn in (iUp, iDown, iLeft, iRight)):
        tileType = GetPlayerTile(currentBiome, playerX, playerY)
        if tileType in tileChances and random() <= tileChances[tileType][0]:
            battled = True
            if tileType == "X":
                Battle([NewPicomon("Poulter", 20)])
            else:
                enemyCount = 1
                while enemyCount < 4 and randint(0, 1):
                    enemyCount += 1
                weights = tileChances[tileType][1]
                enemies = [NewPicomon(ChooseSpeciesByType(weights)) for _ in range(enemyCount)]
                Battle(enemies)
            DrawTilemap(currentBiome, True)
            DrawPlayerBuffered(playerX, playerY, currentBiome)

    if debug:
        if battled:
            frameStart = ticks_us()
        ShowFPS(frameStart, False)
    sleep(max(0, ((1000000/targetFps) - (ticks_us() - frameStart)) / 1000000))

#TODO
#add a thing so if you fail to flee 3x in a row it just lets you
#add other biomes and minibosses; maybe add le poisson steve as the water boss with only fire and electric moves
#obviously more picomon is always a good thing too but they take ages, maybe ask anna for help after munich
