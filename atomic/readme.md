# Atomic Engine Documentation

Atomic is a lightweight MicroPython engine for fast 2D graphics on the Raspberry Pi Pico 2.

It uses MicroPython Viper where possible, and Native where not, for optimisation.

---

# Graphics Module

`from atomic import graphics`

High-performance Viper-optimised functions for 2D graphics.

---

### SetPixel

Write a 16-bit RGB565 pixel into a linear framebuffer at (x, y).  
The buffer must be a bytearray or memoryview of RGB565 pixels.

**SetPixel(buf, x, y, color, width)**  
- `buf`: framebuffer (bytearray or memoryview)  
- `x`, `y`: pixel coordinates  
- `color`: 16-bit RGB565 colour  
- `width`: buffer width in pixels

**Example**  
`SetPixel(buf, 10, 12, 0xF800, 240)`

---

### BlitTileToBuffer

Copy a 16×16 RGB565 tile into a 32×32 destination buffer at (dstX, dstY).  
The destination buffer must be 32×32 RGB565 pixels (2048 bytes).

**BlitTileToBuffer(tile, buf, dstX, dstY)**  
- `tile`: 512-byte RGB565 tile (16×16)  
- `buf`: destination buffer (2048-byte 32×32 area)  
- `dstX`, `dstY`: offset in the buffer (usually 0 or 16)

**Example**  
`BlitTileToBuffer(tile, buffer, 0, 0)`

---

### BlendRGB565

Blend two 16-bit RGB565 colours using an 8-bit weight (0–255).  
A higher weight yields more of the second colour.

**BlendRGB565(colour1, colour2, weight)**  
- `colour1`: RGB565 colour A  
- `colour2`: RGB565 colour B  
- `weight`: blend weight (0 = all A, 255 = all B)

**Example**  
`BlendRGB565(0xF800, 0x07E0, 128)`

---

### BlitTransparentSprite

Blit a variable-sized RGB565 sprite with a transparent colour onto a linear framebuffer.  
Useful for drawing sprites without overwriting background tiles.

**BlitTransparentSprite(tile, buf, screenWidth, x, y, tileWidth, tileHeight, transparent)**  
- `tile`: sprite data (tileWidth × tileHeight × 2 bytes)  
- `buf`: framebuffer (e.g. screen or off-screen buffer)  
- `screenWidth`: width of the framebuffer in pixels  
- `x`, `y`: target position to draw the sprite  
- `tileWidth`, `tileHeight`: dimensions of the sprite  
- `transparent`: RGB565 colour to treat as transparent

**Example**  
`BlitTransparentSprite(sprite, framebuffer, 240, 64, 32, 16, 16, WHITE)`

---

### RGBto565

Convert 8-bit per channel RGB values to a single 16-bit RGB565 value.

**RGBto565(r, g, b)**  
- `r`, `g`, `b`: 8-bit (0–255) colour channels  
- **Returns**: 16-bit RGB565 colour

**Example**  
`RGBto565(255, 0, 0)`

---

### HEXto565

Convert a hex string (e.g. `"#FFAA33"`) into a 16-bit RGB565 colour.  
Must be a 6-character hex code with or without a leading `#`.

**HEXto565(hexStr)**  
- `hexStr`: a string like `"#FFAABB"` or `"FFAABB"`  
- **Returns**: 16-bit RGB565 colour

**Example**  
`HEXto565("#00FF00")`

---

# Tile Utilities Module

`from atomic import tileutils`

Efficient tools for working with tilemaps.

---

### GetTileCoords

Convert screen (pixel) coordinates into tilemap (grid) coordinates.

**GetTileCoords(x, y, tileSize)**  
- `x`, `y`: screen position in pixels  
- `tileSize`: tile width/height (e.g. 16)  
- **Returns**: `(tileX, tileY)` tuple

**Example**  
`tileX, tileY = tileutils.GetTileCoords(playerX, playerY, 16)`

---

### GetTileCoordsPacked (internal)

Same as `GetTileCoords`, but returns a packed 32-bit int instead of a tuple.  
Mainly for internal use or performance-critical logic.

**GetTileCoordsPacked(x, y, tileSize)**  
- **Returns**: packed int `(tileY << 16) | tileX`

---

### GetCoveredTileCoords

Return the bounding tile coordinates that cover a rectangular region of a given radius.  
This is useful for visibility, collision, or range checks.

**GetCoveredTileCoords(x, y, radius)**  
- `x`, `y`: centre in pixels  
- `radius`: radius in pixels  
- **Returns**: `(top, bottom, left, right)` tile indices

**Example**  
`top, bottom, left, right = tileutils.GetCoveredTileCoords(playerX, playerY, 24)`

---

### GetCoveredTileCoordsPacked (internal)

Same as `GetCoveredTileCoords`, but returns a packed 32-bit int.  
Mainly for internal use or performance-critical logic.

**GetCoveredTileCoordsPacked(x, y, radius)**  
- **Returns**: packed int `(top << 24) | (bottom << 16) | (left << 8) | right`

---

# Utilities Module

`from atomic import utilities`

Efficient helper functions for core tasks.

### DrawText

Render aligned text to the screen using a bitmap font.  
Supports optional justification to centre or align text.

**DrawText(display, font, msg, x, y, fg, bg, jx=0, jy=0)**  
- `display`: the target display object (e.g. `display`)  
- `font`: a bitmap font object (must have `.WIDTH` and `.HEIGHT`)  
- `msg`: string to render  
- `x`, `y`: position in pixels  
- `fg`, `bg`: foreground and background colours (RGB565)  
- `jx`, `jy`: justification (0 = left/top, 0.5 = centre, 1 = right/bottom)

**Example**  
`DrawText(display, font8, "Hello!", 120, 100, WHITE, BLACK, 0.5, 0.5)`

---

### Pressed

Check if a button is currently being pressed (i.e. its GPIO pin is low).  
This is useful for reading physical button states with internal pull-ups.

**Pressed(pin)**  
- `pin`: a `machine.Pin` object (configured as `Pin.IN` with `Pin.PULL_UP`)  
- **Returns**: `True` if the button is pressed, `False` otherwise

**Example**  
`iA = Pressed(iA)`

---

### BellCurve

Generate a random float using a normal distribution with optional clamping.

**BellCurve(mean, sigma=1.0, lo=None, hi=None)**  
- `mean`: Centre of the distribution  
- `sigma`: Spread (standard deviation)  
- `lo`, `hi`: Optional min/max bounds  
- **Returns**: float value sampled from a bell curve

**Example**  
`damage = utilities.BellCurve(10, 2, 5, 15)`

---

# Licence

Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 (CC BY-NC-ND 4.0)

- Free for personal and educational use
- No commercial use
- No modification or redistribution without permission

(c) 2025 Henry Gurney
