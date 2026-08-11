"""
kriging.py — Spatial Kriging (Ordinary Kriging) engine for the Master Node.

Interpolates sensor readings from N slave nodes across a spatial grid.
This Python prototype is validated offline and then ported to C++ for the ESP32-S3.

Usage:
    python kriging.py                    # demo run with synthetic node data
    python kriging.py --nodes nodes.json # run with real node coordinates + readings

Output:
    GeoJSON FeatureCollection of interpolated grid cells — matches the
    /api/kriging/heatmap endpoint format the Leaflet PWA expects.

Reference:
    Matheron, G. (1963). Principles of Geostatistics. Economic Geology 58(8).
    overview.pdf §7 — Spatial Kriging Engine.
"""

import numpy as np
import json
import argparse
from typing import List, Dict, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Variogram model
# ─────────────────────────────────────────────────────────────────────────────

def spherical_variogram(h: np.ndarray, nugget: float, sill: float, range_: float) -> np.ndarray:
    """
    Spherical variogram model.
    γ(h) = nugget + sill * [1.5*(h/a) - 0.5*(h/a)^3]  for h ≤ a
    γ(h) = nugget + sill                                 for h > a
    """
    h = np.asarray(h, dtype=float)
    result = np.where(
        h <= range_,
        nugget + sill * (1.5 * (h / range_) - 0.5 * (h / range_) ** 3),
        nugget + sill
    )
    result[h == 0] = 0.0
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Core Kriging
# ─────────────────────────────────────────────────────────────────────────────

