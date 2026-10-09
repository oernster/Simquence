"""The toolbar's sizes, in one Qt-free place.

The buttons and the stylesheet both need them. Written once here, the button
height follows the pictures rather than being a second number kept in step by
hand, which is how a stylesheet minimum and a widget height drift apart.
"""

from __future__ import annotations

# The pictures on the action buttons.
ARTWORK_PX = 48

# The donate mark's height. Smaller than the action pictures because it is a
# wide mark rather than a square one.
GLYPH_PX = 40

# The theme toggle's sun and moon, drawn as emoji text.
EMOJI_PX = 36

# The 2px ring and the 2px padding, above and below the picture, plus a pixel
# of air on each side so the ring never touches it.
_BUTTON_CHROME_PX = 10

TOOLBAR_BUTTON_PX = ARTWORK_PX + _BUTTON_CHROME_PX
