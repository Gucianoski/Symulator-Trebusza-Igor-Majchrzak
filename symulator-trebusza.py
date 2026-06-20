import math
import pygame


# Rozmiar okna i podstawowe stale symulacji.
WIDTH, HEIGHT = 1280, 760
FPS = 60
DT = 1 / FPS
GRAVITY = 9.81

# Punkt obrotu ramienia trebusza w ukladzie swiata, w metrach.
PIVOT_X = 0.0
PIVOT_Y = 5.0
BALL_RADIUS = 0.18
START_THETA = math.radians(205)
COUNTER_SIZE = 0.62

# Prawa czesc okna jest panelem sterowania, lewa czesc pokazuje symulacje.
PANEL_W = 330
WORLD_W = WIDTH - PANEL_W

# Minimalny kadr startowy. Kamera moze go pozniej rozszerzac,
# zeby pokazac caly lot kuli i wszystkie ruchome elementy.
BASE_VIEW = {
    "min_x": -8.0,
    "max_x": 8.0,
    "min_y": -0.5,
    "max_y": 9.0,
}

# Aktualne parametry fizyczne trebusza. Suwaki zmieniaja te wartosci.
PARAMS = {
    "long_arm": 5.0,
    "short_arm": 1.5,
    "sling": 2.25,
    "ball_mass": 12.0,
    "counter_mass": 260.0,
    "counter_hang": 0.9,
    "arm_mass": 45.0,
    "release_min_angle": 24.0,
    "release_max_angle": 52.0,
    "release_min_speed": 8.0,
}

# Definicje suwakow: klucz parametru, etykieta, minimum, maksimum i jednostka.
SLIDERS = [
    ("long_arm", "Dlugie ramie", 3.0, 8.0, "m"),
    ("short_arm", "Krotkie ramie", 0.8, 3.0, "m"),
    ("sling", "Dlugosc procy", 0.8, 4.0, "m"),
    ("ball_mass", "Masa kuli", 2.0, 40.0, "kg"),
    ("counter_mass", "Masa przeciwwagi", 60.0, 500.0, "kg"),
    ("counter_hang", "Zawiesie przeciwwagi", 0.35, 2.0, "m"),
    ("arm_mass", "Masa ramienia", 10.0, 120.0, "kg"),
    ("release_min_angle", "Min. kat zwolnienia", 5.0, 45.0, "deg"),
    ("release_max_angle", "Max. kat zwolnienia", 30.0, 75.0, "deg"),
    ("release_min_speed", "Min. predkosc zwolnienia", 2.0, 20.0, "m/s"),
]


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Trebusz z proca - parametry i dystans")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 18)
small_font = pygame.font.SysFont("Arial", 15)
title_font = pygame.font.SysFont("Arial", 22, bold=True)

camera = BASE_VIEW.copy()
active_slider = None


# Proste funkcje pomocnicze uzywane przez kamere i suwaki.
def lerp(a, b, t):
    return a + (b - a) * t


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def long_arm():
    return PARAMS["long_arm"]


def short_arm():
    return PARAMS["short_arm"]


def sling_length():
    return PARAMS["sling"]


def counter_hang():
    return PARAMS["counter_hang"]


# Polozenie konca dlugiego ramienia, do ktorego przyczepiona jest proca.
def arm_long_tip(theta):
    return (
        PIVOT_X + long_arm() * math.cos(theta),
        PIVOT_Y + long_arm() * math.sin(theta),
    )


# Polozenie konca krotkiego ramienia, do ktorego podwieszona jest przeciwwaga.
def arm_short_tip(theta):
    return (
        PIVOT_X + short_arm() * math.cos(theta + math.pi),
        PIVOT_Y + short_arm() * math.sin(theta + math.pi),
    )


# Predkosc punktu zaczepienia przeciwwagi. Jest potrzebna,
# bo przeciwwaga wisi na ruchomym punkcie i reaguje na jego przyspieszenie.
def arm_short_tip_velocity(theta, omega):
    # Koniec krotkiego ramienia ma polozenie:
    # x = PIVOT_X + r*cos(theta + pi), y = PIVOT_Y + r*sin(theta + pi)
    # Po zrozniczkowaniu po czasie dostajemy:
    # vx = omega*r*sin(theta), vy = -omega*r*cos(theta).
    return (
        omega * short_arm() * math.sin(theta),
        -omega * short_arm() * math.cos(theta),
    )


