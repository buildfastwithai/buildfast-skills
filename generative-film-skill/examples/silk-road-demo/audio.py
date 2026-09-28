from audio_kit import *  # audio_kit.py beside this file

T = Track(bpm=110, beats=28, root=146.83, scale="hijaz")
T.drone_bed(0, 26, level=lambda b: 0.3 if b < 8 else 0.16)
for i in range(4):
    T.at("fx", bell(T.deg(i + 4, 1)), 4 + i, 0.18, -0.4 + 0.25 * i)
T.riser_into(8, 4, 0.3)
T.hand_drum(8, 16, pattern=("b", "-", "s", "t", "b", "b", "s", "-"))
T.melody(8, [(0, 4, 1), (1, 5, 1, 4), (2, 3, 1.5), (4, 2, .5), (4.5, 1, .5), (5, 0, 1.5)])
T.stutter(15.5)
T.groove(16, 24)
T.hand_drum(16, 24, gain=0.8)
T.melody(16, [(0, 7, .5), (.5, 6, .5), (1, 7, .7), (1.75, 4, .8), (3, 5, 1.2, 7), (4, 4, .5), (4.5, 3, .5), (5, 2, .5), (6, 0, 1.5)])
T.at("fx", boom(), 16, 0.5)
T.tihai(24)
T.at("pad", voice(T.hz(0), T.tb(4)), 24, 0.25)
T.mixdown("music.wav", fade_beats=(25, 28))
