"""Depth policy for explicitly sectioned diagnostic views, never film cameras."""


def section_rain_depth(camera_y, forward_y, front_max_ys, hidden_layers):
    if 'FRONT' not in hidden_layers or forward_y < .3 or not front_max_ys:
        return 0.0
    return max(0.0, (max(front_max_ys) + .3 - camera_y) / forward_y)
