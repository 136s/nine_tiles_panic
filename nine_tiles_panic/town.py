#!/usr/bin/env python

from __future__ import annotations

import collections
import copy
from typing import Dict, Generator, List, Union

import networkx as nx
from networkx.utils import pairwise

from nine_tiles_panic import config
from nine_tiles_panic.onroad import Agent, Alien, Hamburger
from nine_tiles_panic.tile import Road, TileFace, Tile

LEN_SIDE = config.LEN_SIDE
NUM_TILE = config.NUM_TILE
NUM_THEME = config.NUM_THEME


class Path:
    """ Path クラス

    町の道のクラス
    町を作った時に、タイルの道を繋げて得点計算するために使う

    Attributes:
        left_end (int): Path の始点（左端）
        right_end (int): Path の終点（右端）
        length (int): タイル1枚を長さ1として数えたときの道の長さ
        objects (List[Union[Agent, Alien, Hamburger]]): 始点から終点までの\
            道上のエージェント・宇宙人・ハンバーガーのリスト
    """

    def __init__(self, path_graph: nx.Graph) -> None:
        end_nodes = set(Town.OUTER_EDGES) & set(path_graph.nodes)
        self.left_end: int = min(end_nodes)
        self.right_end: int = max(end_nodes)
        self.length: int = path_graph.number_of_edges()

        # path にいる Agent, Alien, Hamburger をセット
        self.objects: List[Union[Agent, Alien, Hamburger]] = []
        path_order = nx.shortest_path(
            path_graph, source=self.left_end, target=self.right_end
        )
        for i, j in pairwise(path_order):
            obj = path_graph[i][j]["object"]
            if obj is not None:
                if type(obj) == Hamburger:
                    self.objects.append(obj)
                elif type(obj) in (Agent, Alien):
                    if obj.get_face() == i:
                        self.objects.append(obj.set_dir("left"))
                    elif obj.get_face() == j:
                        self.objects.append(obj.set_dir("right"))

    def get_objects(self) -> List[Union[Agent, Alien, Hamburger]]:
        return self.objects

    def get_length(self) -> int:
        return self.length

    def check_food_chain(self) -> Path:
        """エージェント・宇宙人・ハンバーガーの捕獲・捕食関係を登録"""
        free_agent_left = None
        free_agent_right = None
        free_alien_left = None
        free_alien_right = None
        hangry_alien_left = None
        hangry_alien_right = None
        free_hamburger = None
        for i, obj in enumerate(self.objects):
            if type(obj) == Agent:
                if obj.get_dir() == "left":
                    # 左に宇宙人が居るか判定
                    free_alien = None
                    if (free_alien_left is not None) and (free_alien_right is not None):
                        free_alien = max(free_alien_left, free_alien_right)
                    elif free_alien_left is not None:
                        free_alien = free_alien_left
                    elif free_alien_right is not None:
                        free_alien = free_alien_right
                    # 居たら捕まえる、居なかったらエージェント登録
                    if free_alien is not None:
                        obj.capture(free_alien)
                        self.objects[free_alien].captured(i)
                        # 捕まえた後処理
                        if free_alien_left == free_alien:
                            free_alien_left = None
                        elif free_alien_right == free_alien:
                            free_alien_right = None
                    else:
                        free_agent_left = i  # noqa: F841
                elif obj.get_dir() == "right":
                    free_agent_right = i
            if type(obj) == Alien:
                # 左に右向きのエージェントが居たら捕まる
                if free_agent_right is not None:
                    self.objects[free_agent_right].capture(i)
                    obj.captured(free_agent_right)
                    free_agent_right = None
                # 左に右向きのエージェントが居なかったら宇宙人登録
                else:
                    if obj.get_dir() == "left":
                        free_alien_left = i
                    elif obj.get_dir() == "right":
                        free_alien_right = i
                # 左向きで左にハンバーガーあったら食べる、それ以外は空腹登録
                if obj.get_dir() == "left":
                    if free_hamburger is not None:
                        obj.eat(free_hamburger)
                        self.objects[free_hamburger].eaten(i)
                        free_hamburger = None
                    else:
                        hangry_alien_left = i  # noqa: F841
                elif obj.get_dir() == "right":
                    hangry_alien_right = i
            if type(obj) == Hamburger:
                # 左に右向きの空腹宇宙人が居たら食べられる
                if hangry_alien_right is not None:
                    self.objects[hangry_alien_right].eat(i)
                    obj.eaten(hangry_alien_right)
                # 宇宙人が居ても居なくてもハンバーガー登録
                free_hamburger = i
        return self


