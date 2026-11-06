"""Batch of reference-locked plates generated with FLUX.1 Kontext (free HF space).
Every Surveyor plate is derived from the approved hero design (plates/p_hero.jpg etc.)
so the lander stays consistent. Run: python src/plates_batch.py [name ...]"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLE = (" Keep the premium 3D animated feature-film rendering style, physically based materials, "
         "cinematic lighting and shallow depth of field. No text, no logos, no watermark.")
KEEP = ("Keep the exact same NASA Surveyor 3 lander design: tripod with exactly three legs and round "
        "footpads, central mast with flat solar panel and flat planar antenna, cylindrical TV camera "
        "with mirror hood, scissor-lattice sampling arm with scoop. No face, no eyes, no wheels. ")

RESTYLE = ("Convert this real NASA photograph into a full-color premium 3D animated feature-film still. "
           "Keep the exact composition, camera angle, hardware shapes and proportions, and the poses; "
           "replace only the photographic look with rich physically based 3D rendering and cinematic light. ")

JOBS = {
    "k_apollo_wide": ("plates/p_hero.jpg", KEEP +
        "The lander now sits on the inner slope of a shallow crater, covered in a fine layer of dust. Two "
        "Apollo astronauts in white spacesuits with life-support backpacks and gold visors walk down the "
        "crater slope toward it from the right background, leaving footprints. Far away on the crater rim "
        "stands a small Apollo lunar module with gold foil descent stage. Black sky, Earth high in the sky, "
        "warm low sunlight.", 12),
    "k_descent": ("plates/p_hero.jpg", KEEP +
        "The lander is now hovering about two meters above the grey lunar surface during its final "
        "descent, legs extended, sampling arm folded against the body. Three short, soft, cone-shaped "
        "bluish-white rocket exhaust plumes glow under the body, and a radial sheet of fine lunar dust "
        "blows outward across the ground beneath it. Black starry sky, Earth upper right, golden sunlight "
        "from the right.", 21),
    "k_opp_hero": ("plates/inputs/opp_hero_in.jpg",
        "Convert this NASA artist concept into a premium 3D animated feature-film still and extend the "
        "Martian landscape naturally across the whole frame (no blurred borders). Keep the exact NASA Mars "
        "Exploration Rover Opportunity design: six wheels on rocker-bogie suspension, flat dark-blue solar "
        "panel wings, tall camera mast with twin camera head, robotic arm. Rich rusty-orange terrain, warm "
        "golden late-afternoon light, butterscotch sky, fine dust in the air, long shadows.", 4),
    "k_cruise": ("plates/p_hero.jpg", KEEP +
        "Remove the ground entirely: the lander now flies through deep black space toward the Moon, seen "
        "from slightly below and behind, legs extended, sampling arm folded. A huge grey cratered Moon fills "
        "the lower right of the frame, lit by golden sunlight; tiny distant stars; the small blue Earth far "
        "away in the upper left.", 7),
    "k_scoop": ("plates/p_hero.jpg", KEEP +
        "Macro close-up of the small metal sampling scoop at the end of the scissor-lattice arm biting into "
        "the grey lunar soil, digging a shallow trench, a few clumps of fine dark-grey regolith falling from "
        "the scoop's edge. Low golden sunlight raking across the soil texture, black sky, very shallow "
        "depth of field.", 9),
    "k_launch": ("plates/inputs/launch_in.jpg", RESTYLE +
        "A 1960s NASA Atlas-Centaur rocket lifting off at night from Cape Kennedy beside its red service "
        "tower, a brilliant orange-white engine flame and huge billowing clouds of exhaust smoke lit from "
        "within, warm sodium floodlights, deep blue night sky. No text, no logos.", 3),
    "k_touchdown": ("plates/p_lowangle.jpg", KEEP +
        "Extreme low close-up at ground level of one round landing footpad pressing into the soft grey "
        "lunar soil at the instant of touchdown, a ring of fine lunar dust bursting outward and up around "
        "the footpad, the shock-absorbing leg strut above it. The rest of the lander blurred above, black "
        "sky, golden sunlight, Earth softly out of focus.", 5),
    "k_apollo_examine": ("plates/inputs/apollo_examine_in.jpg", RESTYLE +
        "An Apollo 12 astronaut in a white spacesuit examining the dusty Surveyor 3 lander on the Moon in "
        "November 1969, the lunar module in the far distance on the crater rim; deep black sky, warm low "
        "sunlight, silver and dusty-tan lander surfaces.", 6),
    "k_opp_arm": ("plates/inputs/opp_arm_in.jpg",
        "Convert this NASA artist concept into a premium 3D animated feature-film still and extend the "
        "Martian landscape naturally across the whole frame (no blurred borders). Keep the exact rover "
        "design: six wheels, flat solar panel wings, tall camera mast, and the robotic arm reaching out to "
        "touch a reddish rock with its instrument turret. Rusty-orange terrain, warm golden light, "
        "butterscotch sky.", 8),
    "k_apollo_beside": ("plates/inputs/apollo_beside_in.jpg", RESTYLE +
        "An Apollo 12 astronaut in a white spacesuit standing right beside the dusty Surveyor 3 lander on "
        "the Moon, the lunar module small on the horizon, black sky, warm golden low sunlight, gentle rim "
        "light on the astronaut's helmet. Emotional, quiet, reverent mood.", 10),
}
LATE = {
    "k_opp_storm": ("plates/k_opp_hero.jpg",
        "Keep the exact same rover design and 3D animated film style. A massive Martian dust storm now "
        "darkens the sky into a thick hazy brown-orange murk, the Sun reduced to a faint pale disk, dust "
        "streaming past horizontally, a thin coat of dust on the solar panels. Moody, lonely.", 14),
    "k_opp_sunset": ("plates/k_opp_hero.jpg",
        "Keep the exact same rover design and 3D animated film style. The rover now rests quietly on the "
        "slope of a long shallow Martian valley at sunset, the small blue-white Martian sunset glow around "
        "the setting Sun on the horizon, long shadows, dusty solar panels, peaceful and bittersweet.", 15),
}
JOBS.update(LATE)

only = set(sys.argv[1:])
for name, (ref, prompt, seed) in JOBS.items():
    out = os.path.join(ROOT, "plates", name + ".jpg")
    if (only and name not in only) or (not only and os.path.exists(out)):
        continue
    r = subprocess.run([sys.executable, os.path.join(ROOT, "src/flux.py"), "kontext", out,
                        os.path.join(ROOT, ref), prompt + STYLE, str(seed)],
                       capture_output=True, text=True)
    print(name, (r.stdout + r.stderr).strip().splitlines()[-1][:300], flush=True)