# Polozenie srodka przeciwwagi jako wahadla podwieszonego do krotkiego ramienia.
def counterweight_center(theta, counter_angle):
    hook_x, hook_y = arm_short_tip(theta)
    # counter_angle jest liczony od pionu w dol.
    # Dla wahadla o dlugosci L:
    # x = x_haka + L*sin(phi)
    # y = y_haka - L*cos(phi)
    return (
        hook_x + counter_hang() * math.sin(counter_angle),
        hook_y - counter_hang() * math.cos(counter_angle),
    )


# Predkosc konca dlugiego ramienia. Z niej proca "dziedziczy" ruch.
def arm_long_tip_velocity(theta, omega):
    # Dla punktu na ramieniu:
    # x = r*cos(theta), y = r*sin(theta)
    # vx = dx/dt = -omega*r*sin(theta)
    # vy = dy/dt =  omega*r*cos(theta)
    return (
        -omega * long_arm() * math.sin(theta),
        omega * long_arm() * math.cos(theta),
    )


# Przyblizony naciag linki przeciwwagi. Sila z linki dziala na hak
# i wytwarza moment obrotowy na ramieniu trebusza.
def counter_force_on_hook(state, hook_ax=0.0, hook_ay=0.0):
    angle = state["counter_angle"]
    angle_v = state["counter_omega"]
    mass = PARAMS["counter_mass"]

    # Wektor jednostkowy od haka do przeciwwagi:
    # r = [sin(phi), -cos(phi)].
    rx = math.sin(angle)
    ry = -math.cos(angle)

    # Przyblizamy naciag linki z rownania radialnego wahadla:
    # T/m + a_haka_radial + g_radial = L*omega_phi^2
    # Stad: T = m * (L*omega_phi^2 - a_haka_radial - g_radial).
    # W kodzie (hook_ay + GRAVITY) oznacza pionowe przyspieszenie efektywne.
    # max(0, ...) pilnuje, zeby linka nie "pchala" przeciwwagi.
    radial_acc = hook_ax * rx + (hook_ay + GRAVITY) * ry
    tension = mass * max(0.0, counter_hang() * angle_v**2 - radial_acc)

    # Sila dzialajaca na hak ma kierunek linki.
    return tension * rx, tension * ry


# Moment bezwladnosci ukladu wzgledem osi obrotu.
# Po wypuszczeniu kuli jej masa nie obciaza juz ramienia.
def moment_of_inertia(attached_ball=True):
    arm_total = long_arm() + short_arm()
    # Ramie traktujemy jak jednorodny pret:
    # I_pret = (1/12) * m * L^2.
    # To uproszczenie, bo rzeczywista os nie musi przechodzic przez srodek preta.
    arm_i = (1 / 12) * PARAMS["arm_mass"] * arm_total**2

    # Kula przed zwolnieniem jest przyblizona jako masa punktowa na odleglosci
    # dlugie_ramie + dlugosc_procy od osi:
    # I_punkt = m * r^2.
    ball_i = PARAMS["ball_mass"] * (long_arm() + sling_length()) ** 2 if attached_ball else 0.0
    return arm_i + ball_i


# Przyspieszenie katowe ramienia: suma momentu od kuli, naciagu przeciwwagi
# i niewielkiego tlumienia numerycznego.
def angular_acceleration(state, attached_ball=True, hook_ax=0.0, hook_ay=0.0):
    theta = state["theta"]

    # Moment sily od kuli liczony jest przez ramie poziome x:
    # tau = r x F = x*Fy - y*Fx.
    # Dla grawitacji F = [0, -m*g], wiec tau = -m*g*x.
    ball_x = (long_arm() + sling_length()) * math.cos(theta) if attached_ball else 0.0

    # Punkt zaczepienia przeciwwagi wzgledem osi obrotu.
    hook_x = short_arm() * math.cos(theta + math.pi)
    hook_y = short_arm() * math.sin(theta + math.pi)
    force_x, force_y = counter_force_on_hook(state, hook_ax, hook_ay)

    # Moment sily od linki przeciwwagi:
    # tau = r_x*F_y - r_y*F_x.
    tau_counter = hook_x * force_y - hook_y * force_x
    tau_ball = -PARAMS["ball_mass"] * GRAVITY * ball_x if attached_ball else 0.0

    # Proste tlumienie lepkie: tau_tlumienia = -c*omega.
    # Stabilizuje symulacje i udaje straty energii w osi oraz linach.
    damping = -1.6 * state["omega"]

    # Rownanie ruchu obrotowego:
    # suma momentow = I * alpha, wiec alpha = tau / I.
    return (tau_counter + tau_ball + damping) / moment_of_inertia(attached_ball)


