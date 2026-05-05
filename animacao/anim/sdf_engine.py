"""Signed Distance Field engine for smooth mask interpolation."""
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from PIL import Image
from .config import EPOCHS, SDF_BLUR_SIGMA


def load_binary_mask(filepath):
    """Load a PNG with alpha channel as a binary mask (float32, 0 or 1)."""
    img = Image.open(filepath).convert('RGBA')
    return (np.array(img)[:, :, 3] > 30).astype(np.float32)


def mask_to_sdf(mask):
    """Convert binary mask to signed distance field.

    Returns: float32 array where negative = inside, positive = outside.
    This convention means threshold at 0 recovers the original boundary.
    """
    mask_bool = mask > 0.5
    if not np.any(mask_bool):
        return np.full(mask.shape, 1000.0, dtype=np.float32)
    if np.all(mask_bool):
        return np.full(mask.shape, -1000.0, dtype=np.float32)

    dist_outside = distance_transform_edt(~mask_bool).astype(np.float32)
    dist_inside = distance_transform_edt(mask_bool).astype(np.float32)

    sdf = dist_outside - dist_inside
    return sdf


def interpolate_sdf(sdf_a, sdf_b, t):
    """Linearly interpolate between two SDFs. t=0 gives sdf_a, t=1 gives sdf_b."""
    return sdf_a * (1.0 - t) + sdf_b * t


def sdf_to_smooth_mask(sdf, blur_sigma=SDF_BLUR_SIGMA):
    """Convert SDF back to a smooth mask (0-1) with soft edges."""
    mask = (sdf <= 0).astype(np.float32)
    if blur_sigma > 0:
        mask = gaussian_filter(mask, sigma=blur_sigma)
    return np.clip(mask, 0, 1)


def year_to_interpolation_params(year):
    """Given a year, find the two bracketing epochs and interpolation factor t.

    Returns: (epoch_idx_a, epoch_idx_b, t) where t in [0, 1].
    """
    ref_years = [e[2] for e in EPOCHS]

    if year <= ref_years[0]:
        return 0, 0, 0.0
    if year >= ref_years[-1]:
        n = len(ref_years) - 1
        return n, n, 0.0

    for i in range(len(ref_years) - 1):
        if ref_years[i] <= year <= ref_years[i + 1]:
            span = ref_years[i + 1] - ref_years[i]
            t = (year - ref_years[i]) / span
            return i, i + 1, t

    return 0, 0, 0.0


def compute_all_sdfs(masks):
    """Pre-compute SDFs for a list of binary masks."""
    return [mask_to_sdf(m) for m in masks]


def get_mask_for_year(sdfs, year):
    """Get a smooth interpolated mask for any year."""
    idx_a, idx_b, t = year_to_interpolation_params(year)
    if idx_a == idx_b:
        return sdf_to_smooth_mask(sdfs[idx_a])

    interpolated = interpolate_sdf(sdfs[idx_a], sdfs[idx_b], t)
    return sdf_to_smooth_mask(interpolated)


def get_epoch_color_mask(edif_sdfs, year):
    """Get per-pixel epoch color assignment for a given year.

    Each pixel gets the color of the epoch when it first appeared.
    Pixels appearing during interpolation receive the color of the NEXT epoch.

    Returns:
        color_indices: int array, values 0..N-1 indicating epoch color.
        combined_mask: float32 array (0-1), the smooth combined edificado mask.
    """
    idx_a, idx_b, t = year_to_interpolation_params(year)

    h, w = edif_sdfs[0].shape
    color_indices = np.full((h, w), -1, dtype=np.int32)

    # All epochs that are fully in the past
    for i in range(idx_a + 1):
        epoch_mask = (edif_sdfs[i] <= 0)
        color_indices[epoch_mask] = i

    # If we're interpolating between idx_a and idx_b
    if idx_a != idx_b and t > 0:
        interpolated = interpolate_sdf(edif_sdfs[idx_a], edif_sdfs[idx_b], t)
        current_mask = (interpolated <= 0)
        prev_mask = (edif_sdfs[idx_a] <= 0)
        new_pixels = current_mask & ~prev_mask
        color_indices[new_pixels] = idx_b
        # Reuse interpolated SDF for smooth mask
        combined_mask = sdf_to_smooth_mask(interpolated)
    else:
        combined_mask = sdf_to_smooth_mask(edif_sdfs[idx_a])

    return color_indices, combined_mask
