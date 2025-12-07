import math
import pandas as pd
import lapscounter  # your file with ll_to_xy

# ============================================================
# CONFIGURATION
# ============================================================
CSV_FILE = "onefifthnewdata copy.csv"

# Fixed finish line coordinates (from your analysis)
FINISH = {
    "start_lat": 42.906709,
    "start_lon": -89.326610,
    "end_lat":   42.906389,
    "end_lon":   -89.326607,
}

# Parameters
TOLERANCE_M      = 20.0    # ± GPS tolerance around finish line (meters)
MIN_MOVE_M       = 0.5     # ignore jitter
MERGE_INDEX_GAP  = 80      # collapse clustered hits
MIN_NORMAL_STEP  = 2.0     # minimum motion across line (meters)

# ============================================================
# GEOMETRY HELPERS
# ============================================================
def signed_side(px, py, ax, ay, bx, by):
    """Return signed cross product → which side of line AB point P lies on."""
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)

def point_to_line_distance(px, py, ax, ay, bx, by):
    """Distance from P to infinite line AB (in meters)."""
    abx, aby = (bx - ax), (by - ay)
    L = math.hypot(abx, aby)
    if L == 0:
        return math.hypot(px - ax, py - ay)
    return abs(abx * (py - ay) - aby * (px - ax)) / L

def within_segment_projection(px, py, ax, ay, bx, by, tolerance=20.0):
    """Check whether (px,py) projects within or near the finite segment A→B."""
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab_len2 = abx**2 + aby**2
    if ab_len2 == 0:
        return math.hypot(px - ax, py - ay) <= tolerance
    t = (apx * abx + apy * aby) / ab_len2  # projection scalar along AB
    # use ±(tolerance / sqrt(ab_len2)) margin, not tolerance/ab_len2 (too tiny)
    margin = tolerance / math.sqrt(ab_len2)
    return -margin <= t <= 1 + margin

def dot(ax, ay, bx, by):
    """Dot product helper."""
    return ax * bx + ay * by

# ============================================================
# LOAD DATA
# ============================================================
df = pd.read_csv(CSV_FILE)
lat_lon = df[['lat', 'lon']]
ref_lat = float(lat_lon.iloc[0]['lat'])
ref_lon = float(lat_lon.iloc[0]['lon'])

# Convert finish line endpoints to local XY
fx1, fy1 = lapscounter.ll_to_xy(FINISH["start_lat"], FINISH["start_lon"], ref_lat, ref_lon)
fx2, fy2 = lapscounter.ll_to_xy(FINISH["end_lat"],   FINISH["end_lon"],   ref_lat, ref_lon)

# Line unit vectors
lx, ly = (fx2 - fx1), (fy2 - fy1)
L = math.hypot(lx, ly)
ux, uy = lx / L, ly / L
nx, ny = -uy, ux  # perpendicular normal direction (for crossing sign)

# ============================================================
# SCAN GPS POINTS
# ============================================================
prev_xy = None
last_stable_side = None
last_hit_idx = None
raw_indices = []
raw_dirs = []  # store sign of direction

for i, row in enumerate(lat_lon.itertuples(index=False)):
    lat = float(row.lat)
    lon = float(row.lon)
    if lat == 0.0 or lon == 0.0:
        continue

    x, y = lapscounter.ll_to_xy(lat, lon, ref_lat, ref_lon)

    if prev_xy is not None:
        step_dx, step_dy = (x - prev_xy[0]), (y - prev_xy[1])
        if math.hypot(step_dx, step_dy) < MIN_MOVE_M:
            continue

        s_prev_raw = signed_side(prev_xy[0], prev_xy[1], fx1, fy1, fx2, fy2)
        s_curr_raw = signed_side(x, y, fx1, fy1, fx2, fy2)
        s_prev = 1 if s_prev_raw > 1e-6 else (-1 if s_prev_raw < -1e-6 else 0)
        s_curr = 1 if s_curr_raw > 1e-6 else (-1 if s_curr_raw < -1e-6 else 0)

        strict_cross = (s_prev * s_curr) < 0
        near_prev = point_to_line_distance(prev_xy[0], prev_xy[1], fx1, fy1, fx2, fy2) <= TOLERANCE_M
        near_curr = point_to_line_distance(x, y, fx1, fy1, fx2, fy2) <= TOLERANCE_M

        # projected step across line’s normal (for direction)
        normal_step = dot(step_dx, step_dy, nx, ny)
        proj_valid = within_segment_projection(x, y, fx1, fy1, fx2, fy2, tolerance=TOLERANCE_M)

        crossed = False
        if strict_cross:
            crossed = True
        elif (near_prev or near_curr) and last_stable_side is not None and s_curr != 0 and s_curr != last_stable_side:
            crossed = True

        if crossed and proj_valid and abs(normal_step) >= MIN_NORMAL_STEP:
            if last_hit_idx is None or (i - last_hit_idx) > MERGE_INDEX_GAP:
                raw_indices.append(i)
                raw_dirs.append(normal_step)
                last_hit_idx = i

        if not near_curr and s_curr != 0:
            last_stable_side = s_curr

    else:
        s0 = signed_side(x, y, fx1, fy1, fx2, fy2)
        if abs(s0) > 1e-6:
            last_stable_side = 1 if s0 > 0 else -1

    prev_xy = (x, y)

# ============================================================
# FILTER BY DIRECTION (forward-only)
# ============================================================
if raw_indices:
    forward_sign = 1 if raw_dirs[0] > 0 else -1
    forward_crossings = [
        idx for idx, d in zip(raw_indices, raw_dirs) if (1 if d > 0 else -1) == forward_sign
    ]
else:
    forward_crossings = []

laps = max(0, len(forward_crossings) - 1)

# ============================================================
# OUTPUT RESULTS
# ============================================================
print("==================== SEGMENT-VALIDATED RESULTS ====================")
print(f"All raw crossings (merged): {raw_indices}")
print(f"Forward-only crossings:     {forward_crossings}")
print(f"Detected laps (forward-1):  {laps}")
print("===================================================================")