# Przywraca symulacje do stanu poczatkowego przy aktualnych parametrach.
def reset():
    theta = START_THETA
    tip = arm_long_tip(theta)
    hook_vx, hook_vy = arm_short_tip_velocity(theta, 0.0)
    return {
        "theta": theta,
        "omega": 0.0,
        "counter_angle": 0.0,
        "counter_omega": 0.0,
        "last_hook_vx": hook_vx,
        "last_hook_vy": hook_vy,
        "ball_x": tip[0],
        "ball_y": tip[1] - sling_length(),
        "ball_vx": 0.0,
        "ball_vy": 0.0,
        "released": False,
        "time": 0.0,
        "trajectory": [],
        "predicted_path": [],
        "landed": False,
        "release_x": None,
        "landing_x": None,
        "distance": None,
        "release_vx": None,
        "release_vy": None,
        "release_speed": None,
        "impact_speed": None,
    }


# Po zwolnieniu kuli wyliczamy przewidywany tor balistyczny az do ziemi.
# Kamera uzywa tej listy, aby od razu pokazac caly lot.
def predict_ballistic_path(x, y, vx, vy):
    path = []
    px, py = x, y
    pvx, pvy = vx, vy

    for _ in range(3000):
        path.append((px, py))
        if py <= BALL_RADIUS and pvy <= 0:
            break

        # Lot balistyczny bez oporu powietrza:
        # vy(t + dt) = vy(t) - g*dt
        # x(t + dt) = x(t) + vx*dt
        # y(t + dt) = y(t) + vy*dt
        pvy -= GRAVITY * DT
        px += pvx * DT
        py += pvy * DT

        if py < BALL_RADIUS:
            py = BALL_RADIUS
            path.append((px, py))
            break

    return path


# Dopasowanie kamery do trebusza, przeciwwagi, aktualnej trajektorii
# i przewidywanego lotu. Kadr zachowuje proporcje, wiec obraz sie nie rozciaga.
def update_camera(state):
    global camera
    counter_x, counter_y = counterweight_center(state["theta"], state["counter_angle"])

    xs = [
        BASE_VIEW["min_x"],
        BASE_VIEW["max_x"],
        PIVOT_X - long_arm() - sling_length(),
        PIVOT_X + short_arm() + 1.0,
        state["ball_x"],
        counter_x - COUNTER_SIZE,
        counter_x + COUNTER_SIZE,
    ]
    ys = [
        BASE_VIEW["min_y"],
        BASE_VIEW["max_y"],
        0.0,
        PIVOT_Y + short_arm() + 1.0,
        state["ball_y"],
        counter_y - COUNTER_SIZE,
        counter_y + COUNTER_SIZE,
    ]

    for x, y in state["trajectory"]:
        xs.append(x)
        ys.append(y)

    for x, y in state["predicted_path"]:
        xs.append(x)
        ys.append(y)

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    margin_x = max(2.0, (max_x - min_x) * 0.10)
    margin_y = max(1.2, (max_y - min_y) * 0.16)

    min_x -= margin_x
    max_x += margin_x
    min_y -= margin_y
    max_y += margin_y

    world_w = max_x - min_x
    world_h = max_y - min_y
    screen_aspect = WORLD_W / HEIGHT
    world_aspect = world_w / world_h

    if world_aspect < screen_aspect:
        needed_w = world_h * screen_aspect
        extra = (needed_w - world_w) / 2
        min_x -= extra
        max_x += extra
    else:
        needed_h = world_w / screen_aspect
        extra = (needed_h - world_h) / 2
        min_y -= extra
        max_y += extra

    smooth = 1.0 if state["released"] else 0.12
    camera["min_x"] = lerp(camera["min_x"], min_x, smooth)
    camera["max_x"] = lerp(camera["max_x"], max_x, smooth)
    camera["min_y"] = lerp(camera["min_y"], min_y, smooth)
    camera["max_y"] = lerp(camera["max_y"], max_y, smooth)


