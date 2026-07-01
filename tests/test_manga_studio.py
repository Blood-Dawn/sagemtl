"""Studio model tests: text layers + scanlation cleanup ops (deterministic, no Qt)."""

from __future__ import annotations

import numpy as np

from sagemtl_desktop.core.manga.models import TextRegion
from sagemtl_desktop.core.manga.studio import StudioModel, TextLayer


def _page(color=(255, 255, 255), size=(120, 160)):
    return np.full((size[1], size[0], 3), color, np.uint8)


def test_text_layer_round_trip():
    layer = TextLayer(text="Hi", x=1, y=2, width=30, height=20, color=(10, 20, 30), align="left")
    restored = TextLayer.from_dict(layer.to_dict())
    assert restored.text == "Hi"
    assert restored.color == (10, 20, 30)
    assert restored.align == "left"


def test_from_regions_builds_layers_from_translations():
    regions = [
        TextRegion(box=(0, 0, 40, 20), cls="text_bubble", target_text="Hello"),
        TextRegion(box=(0, 0, 40, 20), cls="text_free", target_text=""),     # empty -> skipped
        TextRegion(box=(0, 0, 40, 20), cls="bubble", target_text="ignored"),  # non-text -> skipped
    ]
    model = StudioModel.from_regions(_page(), regions)
    assert len(model.layers) == 1
    assert model.layers[0].text == "Hello"


def test_render_draws_text_over_page():
    model = StudioModel(_page())
    model.add_layer(TextLayer(text="Hi there", x=10, y=10, width=100, height=40))
    rendered = model.render()
    assert rendered.shape == model.base.shape
    assert not np.array_equal(rendered, model.base)  # text was drawn


def test_render_layer_is_box_sized_rgba():
    model = StudioModel(_page())
    layer = TextLayer(text="X", x=0, y=0, width=50, height=30)
    arr = np.asarray(model.render_layer(layer))
    assert arr.shape == (30, 50, 4)


def test_apply_levels():
    model = StudioModel(_page((128, 128, 128)))
    model.apply_levels(black=128, white=255, gamma=1.0)
    assert int(model.base.max()) == 0  # 128 maps to the new black point


def test_inpaint_mask_removes_painted_ink():
    page = _page((255, 255, 255))
    page[70:74, 20:140] = 0  # dark line
    model = StudioModel(page)
    mask = np.zeros(page.shape[:2], np.uint8)
    mask[66:78, 16:144] = 255
    model.inpaint_mask(mask)
    assert int(model.base[70:74, 20:140].min()) > 150  # line erased


def test_clone_stamp_copies_patch():
    page = _page((255, 255, 255))
    page[0:10, 0:10] = (255, 0, 0)  # red source patch
    model = StudioModel(page)
    model.clone_stamp(0, 0, 50, 50, 10, 10)
    assert tuple(int(c) for c in model.base[55, 55]) == (255, 0, 0)


def test_fill_rect():
    model = StudioModel(_page((255, 255, 255)))
    model.fill_rect(10, 10, 20, 20, (0, 0, 0))
    assert int(model.base[15, 15].max()) == 0


def test_despeckle_preserves_shape():
    rng = np.random.RandomState(0)
    model = StudioModel(rng.randint(0, 256, (60, 60, 3), dtype=np.uint8))
    model.despeckle(3)
    assert model.base.shape == (60, 60, 3)


def test_reset_image_restores_original():
    model = StudioModel(_page((255, 255, 255)))
    model.fill_rect(0, 0, 60, 60, (0, 0, 0))
    assert int(model.base.min()) == 0
    model.reset_image()
    assert int(model.base.min()) == 255
