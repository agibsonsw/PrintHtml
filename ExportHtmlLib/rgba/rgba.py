'''
RGBA
Licensed under MIT
Copyright (c) 2012 Isaac Muse <isaacmuse@gmail.com>
'''

import math
import re


class RGBA(object):
    r = None
    g = None
    b = None
    a = None
    color_pattern = re.compile(r"^#(?:([A-Fa-f\d]{6})([A-Fa-f\d]{2})?|([A-Fa-f\d]{3}))")

    def __init__(self, s):
        self.r, self.g, self.b, self.a = self._split_channels(s)

    def _split_channels(self, s):
        def alpha_channel(alpha):
            return int(alpha, 16) if alpha else 0xFF

        m = self.color_pattern.match(s)
        if m is not None:
            if m.group(1):
                return int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16), alpha_channel(m.group(2))
            else:
                return int(s[1] * 2, 16), int(s[2] * 2, 16), int(s[3] * 2, 16), 0xFF
        return 0x0, 0x0, 0x0, 0xFF

    def get_rgba(self):
        return "#%02X%02X%02X%02X" % (self.r, self.g, self.b, self.a)

    def get_rgb(self):
        return "#%02X%02X%02X" % (self.r, self.g, self.b)

    def apply_alpha(self, background="#000000AA"):
        def tx_alpha(cf, af, cb, ab):
            return abs(cf * af + cb * ab * (1 - af)) & 0xFF

        if self.a < 0xFF:
            r, g, b, a = self._split_channels(background)

            self.r, self.g, self.b = (tx_alpha(self.r, self.a, r, a), tx_alpha(self.g, self.a, g, a), tx_alpha(self.b, self.a, b, a))

        return self.get_rgb()

    def luminance(self):
        return int(0.299 * self.r + 0.587 * self.g + 0.114 * self.b)

    def brightness(self, lumes):
        def get_overage(c):
            o = 0
            if c < 0:
                o = 0 + c
                c = 0
            elif c > 255:
                o = c - 255
                c = 255
            return o, c

        def distribute_overage(r, g, b, o, s):
            channels = len(s)
            if channels == 0:
                return r, g, b
            share = o / len(s)
            if "r" in s and "g" in s:
                return r + share, g + share, b
            elif "r" in s and "b" in s:
                return r + share, g, b + share
            elif "g" in s and "b" in s:
                return r, g + share, b + share
            elif "r" in s:
                return r + share, g, b
            elif "g" in s:
                return r, g + share, b
            else:  # "b" in s:
                return r, g, b + share

        l = self.luminance()

        # Balck or white
        if l + lumes > 255:
            self.r = 0xFF
            self.g = 0xFF
            self.b = 0xFF
            return
        elif l + lumes < 0:
            self.r = 0x00
            self.g = 0x00
            self.b = 0x00
            return

        # Adjust Brightness
        factor = (l + lumes - 0.299 * self.r - 0.587 * self.g - 0.114 * self.b)

        slots = set(["r", "g", "b"])
        rf = self.r + factor
        gf = self.g + factor
        bf = self.b + factor

        overage, rf = get_overage(rf)
        if overage:
            slots.remove("r")
            rf, gf, bf = distribute_overage(rf, gf, bf, overage, slots)
        overage, gf = get_overage(gf)
        if overage:
            slots.remove("g")
            rf, gf, bf = distribute_overage(rf, gf, bf, overage, slots)
        overage, bf = get_overage(bf)
        if overage:
            slots.remove("b")
            rf, gf, bf = distribute_overage(rf, gf, bf, overage, slots)

        self.r = int(math.ceil(rf)) & 0xFF
        self.g = int(math.ceil(gf)) & 0xFF
        self.b = int(math.ceil(bf)) & 0xFF
