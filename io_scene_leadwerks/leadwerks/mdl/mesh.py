# -*- coding: utf-8 -*-
from . import constants
from .entity import Entity


class Mesh(Entity):
    def __init__(self):
        self.surfaces = []

