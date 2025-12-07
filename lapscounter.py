import math

# ======================
# Basic geometry helpers
# ======================

class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


def ll_to_xy(lat, lon, ref_lat, ref_lon):
    """
    Convert latitude/longitude to local x,y (meters) using equirectangular
    projection with cosine at the average latitude for proper east-west scale.
    """
    R = 6371000.0  # meters
    lat_rad = math.radians(lat)
    ref_lat_rad = math.radians(ref_lat)
    dlat = math.radians(lat - ref_lat)
    dlon = math.radians(lon - ref_lon)
    x = R * dlon * math.cos((lat_rad + ref_lat_rad) / 2.0)
    y = R * dlat
    return x, y


def seg_intersect(p1, p2, q1, q2):
    """Classic segment intersection (exact, no tolerance)."""
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
    return ccw(p1, q1, q2) != ccw(p2, q1, q2) and ccw(p1, p2, q1) != ccw(p1, p2, q2)


def seg_intersect_with_tolerance(p1, p2, q1, q2, tolerance=10.0):
    """
    Legacy tolerant intersection. Kept for compatibility,
    but LapCounter below does a stricter side-change check instead.
    """
    if seg_intersect(p1, p2, q1, q2):
        return True
    for a in (p1, p2):
        for b in (q1, q2):
            if math.hypot(a[0]-b[0], a[1]-b[1]) <= tolerance:
                return True
    return False


def _signed_side(point: Point, a: Point, b: Point) -> float:
    """
    Signed area (cross product) telling which side of line AB 'point' lies on.
    >0 one side, <0 the other, 0 on the infinite line.
    """
    return (b.x - a.x) * (point.y - a.y) - (b.y - a.y) * (point.x - a.x)


def _segment_min_distance_to_line(p: Point, q: Point, a: Point, b: Point) -> float:
    """
    Minimum distance from segment PQ to infinite line AB (not segment AB).
    Used only as a soft helper with tolerance when very near the line.
    """
    # Distance from a point to an infinite line = |cross(AB, AP)| / |AB|
    abx, aby = (b.x - a.x), (b.y - a.y)
    ab_len = math.hypot(abx, aby)
    if ab_len == 0:
        return math.hypot(p.x - a.x, p.y - a.y)
    # take min of endpoints’ distances; good enough as a soft check
    def point_to_line(pt: Point):
        return abs((abx * (pt.y - a.y) - aby * (pt.x - a.x)) / ab_len)
    return min(point_to_line(p), point_to_line(q))


def _sign(x: float, eps: float = 1e-9) -> int:
    if x > eps:
        return 1
    if x < -eps:
        return -1
    return 0


# ======================
# Lap counter (robust)
# ======================

class LapCounter:
    """
    Robust lap counter that:
      1) Requires a true side change across the finish line.
      2) Applies a distance tolerance to allow for GPS error near the line.
      3) Ignores tiny movements (< min_move).
      4) Requires a minimum distance traveled between counted crossings
         to prevent over-counting clustered samples during one pass.
    """
    def __init__(
        self,
        line_start: Point,
        line_end: Point,
        *,
        tolerance_m: float = 20.0,
        min_move_m: float = 0.5,
        min_lap_distance_m: float = 50.0
    ):
        self.line_start = line_start
        self.line_end = line_end
        self.tolerance_m = float(tolerance_m)
        self.min_move_m = float(min_move_m)
        self.min_lap_distance_m = float(min_lap_distance_m)

        self.previous_position: Point | None = None
        self.current_position: Point | None = None

        self._last_side: int | None = None      # last known side (+1 / -1)
        self._last_cross_xy: Point | None = None
        self.lap_count: int = 0

    def update_position(self, lat: float, lon: float, ref_lat: float, ref_lon: float):
        """Feed one GPS sample and update lap count if a valid crossing occurs."""
        self.current_position = Point(*ll_to_xy(lat, lon, ref_lat, ref_lon))

        if self.previous_position is None:
            # Initialize side on first meaningful sample
            s_now = _sign(_signed_side(self.current_position, self.line_start, self.line_end))
            if s_now != 0:
                self._last_side = s_now
            self.previous_position = self.current_position
            return

        # Ignore tiny/no-movement jitter
        move = math.hypot(
            self.current_position.x - self.previous_position.x,
            self.current_position.y - self.previous_position.y
        )
        if move < self.min_move_m:
            return

        # Compute side for previous and current positions
        s_prev_raw = _signed_side(self.previous_position, self.line_start, self.line_end)
        s_curr_raw = _signed_side(self.current_position, self.line_start, self.line_end)
        s_prev = _sign(s_prev_raw)
        s_curr = _sign(s_curr_raw)

        # Straddle test: strict crossing if signs differ
        crossed_strict = (s_prev * s_curr) < 0

        # Soft near-line test (within tolerance of the infinite line)
        near_line = (
            abs(s_prev_raw) <= self.tolerance_m or
            abs(s_curr_raw) <= self.tolerance_m or
            _segment_min_distance_to_line(self.previous_position, self.current_position,
                                          self.line_start, self.line_end) <= self.tolerance_m
        )

        # Decide if this sample constitutes a crossing:
        # - Prefer strict side change.
        # - If not strictly straddling, allow near-line if we actually changed side
        #   relative to the last known stable side.
        crossing = False
        if crossed_strict:
            crossing = True
        elif near_line and self._last_side is not None and (s_curr != 0) and (s_curr != self._last_side):
            crossing = True

        if crossing:
            # Merge/cluster protection via minimum distance between counted crossings
            count_this = True
            if self._last_cross_xy is not None:
                gap = math.hypot(
                    self.current_position.x - self._last_cross_xy.x,
                    self.current_position.y - self._last_cross_xy.y
                )
                if gap < self.min_lap_distance_m:
                    count_this = False  # still same pass cluster; don't double-count

            if count_this:
                self.lap_count += 1
                self._last_cross_xy = Point(self.current_position.x, self.current_position.y)

        # Update last stable side if we’re not essentially on the line
        if s_curr != 0:
            self._last_side = s_curr

        # Slide window
        self.previous_position = self.current_position