# Zamiana wspolrzednych fizycznych, liczonych w metrach, na piksele ekranu.
def world_to_screen(x, y):
    # Mapowanie liniowe z ukladu swiata do ekranu:
    # sx = (x - min_x) / szerokosc_swiata * szerokosc_ekranu.
    # Dla osi y odejmujemy od HEIGHT, bo w pygame y rosnie w dol.
    sx = int((x - camera["min_x"]) / (camera["max_x"] - camera["min_x"]) * WORLD_W)
    sy = int(HEIGHT - (y - camera["min_y"]) / (camera["max_y"] - camera["min_y"]) * HEIGHT)
    return sx, sy


# Przeliczanie rozmiarow obiektow z metrow na piksele.
# Dzieki temu trebusz i przeciwwaga zmniejszaja sie przy oddaleniu kamery.
def metres_to_pixels(value):
    scale_x = WORLD_W / (camera["max_x"] - camera["min_x"])
    scale_y = HEIGHT / (camera["max_y"] - camera["min_y"])
    return max(2, int(value * min(scale_x, scale_y)))


def line_width_metres(value):
    return max(1, metres_to_pixels(value))


def draw_text(text, x, y, color=(25, 25, 25), use_font=None):
    label = (use_font or font).render(text, True, color)
    screen.blit(label, (x, y))


# Rysowanie kuli w aktualnym kadrze.
def draw_ball(x, y):
    pygame.draw.circle(
        screen,
        (35, 35, 35),
        world_to_screen(x, y),
        metres_to_pixels(BALL_RADIUS),
    )


# Polozenie paska suwaka w panelu bocznym.
def slider_rect(index):
    x = WORLD_W + 32
    y = 182 + index * 55
    return pygame.Rect(x, y, PANEL_W - 64, 8)


# Aktualizacja parametru na podstawie pozycji myszy na suwaku.
def set_slider_value(index, mouse_x):
    key, _label, lo, hi, _unit = SLIDERS[index]
    rect = slider_rect(index)
    # Normalizacja pozycji myszy na zakres 0..1:
    # t = (x_myszy - x_poczatku_suwaka) / szerokosc_suwaka.
    # Potem interpolujemy liniowo wartosc parametru:
    # value = min + t*(max - min).
    t = clamp((mouse_x - rect.left) / rect.width, 0.0, 1.0)
    PARAMS[key] = lo + t * (hi - lo)

    if PARAMS["release_max_angle"] <= PARAMS["release_min_angle"] + 2:
        if key == "release_min_angle":
            PARAMS["release_max_angle"] = PARAMS["release_min_angle"] + 2
        else:
            PARAMS["release_min_angle"] = PARAMS["release_max_angle"] - 2


# Panel boczny: wynik dystansu i wszystkie suwaki parametrow.
def draw_panel(state):
    pygame.draw.rect(screen, (244, 245, 241), (WORLD_W, 0, PANEL_W, HEIGHT))
    pygame.draw.line(screen, (195, 198, 188), (WORLD_W, 0), (WORLD_W, HEIGHT), 2)

    draw_text("Parametry trebusza", WORLD_W + 24, 22, use_font=title_font)
    draw_text("Przeciagnij suwaki. R - restart.", WORLD_W + 24, 54, color=(70, 70, 65), use_font=small_font)

    if state["distance"] is None:
        result = "Dystans: jeszcze nie zmierzony"
    else:
        result = f"Dystans: {state['distance']:.2f} m"
    draw_text(result, WORLD_W + 24, 88, color=(125, 35, 28), use_font=font)

    if state["release_speed"] is None:
        release_result = "Predkosc wyrzutu: -"
    else:
        release_result = f"Predkosc wyrzutu: {state['release_speed']:.2f} m/s"
    draw_text(release_result, WORLD_W + 24, 114, color=(55, 55, 50), use_font=small_font)

    if state["impact_speed"] is None:
        impact_result = "Predkosc uderzenia: -"
    else:
        impact_result = f"Predkosc uderzenia: {state['impact_speed']:.2f} m/s"
    draw_text(impact_result, WORLD_W + 24, 136, color=(55, 55, 50), use_font=small_font)

    for i, (key, label, lo, hi, unit) in enumerate(SLIDERS):
        rect = slider_rect(i)
        value = PARAMS[key]
        t = (value - lo) / (hi - lo)
        knob_x = rect.left + t * rect.width

        label_y = rect.top - 24
        value_text = f"{label}: {value:.2f} {unit}"
        draw_text(value_text, rect.left, label_y, use_font=small_font)

        pygame.draw.rect(screen, (206, 208, 199), rect, border_radius=4)
        fill_rect = pygame.Rect(rect.left, rect.top, int(t * rect.width), rect.height)
        pygame.draw.rect(screen, (120, 78, 36), fill_rect, border_radius=4)
        pygame.draw.circle(screen, (42, 42, 38), (int(knob_x), rect.centery), 9)


