import array
import math
import random
import sys
import pygame
from pygame._sdl2.video import Window, Renderer, Texture

# Настройки теста (можешь смело ставить COUNT = 1000 или 2000)
WIDTH, HEIGHT = 1800,900
COUNT = 100000
SPEED_BUBBLE = 100000  # Скорость для пузырька (ему нужно много шагов)
SPEED_MERGE = 5000  # Скорость для слияния (он слишком быстрый!)

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# vsync=False позволяет увидеть реальный максимальный FPS видеокарты без ограничения в 60 Гц
window = Window("GPU Сортировка: [1] Bubble Sort | [2] Merge Sort | [Пробел] Заново", size=(WIDTH, HEIGHT))
renderer = Renderer(window, accelerated=True, vsync=False)

clock = pygame.time.Clock()
font = pygame.font.SysFont("monospace", 20, bold=True)


def make_beep(freq, duration=0.02):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    buf = array.array("h")
    for s in range(n_samples):
        t = float(s) / sample_rate
        fade = 1.0 - (s / n_samples)
        val = int(math.sin(2.0 * math.pi * freq * t) * 2500 * fade)
        buf.append(val)
    return pygame.mixer.Sound(buffer=buf)


sounds = [make_beep(200 + (i / COUNT) * 800) for i in range(COUNT + 1)]

# Кэш цветов
c1 = pygame.Color(0, 255, 220)
c2 = pygame.Color(0, 255, 60)
colors_cache = [tuple(c1.lerp(c2, h / COUNT)) for h in range(COUNT + 1)]

sort = list(range(1, COUNT + 1))
random.shuffle(sort)
inGap = WIDTH / COUNT

comparisons = 0
writes = 0
mode = "MERGE"  # По умолчанию запускаем сразу Merge Sort для эффекта!


def bubble_sort_gen(arr):
    global comparisons, writes
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            comparisons += 1
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                writes += 2
                swapped = True
                yield j + 1
        if not swapped:
            break
    yield -1


def merge_sort_gen(arr, start=0, end=None):
    """Генератор сортировки слиянием (Merge Sort) прямо поверх основного массива."""
    global comparisons, writes
    if end is None:
        end = len(arr)
    if end - start <= 1:
        return

    mid = (start + end) // 2
    yield from merge_sort_gen(arr, start, mid)
    yield from merge_sort_gen(arr, mid, end)

    # Сливаем две отсортированные половины
    left = arr[start:mid]
    right = arr[mid:end]
    i = j = 0
    k = start

    while i < len(left) and j < len(right):
        comparisons += 1
        if left[i] <= right[j]:
            arr[k] = left[i]
            i += 1
        else:
            arr[k] = right[j]
            j += 1
        writes += 1
        yield k
        k += 1

    while i < len(left):
        arr[k] = left[i]
        writes += 1
        yield k
        i += 1
        k += 1

    while j < len(right):
        arr[k] = right[j]
        writes += 1
        yield k
        j += 1
        k += 1

    if start == 0 and end == len(arr):
        yield -1


def reset(new_mode=None):
    global sort, comparisons, writes, sorter, active_idx, mode
    if new_mode:
        mode = new_mode
    random.shuffle(sort)
    comparisons = 0
    writes = 0
    active_idx = -1
    if mode == "BUBBLE":
        sorter = bubble_sort_gen(sort)
    else:
        sorter = merge_sort_gen(sort)


reset("MERGE")


def drawColumnsGPU(arr, current_idx):
    """Пакетная отрисовка на GPU."""
    col_w = max(1, math.ceil(inGap))

    for idx, h in enumerate(arr):
        x = int(idx * inGap)
        col_h = int(h * HEIGHT / COUNT)
        y = HEIGHT - col_h

        if idx == current_idx:
            renderer.draw_color = (255, 50, 50, 255)
        else:
            renderer.draw_color = colors_cache[h]

        renderer.fill_rect((x, y, col_w, col_h))


def drawStatsGPU(fps):
    algo_name = "Merge Sort" if mode == "MERGE" else "Bubble Sort"
    text = f"FPS: {int(fps)} | {algo_name} | Сравнений: {comparisons} | Записей: {writes}"
    text_surface = font.render(text, True, (255, 255, 255))
    text_texture = Texture.from_surface(renderer, text_surface)
    text_texture.draw(dstrect=(20, 20, text_surface.get_width(), text_surface.get_height()))


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                reset()
            elif event.key == pygame.K_1:
                reset("BUBBLE")
            elif event.key == pygame.K_2:
                reset("MERGE")

    current_speed = SPEED_MERGE if mode == "MERGE" else SPEED_BUBBLE

    for _ in range(current_speed):
        try:
            active_idx = next(sorter)
            if active_idx == -1:
                break
        except StopIteration:
            active_idx = -1
            break

    if active_idx != -1:
        sounds[sort[active_idx]].play()

    renderer.draw_color = (25, 25, 28, 255)
    renderer.clear()

    drawColumnsGPU(sort, active_idx)
    drawStatsGPU(clock.get_fps())

    renderer.present()
    clock.tick(0)

pygame.quit()
sys.exit()
