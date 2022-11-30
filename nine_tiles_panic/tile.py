#!/usr/bin/env python

from __future__ import annotations

import copy
from typing import List, Optional


class Road:
    """Road クラス

    タイルの道のクラス
    辺番号は以下の通り
         0
        1 3
         2

    Attributes:
        initial_edge (int): 始点の辺番号 (0-3)
        terminal_edge (int): 終点の辺番号 (0-3)
        agent_face (int): エージェントの向いてる方向の辺番号 (0-3)
        alien_face (int): 宇宙人の向いてる方向の辺番号 (0-3)
        num_hamburger (int): ハンバーガーの向いてる方向の辺番号 (0-3)
    """

    def __init__(
        self,
        initial_edge: int,
        terminal_edge: int,
        agent_face: int = None,
        alien_face: int = None,
        num_hamburger: int = 0,
    ) -> None:
        self.initial_edge: int = initial_edge
        self.terminal_edge: int = terminal_edge
        self.agent_face: int = agent_face
        self.alien_face: int = alien_face
        self.num_hamburger: int = num_hamburger

    def __str__(self) -> str:
        return ", ".join(map(str, self.get_edges()))

    def __repr__(self) -> str:
        return self.__str__()

    def get_initial_edge(self) -> int:
        return self.initial_edge

    def get_terminal_edge(self) -> int:
        return self.terminal_edge

    def get_edges(self, angle: int = 0) -> list[int]:
        if angle != 0:
            self.rotate(angle)
        return [self.get_initial_edge(), self.get_terminal_edge()]

    def rotate(self, angle: int = 0) -> None:
        if angle != 0:
            self.initial_edge = (self.initial_edge + angle) % 4
            self.terminal_edge = (self.terminal_edge + angle) % 4
            if self.agent_face is not None:
                self.agent_face = (self.agent_face + angle) % 4
            if self.alien_face is not None:
                self.alien_face = (self.alien_face + angle) % 4

    def is_curve(self) -> bool:
        return bool((self.get_initial_edge() - self.get_terminal_edge()) % 2)

    def get_agent_face(self) -> Optional[int]:
        return self.agent_face

    def get_alien_face(self) -> Optional[int]:
        return self.alien_face

    def get_num_agent(self) -> int:
        return int(self.get_agent_face() is not None)

    def get_num_alien(self) -> int:
        return int(self.get_alien_face() is not None)

    def get_num_hamburger(self) -> int:
        return self.num_hamburger


class TileFace:
    """TileFace クラス

    タイルのおもて面・うら面のクラス

    Attributes:
        roads (List(Road)): Road のリスト
        num_dog (int): 犬の数
        num_girl (int): 市民（女の子）の数
        num_boy (int): 市民（男の子）の数
        num_house (int): 家の数
        num_ufo (int): UFO の数
        num_agent_offroad (int): 道の外にいるエージェントの数
        num_alien_offroad_captured (int): 道の外に居て捕まっている宇宙人の数
    """

    TILE_SIZE = 100

    def __init__(
        self,
        roads: List[Road] = [],
        num_dog: int = 0,
        num_girl: int = 0,
        num_boy: int = 0,
        num_house: int = 0,
        num_ufo: int = 0,
        num_agent_offroad: int = 0,
        num_alien_offroad_captured: int = 0,
    ) -> None:
        self.roads: List[Road] = roads
        self.num_dog: int = num_dog
        self.num_girl: int = num_girl
        self.num_boy: int = num_boy
        self.num_house: int = num_house
        self.num_ufo: int = num_ufo
        self.num_agent_offroad: int = num_agent_offroad
        self.num_alien_offroad_captured: int = num_alien_offroad_captured

    def __str__(self) -> str:
        return str(self.get_edges())

    def get_roads(self) -> List[Road]:
        return self.roads

    def get_edges(self, angle: int = 0) -> List[int]:
        return [r.get_edges(angle) for r in self.get_roads()]

    def get_num_house(self) -> int:
        return self.num_house

    def get_num_dog(self) -> int:
        return self.num_dog

    def get_num_girl(self) -> int:
        return self.num_girl

    def get_num_boy(self) -> int:
        return self.num_boy

    def get_num_citizen(self) -> int:
        return self.num_girl + self.num_boy

    def get_num_ufo(self) -> int:
        return self.num_ufo

    def get_num_agent(self) -> int:
        num_agent = self.num_agent_offroad
        for road in self.get_roads():
            num_agent += road.get_num_agent()
        return num_agent

    def alien_exist(self) -> bool:
        if self.num_alien_offroad_captured > 0:
            return True
        else:
            for road in self.get_roads():
                if road.get_num_alien() > 0:
                    return True
        return False

    def get_num_agent_offroad(self) -> int:
        return self.num_agent_offroad

    def get_num_alien_offroad_captured(self) -> int:
        return self.num_alien_offroad_captured

    def rotate(self, angle: int) -> TileFace:
        face = copy.deepcopy(self)
        for r in face.get_roads():
            r.rotate(angle)
        return face

    def does_have_road_edge(self, finding_edge: int) -> bool:
        return finding_edge in sum(self.get_edges(), [])


