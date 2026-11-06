# Narration lines for "Abandoned, But Not Forgotten".
# Each entry: (id, scene, start_seconds, text_for_tts, subtitle_text)
# start_seconds are placed on the 90 s master timeline; the mixer uses them directly.
# Accuracy edits vs. the brief (sourced from NASA NSSDCA + science.nasa.gov):
#   * "Two years later" -> "Two and a half years later" (Apr 1967 -> Nov 1969).
#   * TTS spells out numbers so the voice pronounces them naturally.

LINES = [
    # SCENE 1 - THE MYSTERIOUS SIGNAL (0-8)
    ("s1_01", 1, 0.0, "Hello...?", "Hello...?"),
    ("s1_02", 1, 0.0, "Hello?", "Hello...?"),
    ("s1_03", 1, 0.0, "Can anyone hear me?", "Can anyone hear me?"),
    ("s1_04", 1, 0.0, "Is someone out there?", "Is someone out there?"),
    # SCENE 2 - MEET SURVEYOR 3 (8-21)
    ("s2_01", 2, 0.0, "Oh... there you are.", "Oh... there you are."),
    ("s2_02", 2, 0.0, "It's been such a long time since someone came to visit me.",
     "It's been such a long time since someone came to visit me."),
    ("s2_03", 2, 0.0, "My name is Surveyor Three.", "My name is Surveyor 3."),
    ("s2_04", 2, 0.0, "And I have a story to tell.", "And I have a story to tell."),
    # SCENE 3 - MY JOURNEY TO THE MOON (21-36)
    ("s3_01", 3, 0.0, "I was launched on April seventeenth, nineteen sixty-seven.",
     "I was launched on April 17, 1967."),
    ("s3_02", 3, 0.0, "My mission was simple, but incredibly important.",
     "My mission was simple, but incredibly important."),
    ("s3_03", 3, 0.0, "I was sent to prove that humans could one day land safely on the Moon.",
     "I was sent to prove that humans could one day land safely on the Moon."),
    ("s3_04", 3, 0.0, "I explored the lunar soil, captured thousands of images, and helped prepare the way for human exploration.",
     "I explored the lunar soil, captured thousands of images,|and helped prepare the way for human exploration."),
    # SCENE 4 - I HAD A PURPOSE (36-49)
    ("s4_01", 4, 0.0, "I studied the soil beneath me.", "I studied the soil beneath me."),
    ("s4_02", 4, 0.0, "I dug into the lunar surface.", "I dug into the lunar surface."),
    ("s4_03", 4, 0.0, "Every image, every measurement, every little experiment, helped scientists understand a world humanity had only dreamed of exploring.",
     "Every image, every measurement, every little experiment|helped scientists understand a world humanity had only dreamed of exploring."),
    # SCENE 5 - SOMEONE CAME BACK (49-66)
    ("s5_01", 5, 0.0, "And then... something extraordinary happened.", "And then... something extraordinary happened."),
    ("s5_02", 5, 0.0, "Two and a half years later... someone came back.", "Two and a half years later... someone came back."),
    ("s5_03", 5, 0.0, "Apollo Twelve astronauts walked across the Moon to visit me.",
     "Apollo 12 astronauts walked across the Moon to visit me."),
    ("s5_04", 5, 0.0, "They studied me, collected parts of me, and brought them home.",
     "They studied me, collected parts of me, and brought them home."),
    ("s5_05", 5, 0.0, "For the first time, I wasn't just a machine left behind.",
     "For the first time, I wasn't just a machine left behind."),
    ("s5_06", 5, 0.0, "Someone had remembered me.", "Someone had remembered me."),
    # SCENE 6 - I'M NOT THE ONLY ONE (66-79)
    ("s6_01", 6, 0.0, "And I'm not the only one with a story.", "And I'm not the only one with a story."),
    ("s6_02", 6, 0.0, "Far away on Mars, my friend Opportunity explored another world for nearly fifteen years.",
     "Far away on Mars, my friend Opportunity|explored another world for nearly fifteen years."),
    ("s6_03", 6, 0.0, "Different missions. Different worlds.", "Different missions. Different worlds."),
    ("s6_04", 6, 0.0, "But we share something special.", "But we share something special."),
    ("s6_05", 6, 0.0, "We helped humanity discover things it never knew before.",
     "We helped humanity discover things it never knew before."),
    # SCENE 7 - THE INVITATION (79-90)
    ("s7_01", 7, 0.0, "So... what do you say?", "So... what do you say?"),
    ("s7_02", 7, 0.0, "Come along with me.", "Come along with me."),
    ("s7_03", 7, 0.0, "Let's explore the machines that changed our understanding of the universe.",
     "Let's explore the machines that changed our understanding of the universe."),
    ("s7_04", 7, 0.0, "Because even when their missions end...", "Because even when their missions end..."),
    ("s7_05", 7, 0.0, "their stories never do.", "...their stories never do."),
]
