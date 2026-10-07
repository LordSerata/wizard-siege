"""
Visual helpers — glow, bloom, gradients.

All functions draw onto a surface using alpha blending so they stack
cleanly on top of whatever is already there.
"""

import pygame


def glow_circle(surface, color, pos, radius, layers=5, max_alpha=90):
    """Draw a soft bloom halo around a point."""
    for i in range(layers, 0, -1):
        r = int(radius * (1 + i * 0.55))
        alpha = int(max_alpha * (1 - i / (layers + 1)))
        s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (r + 1, r + 1), r)
        surface.blit(s, (pos[0] - r - 1, pos[1] - r - 1))


def glow_line(surface, color, start, end, width=2, layers=3, max_alpha=60):
    """Draw a glowing line (used for staff, beams, etc.)."""
    for i in range(layers, 0, -1):
        w = width + i * 3
        alpha = int(max_alpha * (1 - i / (layers + 1)))
        s = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.line(s, (*color, alpha), start, end, w)
        surface.blit(s, (0, 0))
    pygame.draw.line(surface, color, start, end, width)


def glow_rect(surface, color, rect, radius=6, layers=3, max_alpha=60):
    """Glowing border around a rect — good for UI panels."""
    for i in range(layers, 0, -1):
        pad = i * 3
        r = pygame.Rect(rect.x - pad, rect.y - pad,
                        rect.width + pad * 2, rect.height + pad * 2)
        alpha = int(max_alpha * (1 - i / (layers + 1)))
        s = pygame.Surface((r.width + 4, r.height + 4), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha),
                         (2, 2, r.width, r.height), border_radius=radius + pad)
        surface.blit(s, (r.x - 2, r.y - 2))


def radial_gradient(surface, center, inner_color, outer_color, radius):
    """Paint a soft radial gradient circle (cheap approximation)."""
    steps = 12
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(radius * t)
        color = tuple(
            int(inner_color[c] * (1 - t) + outer_color[c] * t)
            for c in range(3)
        )
        alpha = int(40 * (1 - t))
        s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (r + 1, r + 1), r)
        surface.blit(s, (center[0] - r - 1, center[1] - r - 1))


def load_fonts(base_path):
    """
    Load custom TTFs. Returns a dict of font objects.
    Falls back to system fonts if the files are missing.
    """
    import os

    def ttf(name, size, bold=False):
        path = os.path.join(base_path, "assets", "fonts", name)
        try:
            f = pygame.font.Font(path, size)
            # Verify the font actually renders — broken TTFs load but crash on render
            f.render("A", True, (255, 255, 255))
            return f
        except Exception:
            return pygame.font.SysFont("consolas", size, bold=bold)

    return {
        "title":   ttf("Cinzel-Bold.ttf",      52),
        "heading": ttf("Cinzel-Bold.ttf",       30),
        "ui":      ttf("Rajdhani-Bold.ttf",     22),
        "ui_sm":   ttf("Rajdhani-Medium.ttf",   17),
        "ui_xs":   ttf("Rajdhani-Medium.ttf",   14),
    }