class OrdinaryKriging:
    """
    Ordinary Kriging interpolator.

    Precomputes the covariance matrix A from node positions at startup.
    Runtime per grid point is just a matrix–vector solve (O(N²)).

    ESP32-S3 feasibility (per overview.pdf §7.2):
      N=20 nodes → 21×21 matrix → Gaussian elimination ≈ 9,261 MACs → <5 ms at 240 MHz.
    """

    def __init__(
        self,
        node_coords: np.ndarray,   # shape (N, 2), [lat, lon] in decimal degrees
        nugget: float = 0.0,
        sill: float   = 1.0,
        range_km: float = 10.0,    # spatial correlation range in km
    ):
        self.coords   = node_coords          # (N, 2)
        self.N        = len(node_coords)
        self.nugget   = nugget
        self.sill     = sill
        self.range_km = range_km

        # Precompute pairwise distance matrix (km) between nodes
        self.D = self._pairwise_distances(node_coords, node_coords)

        # Build (N+1)×(N+1) Kriging system matrix A
        # A = [ γ(dij)   1 ]
        #     [   1ᵀ     0 ]
        gamma = spherical_variogram(self.D, nugget, sill, range_km)
        A = np.zeros((self.N + 1, self.N + 1))
        A[:self.N, :self.N] = gamma
        A[:self.N, self.N]  = 1.0
        A[self.N, :self.N]  = 1.0
        A[self.N, self.N]   = 0.0

        # Precompute A⁻¹ once — only need to solve A·λ = b at runtime
        try:
            self.A_inv = np.linalg.inv(A)
        except np.linalg.LinAlgError:
            # Add small regularisation if matrix is singular
            A += np.eye(self.N + 1) * 1e-8
            self.A_inv = np.linalg.inv(A)

    def interpolate(self, query_coords: np.ndarray, values: np.ndarray) -> np.ndarray:
        """
        Interpolate `values` at `query_coords`.

        Args:
            query_coords: (M, 2) array of [lat, lon] query locations
            values:       (N,)   array of sensor readings at node locations

        Returns:
            (M,) array of interpolated values at each query location
        """
        assert len(values) == self.N, f"Expected {self.N} values, got {len(values)}"

        # Distance from each query point to all nodes
        D_query = self._pairwise_distances(query_coords, self.coords)  # (M, N)

        results = np.zeros(len(query_coords))

        for i, d_row in enumerate(D_query):
            # Build RHS vector b = [γ(d₀), γ(d₁), ..., γ(dN-1), 1]
            b = np.zeros(self.N + 1)
            b[:self.N] = spherical_variogram(d_row, self.nugget, self.sill, self.range_km)
            b[self.N]  = 1.0

            # Solve for weights λ = A⁻¹ · b
            weights = self.A_inv @ b          # (N+1,)
            lambda_ = weights[:self.N]        # drop the Lagrange multiplier

            # Kriging estimate
            results[i] = float(lambda_ @ values)

        return results

    @staticmethod
    def _pairwise_distances(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        Haversine distances in km between all pairs in a (M,2) and b (N,2).
        Returns (M, N) array.
        """
        a = np.radians(a)
        b = np.radians(b)
        dlat = a[:, 0:1] - b[:, 0]      # (M, N)
        dlon = a[:, 1:2] - b[:, 1]
        sin2_lat = np.sin(dlat / 2) ** 2
        sin2_lon = np.sin(dlon / 2) ** 2
        cos_prod = np.cos(a[:, 0:1]) * np.cos(b[:, 0])
        h = sin2_lat + cos_prod * sin2_lon
        return 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))  # km


# ─────────────────────────────────────────────────────────────────────────────
# GeoJSON output
# ─────────────────────────────────────────────────────────────────────────────

def build_geojson_grid(
    lat_range: Tuple[float, float],
    lon_range: Tuple[float, float],
    grid_size: int,
    interpolated: Dict[str, np.ndarray],
) -> Dict:
    """
    Build a GeoJSON FeatureCollection from a grid of interpolated values.
    Each cell is a Point feature with properties for each weather parameter.
    The Leaflet PWA renders this as a heatmap overlay.
    """
    lats = np.linspace(lat_range[0], lat_range[1], grid_size)
    lons = np.linspace(lon_range[0], lon_range[1], grid_size)

    features = []
    idx = 0
    for lat in lats:
        for lon in lons:
            props = {param: float(vals[idx]) for param, vals in interpolated.items()}
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": props,
            })
            idx += 1

    return {"type": "FeatureCollection", "features": features}


# ─────────────────────────────────────────────────────────────────────────────
# Main — demo / CLI
# ─────────────────────────────────────────────────────────────────────────────

def demo():
    """Run a demo with synthetic node positions around IIT Mandi."""
    print("=== Spatial Kriging Demo (IIT Mandi region) ===\n")

    # Synthetic slave node positions (lat, lon) in Mandi valley area
    node_coords = np.array([
        [31.7754, 76.9861],   # Node 0 — IIT Mandi campus
        [31.7200, 76.9300],   # Node 1 — Lower valley
        [31.8100, 77.0500],   # Node 2 — East ridge
        [31.7600, 77.1000],   # Node 3 — Far east
        [31.8400, 76.9000],   # Node 4 — North hilltop
    ])

    # Synthetic sensor readings at each node
    node_readings = {
        "temperature":  np.array([28.5, 31.2, 24.1, 22.8, 19.3]),
        "humidity":     np.array([62.0, 71.5, 55.0, 58.2, 48.0]),
        "pressure":     np.array([1002.1, 1005.3, 998.7, 997.2, 994.8]),
        "pm25":         np.array([18.0, 35.4, 12.1, 9.8, 6.5]),
    }

    # Build Kriging model (precomputes A⁻¹ once)
    kriging = OrdinaryKriging(
        node_coords=node_coords,
        nugget=0.0,
        sill=1.0,
        range_km=15.0,
    )
    print(f"Nodes: {len(node_coords)}")
    print(f"Covariance matrix A precomputed ({kriging.N+1}×{kriging.N+1})")

    # Define interpolation grid
    lat_range = (31.70, 31.85)
    lon_range = (76.88, 77.12)
    grid_size = 20   # 20×20 = 400 grid points

    lats = np.linspace(lat_range[0], lat_range[1], grid_size)
    lons = np.linspace(lon_range[0], lon_range[1], grid_size)
    grid_lat, grid_lon = np.meshgrid(lats, lons)
    query_coords = np.column_stack([grid_lat.ravel(), grid_lon.ravel()])

    print(f"\nInterpolating {len(query_coords)} grid points ({grid_size}×{grid_size})...")

    # Interpolate each parameter
    interpolated = {}
    for param, values in node_readings.items():
        interpolated[param] = kriging.interpolate(query_coords, values)
        print(f"  {param}: min={interpolated[param].min():.2f}  "
              f"max={interpolated[param].max():.2f}  "
              f"mean={interpolated[param].mean():.2f}")

    # Build GeoJSON
    geojson = build_geojson_grid(lat_range, lon_range, grid_size, interpolated)
    print(f"\nGeoJSON: {len(geojson['features'])} features")

    # Save output
    out_path = "/Users/ariyanbhakat/Desktop/Dp/master/kriging/heatmap_demo.geojson"
    with open(out_path, "w") as f:
        json.dump(geojson, f, indent=2)
    print(f"Saved: {out_path}")
    print("\n✅ Kriging demo complete.")


def main():
    parser = argparse.ArgumentParser(description="Spatial Kriging engine")
    parser.add_argument("--nodes", type=str, help="JSON file with node coords + readings")
    parser.add_argument("--grid-size", type=int, default=20)
    parser.add_argument("--range-km", type=float, default=15.0)
    parser.add_argument("--output", type=str, default="heatmap.geojson")
    args = parser.parse_args()

    if args.nodes:
        with open(args.nodes) as f:
            data = json.load(f)
        coords = np.array([[n["lat"], n["lon"]] for n in data["nodes"]])
        lats = [n["lat"] for n in data["nodes"]]
        lons = [n["lon"] for n in data["nodes"]]

        kriging = OrdinaryKriging(coords, range_km=args.range_km)
        query = np.array([[la, lo]
                          for la in np.linspace(min(lats), max(lats), args.grid_size)
                          for lo in np.linspace(min(lons), max(lons), args.grid_size)])
        interpolated = {}
        for param in data["nodes"][0]["readings"]:
            vals = np.array([n["readings"][param] for n in data["nodes"]])
            interpolated[param] = kriging.interpolate(query, vals)

        geojson = build_geojson_grid(
            (min(lats), max(lats)), (min(lons), max(lons)), args.grid_size, interpolated
        )
        with open(args.output, "w") as f:
            json.dump(geojson, f)
        print(f"Saved {args.output}")
    else:
        demo()


if __name__ == "__main__":
    main()