class Town:
    """ Town クラス

    町のクラス
    Tile の position は以下の通り
        012
        345
        678
    Path の辺の番号は以下の通り
          00  04  08
        01  03  07  11
          02  06  10
        13  15  19  23
          14  18  22
        25  27  31  35
          26  30  34

    Attributes:
        left_end (int): Path の始点（左端）
        right_end (int): Path の終点（右端）
        length (int): タイル1枚を長さ1として数えたときの道の長さ
        objects (List[Union[Agent, Alien, Hamburger]]): 始点から終点までの\
            道上のエージェント・宇宙人・ハンバーガーのリスト
    """

    # 町の外周の Path の辺の番号
    OUTER_EDGES = [0, 4, 8, 1, 11, 13, 23, 25, 35, 26, 30, 34]
    # 町の外周以外の Path の辺の番号
    INNER_EDGES = [3, 7, 2, 6, 10, 15, 19, 14, 18, 22, 27, 31]

    def __init__(self, pattern: str = None, tiles: list = None) -> None:
        self.face: List[TileFace] = [None] * NUM_TILE
        self.making_failed: bool = False
        self.paths: List[Path] = []
        if pattern is not None:
            self.make(pattern, tiles)

    def get_face(self, position: int) -> TileFace:
        return self.face[position]

    def get_faces(self) -> list[TileFace]:
        return self.face

    def add_tile(
        self, position: int, tile: Tile, is_front: bool = True, angle: int = 0
    ):
        has_added = False
        adding_face = tile.get_face(is_front, angle)
        if self.get_face(position) is None:
            if self.can_add_tile(position, adding_face):
                self.face[position] = adding_face
                has_added = True
        if not has_added:
            self.making_failed = True
        return self

    def has_failed(self) -> bool:
        return self.making_failed

    def can_add_tile(self, position: int, adding_face: TileFace) -> bool:
        can_add = True
        neighbours = self.get_neighbour(position)
        if len(neighbours) != 0:
            for p, f in neighbours.items():
                # 隣接予定 TileFace と 道あり/あり か なし/なし なら True
                is_good_connection = True
                # 置きたい TileFace -> 隣接予定の TileFace の方向で確認
                if f.does_have_road_edge(Town.get_connecting_edge(position, p)):
                    is_good_connection = not is_good_connection
                # 隣接予定の TileFace -> 置きたい TileFace の方向で確認
                if adding_face.does_have_road_edge(
                    Town.get_connecting_edge(p, position)
                ):
                    is_good_connection = not is_good_connection
                if not is_good_connection:
                    can_add = False
                    break
        return can_add

    @classmethod
    def convert_edge(cls, e: int) -> int:
        return (
            e
            if (e in cls.OUTER_EDGES) or (e in cls.INNER_EDGES)
            else e - LEN_SIDE * 4 + 2
            if e % 4 == 0
            else e - 2
        )

    def __make_paths(self) -> None:
        """道の始点・終点番号を再マッピングして格納（閉路がある場合は中断）"""
        if not self.has_failed():
            town_roads = nx.Graph()  # 町中の道を格納
            town_roads.edges.data("object", default=None)
            for i in range(NUM_TILE):
                f = self.get_face(i)
                for r in f.get_roads():
                    # 番号を更新
                    initial_edge = self.convert_edge(i * 4 + r.get_initial_edge())
                    terminal_edge = self.convert_edge(i * 4 + r.get_terminal_edge())
                    if r.get_agent_face() is not None:
                        object = Agent(self.convert_edge(i * 4 + r.get_agent_face()))
                    elif r.get_alien_face() is not None:
                        object = Alien(self.convert_edge(i * 4 + r.get_alien_face()))
                    elif r.get_num_hamburger() > 0:
                        object = Hamburger()
                    else:
                        object = None
                    town_roads.add_edge(initial_edge, terminal_edge, object=object)
            # 繋がっている道それぞれについて閉路を確認して、閉路でなければ格納
            for road in nx.connected_components(town_roads):
                path_graph = copy.deepcopy(town_roads.subgraph(road))
                try:
                    nx.find_cycle(path_graph)
                    self.making_failed = True
                    break
                except nx.NetworkXNoCycle:
                    self.paths.append(Path(path_graph).check_food_chain())

    def get_paths(self) -> List[Path]:
        return self.paths

    def get_roads(self) -> Generator[Road, None, None]:
        for face in self.get_faces():
            for road in face.get_roads():
                yield road

    @classmethod
    def get_connecting_edge(cls, pos1: int, pos2: int) -> int:
        """pos2 のタイル edge の中で、pos1 のタイルと接してる edge を取得"""
        if pos2 in cls.get_neighbour_position(pos1):
            pos_diff = pos1 - pos2
            if pos_diff == -LEN_SIDE:
                return 0
            elif pos_diff == -1:
                return 1
            elif pos_diff == LEN_SIDE:
                return 2
            elif pos_diff == 1:
                return 3
        else:
            return None

    @classmethod
    def get_neighbour_position(cls, position: int) -> list[int]:
        if position == 0:
            return [1, 3]
        elif position == 1:
            return [0, 2, 4]
        elif position == 2:
            return [1, 5]
        elif position == 3:
            return [0, 4, 6]
        elif position == 4:
            return [1, 3, 5, 7]
        elif position == 5:
            return [2, 4, 8]
        elif position == 6:
            return [3, 7]
        elif position == 7:
            return [4, 6, 8]
        elif position == 8:
            return [5, 7]
        else:
            raise NotImplementedError("NUM_TILE = 9 is supported.")

    def get_neighbour(self, position: int) -> Dict[int, TileFace]:
        faces = {}
        for p in Town.get_neighbour_position(position):
            f = self.get_face(p)
            if f is not None:
                faces[p] = f
        return faces

    @classmethod
    def most_adjacent(cls, positions: list[int]) -> int:
        """positions にあるタイルの中で隣り合っている最大エリアのサイズを返す"""
        # タイルとその隣接関係を格納したグラフ
        posgraph = nx.Graph()
        posgraph.add_edges_from(
            (i * LEN_SIDE + j, pi * LEN_SIDE + j)
            for pi, i in pairwise(range(LEN_SIDE))
            for j in range(LEN_SIDE)
        )
        posgraph.add_edges_from(
            (i * LEN_SIDE + j, i * LEN_SIDE + pj)
            for i in range(LEN_SIDE)
            for pj, j in pairwise(range(LEN_SIDE))
        )
        return len(max(nx.connected_components(posgraph.subgraph(positions)), key=len))

    def make(self, pattern: str = "", tiles: list = None) -> None:
        """前 9 桁: 置くタイルの index、後 9 桁: 置き方（0-3: 表で角度、4-7: 裏で角度 +4）"""
        if len(pattern) == NUM_TILE * 2:
            if tiles is None:
                tiles = Tile.get_original()
            pattern = pattern.zfill(2 * NUM_TILE)
            for i in range(NUM_TILE):
                position = i
                tile = tiles[int(pattern[i])]
                is_front = int(pattern[i + NUM_TILE]) < 4
                angle = int(pattern[i + NUM_TILE]) % 4
                self.add_tile(position, tile, is_front, angle)
                if self.has_failed():
                    break
            if not self.has_failed():
                self.__make_paths()  # 町としての道を作成し、閉路の有無も判定
        else:
            raise NotImplementedError(
                "Pattern input is supported only for lengths of 2 or 18. \
                 But the length is "
                + str(len(self.object))
                + "."
            )

    def theme_point(self, no: int) -> int:
        """町と、お題カードの番号を入れると点数を返す"""
        point = 0

        # 宇宙人をつかまえた数が多い
        if no == 1:
            num_captured_alien = 0
            for path in self.get_paths():
                for obj in path.get_objects():
                    if type(obj) == Alien:
                        if not obj.is_free():
                            num_captured_alien += 1
            for face in self.get_faces():
                num_captured_alien += face.get_num_alien_offroad_captured()
            point = num_captured_alien

        # 2人のエージェントではさみうちにした宇宙人の数が多い
        elif no == 2:
            num_stuck_list = [0]  # はさみうちのエージェントペア毎の宇宙人の数
            for path in self.get_paths():
                # パス毎に変数初期化
                right_face_agent = False
                num_stuck_alien = 0
                for obj in path.get_objects():
                    # 右を向いてるエージェントが未発見だったら探索してフラグ立て
                    if not right_face_agent:
                        if type(obj) == Agent:
                            if obj.get_dir() == "right":
                                right_face_agent = True
                    # 右を向いてるエージェントがいて、左を向いてるエージェントが未発見だったら…
                    else:
                        # 宇宙人を数え上げ
                        if type(obj) == Alien:
                            num_stuck_alien += 1
                        # エージェントが居たら…
                        if type(obj) == Agent:
                            # 左向きだったら登録して初期化
                            if obj.get_dir() == "left":
                                num_stuck_list.append(num_stuck_alien)
                                right_face_agent = False
                            # どっち向きでも宇宙人は数え直し
                            num_stuck_alien = 0
            point = max(num_stuck_list)

        # となりあっている『犬がいるタイル』の数が多い
        elif no == 3:
            dog_exists = []
            for p, face in enumerate(self.get_faces()):
                if face.get_num_dog() > 0:
                    dog_exists.append(p)
            if len(dog_exists) > 0:
                point = self.most_adjacent(dog_exists)

        # 町を完成させるのが早い
        elif no == 4:
            point = 0

        # 道が長い
        elif no == 5:
            point = max([path.get_length() for path in self.get_paths()])

        # カーブの数が多い
        elif no == 6:
            num_curve = 0
            for road in self.get_roads():
                num_curve += road.is_curve()
            point = num_curve

        # 家の数が多い
        elif no == 7:
            num_house = 0
            for face in self.get_faces():
                num_house += face.get_num_house()
            point = num_house

        # 【宇宙人の数×ハンバーガーの数】が大きい
        elif no == 8:
            num_free_alien = 0
            num_hamburger = 0
            for path in self.get_paths():
                for obj in path.get_objects():
                    if type(obj) == Alien:
                        if obj.is_free():
                            num_free_alien += 1
                    elif type(obj) == Hamburger:
                        num_hamburger += 1
            point = num_free_alien * num_hamburger

        # エージェントの数が多い
        elif no == 9:
            num_agent = 0
            for face in self.get_faces():
                num_agent += face.get_num_agent()
            point = num_agent

        # 道の本数が多い
        elif no == 10:
            point = len(self.get_paths())

        # 『道のないタイル』の数が多い
        elif no == 11:
            num_no_roads = 0
            for face in self.get_faces():
                num_no_roads += len(face.get_roads()) == 0
            point = num_no_roads

        # 犬の数が多い
        elif no == 12:
            num_dog = 0
            for face in self.get_faces():
                num_dog += face.get_num_dog()
            point = num_dog

        # 同じ長さの道の本数が多い
        elif no == 13:
            point = max(
                collections.Counter(
                    [path.get_length() for path in self.get_paths()]
                ).values()
            )

        # ひとつの道にいるエージェントの数が多い
        elif no == 14:
            num_agent_list = [0]
            for path in self.get_paths():
                num_agent = 0
                for obj in path.get_objects():
                    if type(obj) == Agent:
                        num_agent += 1
                num_agent_list.append(num_agent)
            point = max(num_agent_list)

        # 道の本数が少ない
        elif no == 15:
            point = -len(self.get_paths())

        # 1匹の宇宙人が向いている方向にあるハンバーガーの数が多い
        elif no == 16:
            num_hamburger_list = [0]
            for path in self.get_paths():
                hamburger_in_path = 0
                right_face_alien = False
                for obj in path.get_objects():
                    if type(obj) == Hamburger:
                        hamburger_in_path += 1
                    elif type(obj) == Alien:
                        if obj.is_free():
                            # 右を向いてる宇宙人が居たらここまでのハンバーガーを記録
                            if right_face_alien:
                                num_hamburger_list.append(hamburger_in_path)
                                hamburger_in_path = 0
                                # 左向きの時に右向き宇宙人をリセットするだけ（数は記録されている）
                                if obj.get_dir() == "left":
                                    right_face_alien = False
                            else:
                                if obj.get_dir() == "right":
                                    right_face_alien = True
                                # 右を向いてる宇宙人が居なくても、今回が左向きだったらここまでのハンバーガーを記録
                                elif obj.get_dir() == "left":
                                    num_hamburger_list.append(hamburger_in_path)
                                # 宇宙人が居たらハンバーガーはリセット
                                hamburger_in_path = 0
                # そのパスでの探索を終えた時に、右向き宇宙人の右に居たハンバーガーを記録
                if right_face_alien:
                    num_hamburger_list.append(hamburger_in_path)
            point = max(num_hamburger_list)

        # 【UFO の数×宇宙人の数】が多い
        elif no == 17:
            num_ufo = 0
            for face in self.get_faces():
                num_ufo += face.get_num_ufo()
            num_free_alien = 0
            for path in self.get_paths():
                for obj in path.get_objects():
                    if type(obj) == Alien:
                        if obj.is_free():
                            num_free_alien += 1
            point = num_ufo * num_free_alien

        # ひとつの道でエージェントの方向を向いている宇宙人の数が多い
        elif no == 18:
            num_running_alien_list = [0]
            for path in self.get_paths():
                agent_exists = False
                num_right_face_alien = 0
                num_left_face_alien = 0
                for obj in path.get_objects():
                    if type(obj) == Agent:
                        # エージェントが既にいたらそこまでの左向き宇宙人の数を格納
                        if agent_exists:
                            num_running_alien_list.append(num_left_face_alien)
                        # ここまでの右向き宇宙人の数を格納
                        num_running_alien_list.append(num_right_face_alien)
                        agent_exists = True
                        num_right_face_alien = 0
                        num_left_face_alien = 0
                    elif type(obj) == Alien:
                        if obj.get_dir() == "right":
                            num_right_face_alien += 1
                        elif obj.get_dir() == "left":
                            num_left_face_alien += 1
                # パスの右端まで来たら左向きの宇宙人の数を格納
                if agent_exists:
                    num_running_alien_list.append(num_left_face_alien)
            point = max(num_running_alien_list)

        # ひとつの道にいる宇宙人の数が多い
        elif no == 19:
            num_free_alien_list = [0]
            for path in self.get_paths():
                num_free_alien = 0
                for obj in path.get_objects():
                    if type(obj) == Alien:
                        if obj.is_free():
                            num_free_alien += 1
                num_free_alien_list.append(num_free_alien)
            point = max(num_free_alien_list)

        # 町にある【エージェント+宇宙人+ハンバーガー】の組み合わせの数が多い
        elif no == 20:
            num_seq = 0
            for path in self.get_paths():
                # 右向きと左向きの組合せの並びで、一番右にある obj クラスを格納
                right_seq_end = ""
                left_seq_end = ""
                for obj in path.get_objects():
                    # 右向きを判定
                    if right_seq_end == "Agent":
                        if type(obj) == Alien:
                            if obj.get_dir() == "right":
                                right_seq_end = "Alien"
                        if right_seq_end != "Alien":
                            right_seq_end = ""
                    elif right_seq_end == "Alien":
                        if type(obj) == Hamburger:
                            num_seq += 1
                        right_seq_end = ""
                    if right_seq_end == "":
                        if type(obj) == Agent:
                            if obj.get_dir() == "right":
                                right_seq_end = "Agent"
                    # 左向きを判定
                    if left_seq_end == "Hamburger":
                        if type(obj) == Alien:
                            if obj.get_dir() == "left":
                                left_seq_end = "Alien"
                        if left_seq_end != "Alien":
                            left_seq_end = ""
                    elif left_seq_end == "Alien":
                        if type(obj) == Agent:
                            if obj.get_dir() == "left":
                                num_seq += 1
                        left_seq_end = ""
                    if left_seq_end == "":
                        if type(obj) == Hamburger:
                            left_seq_end = "Hamburger"
            point = num_seq

        # となりあっている『宇宙人がいないタイル』の数が多い
        elif no == 21:
            alien_exists = []
            for p, face in enumerate(self.get_faces()):
                if not face.alien_exist():
                    alien_exists.append(p)
            if len(alien_exists) > 0:
                point = self.most_adjacent(alien_exists)

        # となりあっている『市民がいるタイル』の数が多い
        elif no == 22:
            citizen_exists = []
            for p, face in enumerate(self.get_faces()):
                if face.get_num_citizen() > 0:
                    citizen_exists.append(p)
            if len(citizen_exists) > 0:
                point = self.most_adjacent(citizen_exists)

        # となりあっている『家があるタイル』の数が多い
        elif no == 23:
            house_exists = []
            for p, face in enumerate(self.get_faces()):
                if face.get_num_house() > 0:
                    house_exists.append(p)
            if len(house_exists) > 0:
                point = self.most_adjacent(house_exists)

        # 【市民1人 + 犬1匹】のペアの数が多い
        elif no == 24:
            num_citizen = 0
            num_dog = 0
            for face in self.get_faces():
                num_citizen += face.get_num_citizen()
                num_dog += face.get_num_dog()
            point = min(num_citizen, num_dog)

        # 女の子の数が多い
        elif no == 25:
            num_girl = 0
            for face in self.get_faces():
                num_girl += face.get_num_girl()
            point = num_girl

        # 男の子の数が多い
        elif no == 26:
            num_boy = 0
            for face in self.get_faces():
                num_boy += face.get_num_boy()
            point = num_boy

        return point

    def get_theme_point(self, is_print: bool = False) -> List[int]:
        points = []
        themes = [
            "宇宙人をつかまえた数が多い",
            "2人のエージェントではさみうちにした宇宙人の数が多い",
            "となりあっている『犬がいるタイル』の数が多い",
            "町を完成させるのが早い",
            "道が長い",
            "カーブの数が多い",
            "家の数が多い",
            "【宇宙人の数×ハンバーガーの数】が大きい",
            "エージェントの数が多い",
            "道の本数が多い",
            "『道のないタイル』の数が多い",
            "犬の数が多い",
            "同じ長さの道の本数が多い",
            "ひとつの道にいるエージェントの数が多い",
            "道の本数が少ない",
            "1匹の宇宙人が向いている方向にあるハンバーガーの数が多い",
            "【UFO の数×宇宙人の数】が多い",
            "ひとつの道でエージェントの方向を向いている宇宙人の数が多い",
            "ひとつの道にいる宇宙人の数が多い",
            "町にある【エージェント+宇宙人+ハンバーガー】の組み合わせの数が多い",
            "となりあっている『宇宙人がいないタイル』の数が多い",
            "となりあっている『市民がいるタイル』の数が多い",
            "となりあっている『家があるタイル』の数が多い",
            "【市民1人 + 犬1匹】のペアの数が多い",
            "女の子の数が多い",
            "男の子の数が多い",
        ]
        for theme in range(NUM_THEME):
            points.append(self.theme_point(theme + 1))
        if is_print:
            for i, point in enumerate(points):
                print(i + 1, themes[i], point)
        return points