# Glowna fizyka symulacji.
# Najpierw obraca sie ramie, pozniej liczony jest ruch przeciwwagi,
# a na koncu kula: albo porusza sie na procy, albo leci balistycznie.
def update_physics(state):
    if state["landed"]:
        return

    theta = state["theta"]
    omega = state["omega"]
    released = state["released"]

    old_hook_vx = state["last_hook_vx"]
    old_hook_vy = state["last_hook_vy"]

    # Pierwsze oszacowanie ruchu ramienia na podstawie obecnych sil.
    alpha = angular_acceleration(state, attached_ball=not released)
    omega += alpha * DT
    theta += omega * DT

    state["theta"] = theta
    state["omega"] = omega
    state["time"] += DT

    hook_vx, hook_vy = arm_short_tip_velocity(theta, omega)
    # Przyspieszenie haka liczymy numerycznie z roznicy predkosci:
    # a = (v_now - v_previous) / dt.
    hook_ax = (hook_vx - old_hook_vx) / DT
    hook_ay = (hook_vy - old_hook_vy) / DT
    state["last_hook_vx"] = hook_vx
    state["last_hook_vy"] = hook_vy

    # Przeciwwaga jest traktowana jak wahadlo na ruchomym punkcie zaczepienia.
    # Przyspieszenie haka zmienia efektywny kierunek "dol" widziany przez wahadlo.
    c_angle = state["counter_angle"]
    c_omega = state["counter_omega"]
    # Rownanie wahadla z poruszajacym sie punktem zawieszenia:
    # phi'' = (-a_x*cos(phi) - (g + a_y)*sin(phi)) / L.
    # Gdy hak stoi nieruchomo, zostaje klasyczne:
    # phi'' = -(g/L)*sin(phi).
    c_alpha = (
        -hook_ax * math.cos(c_angle)
        - (GRAVITY + hook_ay) * math.sin(c_angle)
    ) / counter_hang()

    # Tlumienie katowe przeciwwagi: phi'' -= c*phi'.
    c_alpha -= 0.08 * c_omega

    # Caly program uzywa prostej integracji pol-implicit Euler:
    # najpierw aktualizujemy predkosc, potem polozenie.
    c_omega += c_alpha * DT
    c_angle += c_omega * DT
    state["counter_angle"] = c_angle
    state["counter_omega"] = c_omega

    # Drugie, mniejsze oszacowanie ruchu ramienia po policzeniu naciagu linki.
    alpha = angular_acceleration(state, attached_ball=not released, hook_ax=hook_ax, hook_ay=hook_ay)
    state["omega"] += alpha * DT * 0.35
    omega = state["omega"]

    tip = arm_long_tip(theta)
    tip_vx, tip_vy = arm_long_tip_velocity(theta, omega)

    if not released:
        # Kula przed zwolnieniem jest punktem na koncu procy.
        # Najpierw dziala grawitacja, potem wymuszamy stala dlugosc procy.
        # vy = vy - g*dt, x = x + vx*dt, y = y + vy*dt.
        state["ball_vy"] -= GRAVITY * DT
        state["ball_x"] += state["ball_vx"] * DT
        state["ball_y"] += state["ball_vy"] * DT

        # Wektor od konca ramienia do kuli.
        # Po normalizacji daje kierunek linki procy.
        dx = state["ball_x"] - tip[0]
        dy = state["ball_y"] - tip[1]
        dist = math.hypot(dx, dy)

        if dist == 0:
            dx, dy, dist = 0.0, -1.0, 1.0

        nx = dx / dist
        ny = dy / dist

        # Wymuszenie wiezu dlugosci procy:
        # polozenie_kuli = koniec_ramienia + kierunek_linki * dlugosc_procy.
        state["ball_x"] = tip[0] + nx * sling_length()
        state["ball_y"] = tip[1] + ny * sling_length()

        # Predkosc wzgledna kuli wobec konca ramienia.
        rel_vx = state["ball_vx"] - tip_vx
        rel_vy = state["ball_vy"] - tip_vy

        # Rzut predkosci wzglednej na kierunek linki:
        # v_radial = v_rel dot n.
        radial_speed = rel_vx * nx + rel_vy * ny

        # Usuwamy skladowa predkosci wzdluz procy.
        # Pozostaje skladowa styczna, ktora daje efekt wyrzutu.
        # v = v - v_radial*n.
        state["ball_vx"] -= radial_speed * nx
        state["ball_vy"] -= radial_speed * ny

        # Predkosc i kat lotu:
        # speed = sqrt(vx^2 + vy^2), angle = atan2(vy, vx).
        speed = math.hypot(state["ball_vx"], state["ball_vy"])
        flight_angle = math.atan2(state["ball_vy"], state["ball_vx"])

        min_angle = math.radians(PARAMS["release_min_angle"])
        max_angle = math.radians(PARAMS["release_max_angle"])

        good_release = (
            state["time"] > 0.35
            and state["ball_vx"] > 0
            and speed > PARAMS["release_min_speed"]
            and min_angle <= flight_angle <= max_angle
        )
        fallback_release = (
            theta < math.radians(95)
            and state["ball_vx"] > 0
            and speed > max(0.5, PARAMS["release_min_speed"] * 0.35)
        )

        if good_release or fallback_release:
            # W chwili zwolnienia zapamietujemy punkt startu lotu
            # i liczymy przewidywana trajektorie do ziemi.
            state["released"] = True
            state["release_x"] = state["ball_x"]
            state["release_vx"] = state["ball_vx"]
            state["release_vy"] = state["ball_vy"]
            state["release_speed"] = speed
            state["predicted_path"] = predict_ballistic_path(
                state["ball_x"],
                state["ball_y"],
                state["ball_vx"],
                state["ball_vy"],
            )
    else:
        # Po zwolnieniu kula leci jak klasyczny pocisk balistyczny.
        # vx jest stale, vy maleje o g*dt; nie uwzgledniamy oporu powietrza.
        state["ball_vy"] -= GRAVITY * DT
        state["ball_x"] += state["ball_vx"] * DT
        state["ball_y"] += state["ball_vy"] * DT

        if state["ball_y"] <= BALL_RADIUS:
            # Po uderzeniu w ziemie zatrzymujemy kule i zapisujemy dystans lotu.
            state["ball_y"] = BALL_RADIUS
            state["landing_x"] = state["ball_x"]
            state["impact_speed"] = math.hypot(state["ball_vx"], state["ball_vy"])
            if state["release_x"] is not None:
                # Dystans poziomy od punktu zwolnienia do punktu ladowania.
                state["distance"] = max(0.0, state["landing_x"] - state["release_x"])
            state["ball_vx"] = 0.0
            state["ball_vy"] = 0.0
            state["landed"] = True

    state["trajectory"].append((state["ball_x"], state["ball_y"]))
    if len(state["trajectory"]) > 3000:
        state["trajectory"].pop(0)