class Tile:
    """Tile クラス

    タイルのクラス

    Attributes:
        front_face (TileFace): タイルのおもて面
        back_face (TileFace): タイルのうら面
    """

    def __init__(self, front_face: TileFace, back_face: TileFace = None) -> None:
        self.front_face: TileFace = front_face
        self.back_face: TileFace = back_face

    def __get_front(self) -> TileFace:
        return self.front_face

    def __get_back(self) -> TileFace:
        return self.back_face

    def get_face(self, is_font: bool = True, angle: int = 0) -> TileFace:
        if is_font:
            return self.__get_front().rotate(angle)
        else:
            return self.__get_back().rotate(angle)

    @classmethod
    def get_original(cls) -> List[Tile]:
        tiles = [
            # Tile number: 0
            Tile(
                TileFace(num_dog=2, num_agent_offroad=1, num_alien_offroad_captured=1),
                TileFace(roads=[Road(0, 1, num_hamburger=1), Road(2, 3)], num_dog=1),
            ),
            # Tile number: 1
            Tile(
                TileFace(roads=[Road(0, 1, alien_face=1)], num_house=1),
                TileFace(roads=[Road(0, 2, agent_face=2), Road(1, 3)], num_dog=1),
            ),
            # Tile number: 2
            Tile(
                TileFace(roads=[Road(0, 3, agent_face=0), Road(1, 2)], num_boy=1),
                TileFace(roads=[Road(2, 3, num_hamburger=1)], num_dog=1),
            ),
            # Tile number: 3
            Tile(
                TileFace(num_house=2, num_ufo=1),
                TileFace(roads=[Road(0, 2, num_hamburger=1)], num_house=1),
            ),
            # Tile number: 4
            Tile(
                TileFace(roads=[Road(0, 3, alien_face=0), Road(1, 2)], num_house=1),
                TileFace(roads=[Road(0, 2), Road(1, 3, num_hamburger=1)], num_boy=1),
            ),
            # Tile number: 5
            Tile(
                TileFace(roads=[Road(0, 1, num_hamburger=1)], num_house=1),
                TileFace(num_girl=1, num_boy=1, num_ufo=1),
            ),
            # Tile number: 6
            Tile(
                TileFace(roads=[Road(0, 2, alien_face=0), Road(1, 3)], num_house=1),
                TileFace(roads=[Road(0, 2, agent_face=2)], num_girl=1),
            ),
            # Tile number: 7
            Tile(
                TileFace(roads=[Road(0, 3, num_hamburger=1), Road(1, 2)], num_dog=1),
                TileFace(roads=[Road(0, 2, alien_face=2)], num_boy=1),
            ),
            # Tile number: 8
            Tile(
                TileFace(roads=[Road(0, 1, agent_face=1)], num_girl=1),
                TileFace(roads=[Road(0, 2, num_hamburger=1)], num_dog=1),
            ),
        ]
        return tiles

    @classmethod
    def get_synonym(cls) -> List[Tile]:
        """道の形状だけに着目して一意なタイルを生成（おもて面のみ）"""
        tiles = [
            Tile(TileFace()),
            Tile(TileFace(roads=[Road(0, 1)])),
            Tile(TileFace(roads=[Road(0, 1), Road(2, 3)])),
            Tile(TileFace(roads=[Road(0, 2)])),
            Tile(TileFace(roads=[Road(0, 2), Road(1, 3)])),
        ]
        return tiles
