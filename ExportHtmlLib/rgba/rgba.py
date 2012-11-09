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
        return int(math.sqrt(math.pow(self.r, 2) * .241 + math.pow(self.g, 2) * .691 + math.pow(self.b, 2) * .068))

    def brightness(self, lumes):
        lumes = float(max(min(lumes, 255), 0))
        l = self.luminance()
        factor = ((lumes + l) / 255.0) - (l / 255.0)

        def limit_range(c):
            c &= 0xFF
            return max(min(c, 0xFF), 0x0)

        self.r = limit_range(int(math.ceil(self.r + float(factor) * 255.0)))
        self.g = limit_range(int(math.ceil(self.g + float(factor) * 255.0)))
        self.b = limit_range(int(math.ceil(self.b + float(factor) * 255.0)))
