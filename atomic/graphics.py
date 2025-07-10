import micropython

@micropython.viper
def BlitTileToBuffer(tile: ptr16, buf: ptr16,
                     dstX: int, dstY: int):
    dstBase = (dstY * 32 + dstX)
    for row in range(16):
        srcRow = row * 16
        dstRow = dstBase + row * 32
        for col in range(16):
            buf[dstRow + col] = tile[srcRow + col]

@micropython.viper
def SetPixel(buf: ptr8, x: int, y: int, color: int, width: int = 32):
    i = (y * width + x) << 1
    buf[i] = color >> 8
    buf[i + 1] = color & 0xFF

@micropython.viper
def BlendRGB565(a: int, b: int, w8: int) -> int:
    inv = 255 - w8
    r = (((a >> 11) & 0x1F) * inv + ((b >> 11) & 0x1F) * w8) >> 8
    g = (((a >>  5) & 0x3F) * inv + ((b >>  5) & 0x3F) * w8) >> 8
    b_ = (((a      ) & 0x1F) * inv + ((b      ) & 0x1F) * w8) >> 8
    return (r << 11) | (g << 5) | b_

@micropython.viper
def BlitTransparentSprite(tile: ptr16, buf: ptr16,
                          screenW: int, x: int, y: int,
                          w: int, h: int, trans: int):
    for row in range(h):
        srcRow = row * w
        dstRow = (y + row) * screenW + x
        for col in range(w):
            c = tile[srcRow + col]
            if c != trans:
                buf[dstRow + col] = c

@micropython.viper
def RGBto565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

@micropython.native
def HEXto565(h: str) -> int:
    if h[0] == '#':
        h = h[1:]
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return RGBto565(r, g, b)
