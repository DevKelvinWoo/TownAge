"""Generate seamless, stylized streetscape textures for the approved TownAge art."""

import math
import random
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'Saved/MainVillage/Streetscape/Textures'
SIZE = 512


def png(path, size, pixels):
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))

    stride = size * 3
    rows = b''.join(b'\x00' + bytes(pixels[y:y + stride]) for y in range(0, len(pixels), stride))
    header = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
                     + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def pixel(value):
    return max(0, min(255, round(value)))


def pavers(name, block_height, seed):
    rng = random.Random(seed)
    width = 128
    palette = [(220, 199, 172), (213, 195, 174), (224, 205, 184),
               (208, 195, 179), (220, 201, 183), (228, 208, 184)]
    rows = SIZE // block_height
    tiles = [[rng.choice(palette) for _ in range(SIZE // width)] for _ in range(rows)]
    mortar = (192, 174, 155)
    heights = []
    color = bytearray()
    for y in range(SIZE):
        row = y // block_height
        shift = width // 2 if row % 2 and name == 'Sidewalk' else 0
        for x in range(SIZE):
            u = (x + shift) % SIZE
            tile = tiles[row][u // width]
            dx = abs((u % width) + .5 - width / 2) - (width / 2 - 4.5)
            dy = abs((y % block_height) + .5 - block_height / 2) - (block_height / 2 - 4.5)
            distance = math.hypot(max(dx, 0), max(dy, 0)) + min(max(dx, dy), 0)
            relief = max(0., min(1., (3.2 - distance) / 4.))
            relief = relief * relief * (3. - 2. * relief)
            grain = rng.uniform(-1.8, 1.8)
            mottling = 1.5 * math.sin(x * math.tau / SIZE * 7) * math.cos(y * math.tau / SIZE * 5)
            color.extend(pixel(a + (b - a) * relief + grain + mottling) for a, b in zip(mortar, tile))
            heights.append(relief)
    normal = bytearray()
    for y in range(SIZE):
        for x in range(SIZE):
            dx = .60 * (heights[y * SIZE + (x + 1) % SIZE] - heights[y * SIZE + (x - 1) % SIZE])
            dy = .60 * (heights[((y + 1) % SIZE) * SIZE + x] - heights[((y - 1) % SIZE) * SIZE + x])
            length = math.sqrt(dx * dx + dy * dy + 1.)
            normal.extend(pixel((component / length + 1.) * 127.5) for component in (-dx, -dy, 1.))
    png(OUT / f'T_{name}_BaseColor.png', SIZE, color)
    png(OUT / f'T_{name}_Normal.png', SIZE, normal)


def asphalt():
    size = 256
    rng = random.Random(381)
    color = bytearray()
    for y in range(size):
        v = y * math.tau / size
        for x in range(size):
            u = x * math.tau / size
            variation = (.65 * math.sin(3 * u + 2 * v) + .5 * math.cos(6 * u - 5 * v)
                         + rng.uniform(-2.7, 2.7))
            color.extend(pixel(base + variation) for base in (143, 138, 136))
    png(OUT / 'T_Asphalt_BaseColor.png', size, color)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    pavers('Sidewalk', 64, 316)
    pavers('Plaza', 128, 864)
    asphalt()
