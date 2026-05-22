from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_TILE_URL_TEMPLATE = os.environ.get(
    "MAP_TILE_URL_TEMPLATE",
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
)
DEFAULT_TILE_SUBDOMAINS = tuple(
    sd for sd in os.environ.get("MAP_TILE_SUBDOMAINS", "").split(",") if sd
) or ("a", "b", "c")


@dataclass(frozen=True)
class MapLayer:
    key: str
    label: str
    tile_url_template: str
    subdomains: tuple[str, ...] = ()
    preview_url: str | None = None
    attribution: str | None = None


DEFAULT_MAP_LAYER = MapLayer(
    key="",
    label="Backend default (MAP_TILE_URL_TEMPLATE)",
    tile_url_template=DEFAULT_TILE_URL_TEMPLATE,
    subdomains=DEFAULT_TILE_SUBDOMAINS,
)

MAP_LAYERS: tuple[MapLayer, ...] = (
    DEFAULT_MAP_LAYER,
    MapLayer(
        key="osm",
        label="OpenStreetMap (Standard)",
        tile_url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        preview_url="https://tile.openstreetmap.org/12/654/1582.png",
        attribution="OpenStreetMap contributors",
    ),
    MapLayer(
        key="cyclosm",
        label="CyclOSM",
        tile_url_template="https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
        subdomains=("a", "b", "c"),
        preview_url="https://a.tile-cyclosm.openstreetmap.fr/cyclosm/12/654/1582.png",
        attribution="CyclOSM and OpenStreetMap contributors",
    ),
    MapLayer(
        key="opentopomap",
        label="OpenTopoMap (Topo)",
        tile_url_template="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        subdomains=("a", "b", "c"),
        preview_url="https://a.tile.opentopomap.org/12/654/1582.png",
        attribution="OpenTopoMap and OpenStreetMap contributors",
    ),
)

TILE_PROVIDERS = {layer.key: layer for layer in MAP_LAYERS if layer.key}


def resolve_tile_provider(tile_type: str | None) -> tuple[str, tuple[str, ...]]:
    if not tile_type:
        return DEFAULT_TILE_URL_TEMPLATE, DEFAULT_TILE_SUBDOMAINS
    key = tile_type.lower()
    provider = TILE_PROVIDERS.get(key)
    if not provider:
        valid = ", ".join(sorted(TILE_PROVIDERS))
        raise ValueError(f"tile_type must be one of: {valid}")
    return provider.tile_url_template, provider.subdomains


def frontend_map_layers() -> list[dict[str, str]]:
    layers: list[dict[str, str]] = []
    for layer in MAP_LAYERS:
        payload = {
            "key": layer.key,
            "value": layer.key,
            "label": layer.label,
        }
        if layer.preview_url:
            payload["preview_url"] = layer.preview_url
        if layer.attribution:
            payload["attribution"] = layer.attribution
        layers.append(payload)
    return layers
