"""Unveränderliche Gerätewerte; keine HTTP-, ORM- oder Übersetzungsabhängigkeit."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceValues:
    name: str
    manufacturer: str
    model: str


@dataclass(frozen=True)
class Device:
    id: int
    name: str
    manufacturer: str
    model: str


@dataclass(frozen=True)
class DevicePage:
    items: tuple[Device, ...]
    total: int
    snapshot: int
    offset: int


@dataclass(frozen=True)
class Image:
    id: str
    filename: str
    width: int
    height: int


@dataclass(frozen=True)
class ImagePage:
    items: tuple[Image, ...]
    total: int
    offset: int
