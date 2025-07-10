import micropython

@micropython.viper
def GetTileCoordsPacked(x: int, y: int, tileSize: int) -> int:
    tx = x // tileSize
    ty = y // tileSize
    return (ty << 16) | tx

@micropython.native
def GetTileCoords(x: int, y: int, tileSize: int) -> tuple:
    packed = GetTileCoordsPacked(x, y, tileSize)
    tileY = packed >> 16
    tileX = packed & 0xFFFF
    return tileX, tileY

@micropython.viper
def GetCoveredTileCoordsPacked(x: int, y: int, radius: int) -> int:
    left   = (x - radius) // 16
    top    = (y - radius) // 16
    right  = (x + radius - 1) // 16
    bottom = (y + radius - 1) // 16
    return (top << 24) | (bottom << 16) | (left << 8) | right

@micropython.native
def GetCoveredTileCoords(packed: int):
    top    =  packed >> 24
    bottom = (packed >> 16) & 0xFF
    left   = (packed >> 8)  & 0xFF
    right  =  packed & 0xFF
    return top, bottom, left, right
