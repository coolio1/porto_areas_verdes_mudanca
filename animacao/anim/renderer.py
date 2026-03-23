"""Frame renderer for Porto urban growth animation."""
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from .config import (
    EPOCHS, EPOCH_COLORS, VEG_COLOR, RIVER_COLOR, BG_COLOR,
    MUNI_LINE_COLOR, ROAD_COLOR, PANEL_BG, PANEL_WIDTH,
    MAP_WIDTH, OUTPUT_HEIGHT, OUTPUT_WIDTH, TOPO_COLOR,
    TOPO_OUTLINE_COLOR, TOPONYMS, LON_MIN, LON_MAX,
    LAT_MIN, LAT_MAX, PIXEL_AREA_HA, YEAR_START, YEAR_END,
    LAYERS_DIR,
)
from .sdf_engine import (
    load_binary_mask, compute_all_sdfs, get_epoch_color_mask,
    get_mask_for_year,
)
import os


class AnimationRenderer:
    """Manages all layer data and renders individual frames."""

    def __init__(self):
        self._load_data()
        self._precompute()
        self._setup_fonts()

    def _load_data(self):
        """Load all mask layers and compute SDFs."""
        print('  Loading edificado masks...')
        self.edif_masks_raw = []
        for eid, label, year in EPOCHS:
            m = load_binary_mask(os.path.join(LAYERS_DIR, f'edif_{eid}.png'))
            self.edif_masks_raw.append(m)
            print(f'    {label}: {int(m.sum())} px')

        print('  Loading vegetation masks...')
        self.veg_masks_raw = []
        for eid, label, year in EPOCHS:
            v = load_binary_mask(os.path.join(LAYERS_DIR, f'veg_{eid}.png'))
            self.veg_masks_raw.append(v)

        print('  Loading municipality outline...')
        self.muni_raw = load_binary_mask(os.path.join(LAYERS_DIR, 'municipios.png'))

        # Optional layers
        rio_path = os.path.join(LAYERS_DIR, 'rio.png')
        if os.path.exists(rio_path):
            print('  Loading river mask...')
            self.rio_raw = load_binary_mask(rio_path)
        else:
            print('  River mask not found, skipping.')
            self.rio_raw = None

        roads_path = os.path.join(LAYERS_DIR, 'estradas.png')
        if os.path.exists(roads_path):
            print('  Loading roads...')
            img = Image.open(roads_path).convert('RGBA')
            self.roads_rgba_raw = np.array(img)
        else:
            print('  Roads not found, skipping.')
            self.roads_rgba_raw = None

        self.gee_h, self.gee_w = self.edif_masks_raw[0].shape

    def _precompute(self):
        """Pre-compute SDFs, resize layers to output, compute crop."""
        # Compute crop region from municipality extent (fallback to edificado union)
        crop_mask = self.muni_raw
        if not np.any(crop_mask > 0.5):
            print('  WARNING: municipios.png is empty, falling back to edificado union for crop.')
            crop_mask = np.zeros_like(self.edif_masks_raw[0])
            for m in self.edif_masks_raw:
                crop_mask = np.maximum(crop_mask, m)

        muni_rows = np.any(crop_mask > 0.5, axis=1)
        muni_cols = np.any(crop_mask > 0.5, axis=0)
        rmin, rmax = np.where(muni_rows)[0][[0, -1]]
        cmin, cmax = np.where(muni_cols)[0][[0, -1]]
        margin = 20
        self.rmin = max(0, rmin - margin)
        self.rmax = min(self.gee_h, rmax + margin)
        self.cmin = max(0, cmin - margin)
        self.cmax = min(self.gee_w, cmax + margin)

        crop_h = self.rmax - self.rmin
        crop_w = self.cmax - self.cmin

        # Scale to fit MAP_WIDTH x OUTPUT_HEIGHT
        scale_w = MAP_WIDTH / crop_w
        scale_h = OUTPUT_HEIGHT / crop_h
        self.scale = min(scale_w, scale_h)
        self.map_w = int(crop_w * self.scale)
        self.map_h = int(crop_h * self.scale)
        # Ensure even dimensions
        self.map_w += self.map_w % 2
        self.map_h += self.map_h % 2

        print(f'  Crop: {crop_w}x{crop_h}, Output map: {self.map_w}x{self.map_h}')

        # Helper: crop and resize a mask
        def prep(mask):
            cropped = mask[self.rmin:self.rmax, self.cmin:self.cmax]
            return cv2.resize(cropped, (self.map_w, self.map_h),
                              interpolation=cv2.INTER_LINEAR)

        # Pre-compute SDFs at output resolution
        print('  Computing edificado SDFs...')
        edif_prepped = [prep(m) for m in self.edif_masks_raw]
        self.edif_sdfs = compute_all_sdfs(edif_prepped)

        print('  Computing vegetation SDFs...')
        veg_prepped = [prep(v) for v in self.veg_masks_raw]
        self.veg_sdfs = compute_all_sdfs(veg_prepped)

        # Static layers at output resolution
        self.muni_out = prep(self.muni_raw)

        if self.rio_raw is not None:
            self.rio_out = prep(self.rio_raw)
        else:
            self.rio_out = None

        if self.roads_rgba_raw is not None:
            cropped = self.roads_rgba_raw[self.rmin:self.rmax, self.cmin:self.cmax]
            self.roads_out = cv2.resize(cropped, (self.map_w, self.map_h),
                                        interpolation=cv2.INTER_LINEAR)
        else:
            self.roads_out = None

        # Pre-compute municipality fill mask and vignette (static, not per-frame)
        from scipy.ndimage import binary_fill_holes, gaussian_filter
        muni_filled = binary_fill_holes(self.muni_out > 0.3).astype(np.float32)
        self.muni_vignette = gaussian_filter(muni_filled, sigma=8)

        # Pre-compute map padding offsets (center map in MAP_WIDTH if narrower)
        self.map_pad_left = (MAP_WIDTH - self.map_w) // 2
        self.map_pad_right = MAP_WIDTH - self.map_w - self.map_pad_left

        # Statistics from original resolution masks
        self.stats = []
        for i, (eid, label, year) in enumerate(EPOCHS):
            edif_ha = float(np.sum(self.edif_masks_raw[i] > 0.5)) * PIXEL_AREA_HA
            veg_ha = float(np.sum(self.veg_masks_raw[i] > 0.5)) * PIXEL_AREA_HA
            self.stats.append({'edif_ha': edif_ha, 'veg_ha': veg_ha, 'year': year})

        # Toponym pixel positions
        self.topo_pixels = []
        for name, lon, lat in TOPONYMS:
            px = (lon - LON_MIN) / (LON_MAX - LON_MIN) * self.gee_w
            py = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * self.gee_h
            px_out = int((px - self.cmin) * self.scale)
            py_out = int((py - self.rmin) * self.scale)
            if 0 <= px_out < self.map_w and 0 <= py_out < self.map_h:
                self.topo_pixels.append((name, px_out, py_out))

    def _setup_fonts(self):
        """Load fonts with fallbacks."""
        try:
            self.font_title = ImageFont.truetype("arialbd.ttf", 24)
            self.font_year = ImageFont.truetype("arialbd.ttf", 56)
            self.font_label = ImageFont.truetype("arial.ttf", 16)
            self.font_value = ImageFont.truetype("arialbd.ttf", 22)
            self.font_legend = ImageFont.truetype("arial.ttf", 14)
            self.font_small = ImageFont.truetype("arial.ttf", 12)
            self.font_topo = ImageFont.truetype("arialbd.ttf", 13)
            self.font_porto = ImageFont.truetype("arialbd.ttf", 36)
        except OSError:
            fallback = ImageFont.load_default()
            self.font_title = fallback
            self.font_year = fallback
            self.font_label = fallback
            self.font_value = fallback
            self.font_legend = fallback
            self.font_small = fallback
            self.font_topo = fallback
            self.font_porto = fallback

    def _interpolate_stat(self, key, year):
        """Interpolate a statistic for a given year."""
        from .sdf_engine import year_to_interpolation_params
        idx_a, idx_b, t = year_to_interpolation_params(year)
        if idx_a == idx_b:
            return self.stats[idx_a][key]
        val_a = self.stats[idx_a][key]
        val_b = self.stats[idx_b][key]
        # Smooth interpolation
        t_smooth = t * t * (3 - 2 * t)
        return val_a * (1 - t_smooth) + val_b * t_smooth

    def render_map(self, year):
        """Render the map portion of a frame for a given year.

        Returns: np.ndarray (map_h, map_w, 3) uint8 RGB
        """
        # Start with beige background
        frame = np.full((self.map_h, self.map_w, 3),
                        BG_COLOR, dtype=np.float32) / 255.0

        # Vegetation layer (olive, interpolated via SDF)
        veg_mask = get_mask_for_year(self.veg_sdfs, year)
        veg_alpha = veg_mask[:, :, np.newaxis] * 0.85
        veg_rgb = np.array(VEG_COLOR, dtype=np.float32) / 255.0
        frame = frame * (1 - veg_alpha) + veg_rgb * veg_alpha

        # Edificado with epoch colors
        color_indices, edif_combined = get_epoch_color_mask(self.edif_sdfs, year)
        for i, color in enumerate(EPOCH_COLORS):
            epoch_pixels = (color_indices == i)
            if not np.any(epoch_pixels):
                continue
            # Use combined mask for smooth alpha at edges
            layer_alpha = np.zeros((self.map_h, self.map_w), dtype=np.float32)
            layer_alpha[epoch_pixels] = edif_combined[epoch_pixels]
            layer_alpha = layer_alpha[:, :, np.newaxis] * 0.9
            color_rgb = np.array(color, dtype=np.float32) / 255.0
            frame = frame * (1 - layer_alpha) + color_rgb * layer_alpha

        # River (static, solid blue)
        if self.rio_out is not None:
            rio_alpha = np.clip(self.rio_out, 0, 1)[:, :, np.newaxis] * 0.95
            rio_rgb = np.array(RIVER_COLOR, dtype=np.float32) / 255.0
            frame = frame * (1 - rio_alpha) + rio_rgb * rio_alpha

        # Roads (static)
        if self.roads_out is not None:
            road_alpha = self.roads_out[:, :, 3:4].astype(np.float32) / 255.0
            road_rgb = self.roads_out[:, :, :3].astype(np.float32) / 255.0
            frame = frame * (1 - road_alpha) + road_rgb * road_alpha

        # Municipality outline
        muni_alpha = np.clip(self.muni_out, 0, 1)[:, :, np.newaxis] * 0.7
        muni_rgb = np.array(MUNI_LINE_COLOR, dtype=np.float32) / 255.0
        frame = frame * (1 - muni_alpha) + muni_rgb * muni_alpha

        # Fade outside municipality (uses precomputed vignette)
        vignette = self.muni_vignette[:, :, np.newaxis]
        bg_outside = np.array([0.90, 0.88, 0.84], dtype=np.float32)
        frame = frame * vignette + bg_outside * (1 - vignette)

        return np.clip(frame * 255, 0, 255).astype(np.uint8)

    def render_toponyms(self, map_img):
        """Add bold uppercase toponyms with outline to map image.

        Uses RGBA overlay for PORTO watermark semi-transparency.
        """
        pil_img = Image.fromarray(map_img).convert('RGBA')
        # Create transparent overlay for PORTO watermark
        overlay = Image.new('RGBA', pil_img.size, (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)

        # PORTO large centered (semi-transparent watermark)
        porto_text = "PORTO"
        bbox = draw_overlay.textbbox((0, 0), porto_text, font=self.font_porto)
        tw = bbox[2] - bbox[0]
        cx = self.map_w // 2 - tw // 2
        cy = self.map_h // 2 - 20
        draw_overlay.text((cx, cy), porto_text, font=self.font_porto,
                          fill=(255, 255, 255, 140),
                          stroke_width=3,
                          stroke_fill=(30, 30, 30, 100))

        # Composite overlay onto image
        pil_img = Image.alpha_composite(pil_img, overlay)

        # Draw toponyms (fully opaque, on final composited image)
        draw = ImageDraw.Draw(pil_img)
        for name, px, py in self.topo_pixels:
            draw.text((px, py), name, font=self.font_topo,
                      fill=TOPO_COLOR,
                      stroke_width=2,
                      stroke_fill=TOPO_OUTLINE_COLOR)

        return np.array(pil_img.convert('RGB'))

    def render_panel(self, year):
        """Render the side panel with stats, legend, progress bar.

        Returns: np.ndarray (map_h, PANEL_WIDTH, 3) uint8 RGB
        """
        panel = Image.new('RGB', (PANEL_WIDTH, self.map_h), PANEL_BG)
        draw = ImageDraw.Draw(panel, 'RGBA')
        pw = PANEL_WIDTH

        # Left separator line
        draw.line([(0, 0), (0, self.map_h)], fill=(60, 60, 65), width=2)

        # Title
        y = 30
        for line in ["CRESCIMENTO", "URBANO DO PORTO"]:
            bbox = draw.textbbox((0, 0), line, font=self.font_title)
            tw = bbox[2] - bbox[0]
            draw.text(((pw - tw) // 2, y), line,
                      fill=(230, 230, 230), font=self.font_title)
            y += 32
        y += 10

        # Separator
        draw.line([(30, y), (pw - 30, y)], fill=(60, 60, 65), width=1)
        y += 20

        # Year counter
        year_str = str(int(round(year)))
        bbox = draw.textbbox((0, 0), year_str, font=self.font_year)
        tw = bbox[2] - bbox[0]
        draw.text(((pw - tw) // 2, y), year_str,
                  fill=(255, 255, 255), font=self.font_year)
        y += 75

        # Progress bar (proportional to epoch year spans)
        bar_x = 30
        bar_w = pw - 60
        bar_h = 8
        ref_years = [e[2] for e in EPOCHS]
        total_span = ref_years[-1] - ref_years[0]

        # Background bar
        draw.rounded_rectangle([bar_x, y, bar_x + bar_w, y + bar_h],
                               radius=4, fill=(50, 50, 55))

        # Fill segments up to current year
        x_pos = bar_x
        for i in range(len(EPOCHS) - 1):
            seg_frac = (ref_years[i + 1] - ref_years[i]) / total_span
            seg_w = int(seg_frac * bar_w)
            # Use next epoch's color (consistent with pixel color rule)
            seg_color = EPOCH_COLORS[i + 1]
            if year >= ref_years[i + 1]:
                # Full segment
                draw.rectangle([x_pos, y, x_pos + seg_w, y + bar_h],
                               fill=seg_color)
            elif year > ref_years[i]:
                # Partial segment
                fill_frac = (year - ref_years[i]) / (ref_years[i + 1] - ref_years[i])
                fill_w = int(fill_frac * seg_w)
                draw.rectangle([x_pos, y, x_pos + fill_w, y + bar_h],
                               fill=seg_color)
            x_pos += seg_w

        # Current position marker
        if year >= ref_years[0]:
            marker_frac = min((year - ref_years[0]) / total_span, 1.0)
            marker_x = bar_x + int(marker_frac * bar_w)
            draw.ellipse([marker_x - 5, y - 3, marker_x + 5, y + bar_h + 3],
                         fill=(255, 255, 255))

        y += bar_h + 25

        # Separator
        draw.line([(30, y), (pw - 30, y)], fill=(60, 60, 65), width=1)
        y += 20

        # Legend
        draw.text((30, y), "LEGENDA", fill=(140, 140, 145), font=self.font_small)
        y += 20

        # Determine current epoch index
        current_epoch = 0
        for i, (_, _, ey) in enumerate(EPOCHS):
            if year >= ey:
                current_epoch = i

        for j, (eid, elabel, eyear) in enumerate(EPOCHS):
            alpha = 255 if j <= current_epoch else 80
            rect_y = y + j * 28
            draw.rounded_rectangle(
                [30, rect_y, 50, rect_y + 18],
                radius=3, fill=(*EPOCH_COLORS[j], alpha))
            text_color = (220, 220, 220) if j <= current_epoch else (90, 90, 95)
            draw.text((58, rect_y + 1), elabel,
                      fill=text_color, font=self.font_legend)

        y += len(EPOCHS) * 28 + 8

        # Vegetation in legend
        draw.rounded_rectangle([30, y, 50, y + 18], radius=3, fill=VEG_COLOR)
        draw.text((58, y + 1), "Vegeta\u00e7\u00e3o",
                  fill=(220, 220, 220), font=self.font_legend)
        y += 35

        # Separator
        draw.line([(30, y), (pw - 30, y)], fill=(60, 60, 65), width=1)
        y += 20

        # Statistics
        draw.text((30, y), "ESTAT\u00cdSTICAS",
                  fill=(140, 140, 145), font=self.font_small)
        y += 22

        edif_ha = self._interpolate_stat('edif_ha', year)
        veg_ha = self._interpolate_stat('veg_ha', year)

        draw.text((30, y), "\u00c1rea edificada",
                  fill=(170, 170, 175), font=self.font_label)
        y += 22
        val_str = f"{edif_ha:,.0f} ha".replace(',', ' ')
        draw.text((30, y), val_str, fill=(230, 230, 230), font=self.font_value)
        y += 34

        draw.text((30, y), "\u00c1rea de vegeta\u00e7\u00e3o",
                  fill=(170, 170, 175), font=self.font_label)
        y += 22
        val_str = f"{veg_ha:,.0f} ha".replace(',', ' ')
        draw.text((30, y), val_str, fill=(160, 200, 130), font=self.font_value)
        y += 34

        # Change since 1985
        if year > YEAR_START + 1:
            edif_change = edif_ha - self.stats[0]['edif_ha']
            veg_change = veg_ha - self.stats[0]['veg_ha']
            y += 5
            draw.text((30, y), "Varia\u00e7\u00e3o desde 1985",
                      fill=(140, 140, 145), font=self.font_small)
            y += 18
            sign_e = "+" if edif_change >= 0 else ""
            draw.text((30, y),
                      f"Edificado: {sign_e}{edif_change:,.0f} ha".replace(',', ' '),
                      fill=(192, 57, 43) if edif_change > 0 else (100, 200, 100),
                      font=self.font_legend)
            y += 18
            sign_v = "+" if veg_change >= 0 else ""
            draw.text((30, y),
                      f"Vegeta\u00e7\u00e3o: {sign_v}{veg_change:,.0f} ha".replace(',', ' '),
                      fill=(192, 57, 43) if veg_change < 0 else (100, 200, 100),
                      font=self.font_legend)

        # Footer
        draw.text((20, self.map_h - 50), "Fonte: Landsat (USGS/NASA)",
                  fill=(80, 80, 85), font=self.font_small)
        draw.text((20, self.map_h - 35), "NDVI \u2265 0.25 | 30m",
                  fill=(80, 80, 85), font=self.font_small)
        draw.text((20, self.map_h - 20), "JRC Global Surface Water",
                  fill=(80, 80, 85), font=self.font_small)

        return np.array(panel)

    def render_frame(self, year):
        """Render a complete frame (map + panel) for a given year.

        Returns: np.ndarray (OUTPUT_HEIGHT, OUTPUT_WIDTH, 3) uint8 RGB
        """
        # Map
        map_rgb = self.render_map(year)
        map_rgb = self.render_toponyms(map_rgb)

        # Panel
        panel_rgb = self.render_panel(year)

        # Compose: pad map to MAP_WIDTH (centered), then add panel
        frame = np.full((OUTPUT_HEIGHT, OUTPUT_WIDTH, 3), PANEL_BG, dtype=np.uint8)

        # Center map vertically and horizontally within its area
        pad_top = (OUTPUT_HEIGHT - self.map_h) // 2
        pad_left = self.map_pad_left

        # Fill map background with beige
        frame[:, :MAP_WIDTH] = np.array(BG_COLOR, dtype=np.uint8)

        # Place map centered
        if pad_top >= 0 and pad_left >= 0:
            frame[pad_top:pad_top + self.map_h,
                  pad_left:pad_left + self.map_w] = map_rgb

        # Place panel (always full height on the right)
        panel_resized = cv2.resize(panel_rgb, (PANEL_WIDTH, OUTPUT_HEIGHT),
                                   interpolation=cv2.INTER_LANCZOS4)
        frame[:, MAP_WIDTH:] = panel_resized

        return frame