# Rysowanie lewej czesci ekranu: ziemia, trebusz, proca, przeciwwaga i tor kuli.
def draw_world(state):
    screen.fill((234, 238, 232))
    pygame.draw.rect(screen, (234, 238, 232), (0, 0, WORLD_W, HEIGHT))

    ground_y = world_to_screen(0, 0)[1]
    pygame.draw.line(screen, (70, 100, 70), (0, ground_y), (WORLD_W, ground_y), 3)

    pivot = world_to_screen(PIVOT_X, PIVOT_Y)
    long_end_world = arm_long_tip(state["theta"])
    short_end_world = arm_short_tip(state["theta"])
    counter_world = counterweight_center(state["theta"], state["counter_angle"])
    long_end = world_to_screen(*long_end_world)
    short_end = world_to_screen(*short_end_world)
    counter_center = world_to_screen(*counter_world)
    ball_pos = world_to_screen(state["ball_x"], state["ball_y"])

    if len(state["predicted_path"]) > 2:
        # Jasna linia to przewidywany tor po zwolnieniu.
        predicted = [world_to_screen(x, y) for x, y in state["predicted_path"]]
        pygame.draw.lines(screen, (210, 150, 135), False, predicted, 1)

    if len(state["trajectory"]) > 2:
        # Ciemniejsza linia to faktycznie przebyta droga kuli.
        trajectory = [world_to_screen(x, y) for x, y in state["trajectory"]]
        pygame.draw.lines(screen, (190, 60, 45), False, trajectory, line_width_metres(0.035))

    # Drewniana podstawa trebusza.
    base_left = world_to_screen(PIVOT_X - 1.8, 0)
    base_right = world_to_screen(PIVOT_X + 1.8, 0)
    frame_width = line_width_metres(0.14)
    pygame.draw.line(screen, (100, 75, 45), base_left, pivot, frame_width)
    pygame.draw.line(screen, (100, 75, 45), base_right, pivot, frame_width)
    pygame.draw.line(screen, (100, 75, 45), base_left, base_right, frame_width)

    # Ramie glowne i os obrotu.
    pygame.draw.line(screen, (120, 78, 36), long_end, short_end, line_width_metres(0.20))
    pygame.draw.circle(screen, (35, 35, 35), pivot, metres_to_pixels(0.16))

    # Linka przeciwwagi i sama przeciwwaga.
    pygame.draw.line(
        screen,
        (55, 48, 42),
        short_end,
        counter_center,
        line_width_metres(0.045),
    )
    pygame.draw.circle(screen, (45, 40, 35), short_end, metres_to_pixels(0.08))

    counter_size = metres_to_pixels(COUNTER_SIZE)
    pygame.draw.rect(
        screen,
        (82, 78, 75),
        pygame.Rect(
            counter_center[0] - counter_size // 2,
            counter_center[1] - counter_size // 2,
            counter_size,
            counter_size,
        ),
        border_radius=4,
    )

    if not state["released"]:
        # Linka procy jest widoczna tylko przed zwolnieniem kuli.
        pygame.draw.line(screen, (75, 58, 38), long_end, ball_pos, line_width_metres(0.045))

    draw_ball(state["ball_x"], state["ball_y"])

    if state["landed"] and state["impact_speed"] is not None:
        speed = state["impact_speed"]
    else:
        speed = math.hypot(state["ball_vx"], state["ball_vy"])
    angle = math.degrees(math.atan2(state["ball_vy"], state["ball_vx"]))

    if state["landed"]:
        status = "Stan: kula wyladowala"
    elif state["released"]:
        status = "Stan: kula w locie"
    else:
        status = "Stan: kula w procy"

    draw_text("R - restart", 20, 20)
    draw_text(status, 20, 45)
    speed_label = "Predkosc uderzenia" if state["landed"] else "Predkosc kuli"
    draw_text(f"{speed_label}: {speed:.2f} m/s", 20, 70)
    draw_text(f"Kat lotu: {angle:.1f} stopni", 20, 95)

    if state["distance"] is not None:
        draw_text(f"Dystans lotu: {state['distance']:.2f} m", 20, 120, color=(125, 35, 28))
    if state["release_speed"] is not None:
        draw_text(f"Predkosc wyrzutu: {state['release_speed']:.2f} m/s", 20, 145, color=(45, 45, 45))


state = reset()
running = True

# Glowna petla programu: obsluga zdarzen, fizyka, kamera i rysowanie.
while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            state = reset()
            camera = BASE_VIEW.copy()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(len(SLIDERS)):
                hit = slider_rect(i).inflate(0, 22)
                if hit.collidepoint(event.pos):
                    active_slider = i
                    set_slider_value(i, event.pos[0])
                    state = reset()
                    camera = BASE_VIEW.copy()
                    break

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            active_slider = None

        if event.type == pygame.MOUSEMOTION and active_slider is not None:
            set_slider_value(active_slider, event.pos[0])
            state = reset()
            camera = BASE_VIEW.copy()

    update_physics(state)
    update_camera(state)
    draw_world(state)
    draw_panel(state)
    pygame.display.flip()

pygame.quit()
