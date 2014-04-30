# -*- coding: utf-8 -*-
from .node import Node


class Entity(Node):
    def __init__(self):
        self.parent = None
        self.kids = []
        self.properties = []

