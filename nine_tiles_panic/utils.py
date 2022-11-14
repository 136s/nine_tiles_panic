#!/usr/bin/env python

import itertools
import math
import os
import re
import sqlite3
from typing import Generator, List, Tuple, Union

from PIL import Image, ImageDraw

import config
from tile import TileFace, Tile
from town import Town

LEN_SIDE = config.LEN_SIDE
NUM_TILE = config.NUM_TILE
OUT_FILENAME = config.OUT_FILENAME
OUT_DBNAME = config.OUT_DBNAME
NUM_THEME = config.NUM_THEME


class View:
    """View クラス

    オリジナルのタイルのおもて面・うら面や町を描画するクラス
    数字文字列を入れたら元画像で描画する

    Attributes:
        object (Union[str, TileFace, Town]): 描画したいタイルの面か町のインスタンス
        image (Image): 描画された Image
    """

    TILE_SIZE = 100
    TOWN_SIZE = TILE_SIZE * LEN_SIDE
    SCALE = 3 / 4  # 道の辺番号描画のスケール
    OFFSET = 0  # タイルの position 描画のオフセット割合
    ROAD_WIDTH = int(TILE_SIZE * 0.16)  # 疑似描画の道幅
    BG_COLOR = "#E6E7DD"
    ROAD_COLOR = "#FF799A"
    CHAR_COLOR = "#241917"

    def __init__(
        self,
        object: Union[str, TileFace, Town],
        does_display: bool = False,
        view_number: bool = False,
    ) -> None:
        self.object: Union[TileFace, Town] = object
        self.image: Image = None
        self.drawer: ImageDraw = None
        self.view_number = view_number

        # タイプ別に描画
        if type(self.object) == TileFace:
            self._draw_pseudo_tile_face()
        elif type(self.object) == Town:
            self._draw_pseudo_town()
        elif type(self.object) == str:
            if len(self.object) == 2:
                self._draw_real_tile_face()
            elif len(self.object) == NUM_TILE * 2:
                self._draw_real_town()
            else:
                raise NotImplementedError(
                    "Pattern input is supported only for lengths of 2 or 18. \
                     But the length is "
                    + str(len(self.object))
                    + "."
                )

        # 描画に成功して、希望すれば draw
        if does_display and self.get_image() is not None:
            self.draw()

    @staticmethod
    def pos_x(edge: int, scale: float = 1) -> int:
        return int(View.TILE_SIZE * (-math.sin((edge) * math.pi / 2) * scale + 1) / 2)

    @staticmethod
    def pos_y(edge: int, scale: float = 1) -> int:
        return int(View.TILE_SIZE * (-math.cos((edge) * math.pi / 2) * scale + 1) / 2)

    @staticmethod
    def pos_xy(edge: int, scale: float = 1) -> Tuple[int]:
        return (View.pos_x(edge, scale), View.pos_y(edge, scale))

    def tile_x(position: int, offset: float = 0) -> float:
        return View.TILE_SIZE * (position % LEN_SIDE + offset)

    def tile_y(position: int, offset: float = 0) -> float:
        return View.TILE_SIZE * (position // LEN_SIDE + offset)

    def tile_xy(position: int, offset: float = 0) -> Tuple[float]:
        return (View.tile_x(position, offset), View.tile_y(position, offset))

    def char_adj(coodinate: Tuple[float], len: int = 2) -> Tuple[float]:
        return (coodinate[0] - 3 * len, coodinate[1] - 6.5)

    def real_image(tile: int, is_front: bool) -> str:
        return "./data/imgs/tf{}{}.png".format(tile, is_front)

    def _set_drawer(self) -> None:
        self.drawer = ImageDraw.Draw(self.image)

    def _set_town_image(self) -> None:
        self.image = Image.new("RGB", (self.TOWN_SIZE, self.TOWN_SIZE), self.BG_COLOR)

    def _draw_roads(self) -> None:
        """タイル上の道を描画"""
        for road in self.object.get_roads():
            edges = road.get_edges()
            # 直線
            if abs(edges[0] - edges[1]) == 2:
                self.drawer.line(
                    (View.pos_xy(edges[0]), View.pos_xy(edges[1])),
                    fill=self.ROAD_COLOR,
                    width=self.ROAD_WIDTH,
                )
            # 曲線
            else:
                self.drawer.arc(
                    (
                        self.TILE_SIZE * (-0.5 + (3 in edges)) - 0.5 * self.ROAD_WIDTH,
                        self.TILE_SIZE * (-0.5 + (2 in edges)) - 0.5 * self.ROAD_WIDTH,
                        self.TILE_SIZE * (+0.5 + (3 in edges)) + 0.5 * self.ROAD_WIDTH,
                        self.TILE_SIZE * (+0.5 + (2 in edges)) + 0.5 * self.ROAD_WIDTH,
                    ),
                    start=0,
                    end=360,
                    fill=self.ROAD_COLOR,
                    width=self.ROAD_WIDTH,
                )

    def _draw_tile_objects(self) -> None:
        """タイル上のオブジェクトを描画"""
        contents = (
            "Dg" * self.object.get_num_dog()
            + "Gl" * self.object.get_num_girl()
            + "By" * self.object.get_num_boy()
            + "Hs" * self.object.get_num_house()
            + "Uf" * self.object.get_num_ufo()
            + "Ag" * self.object.get_num_agent_offroad()
            + "Al" * self.object.get_num_alien_offroad_captured()
        )
        self.drawer.text(
            View.char_adj((self.TILE_SIZE / 2, self.TILE_SIZE / 2), len(contents)),
            contents,
            fill=self.CHAR_COLOR,
        )
        for road in self.object.get_roads():
            if road is not None:
                agent = road.get_agent_face()
                if agent is not None:
                    self.drawer.text(
                        View.char_adj(View.pos_xy(agent, self.SCALE)),
                        "Ag",
                        fill=self.CHAR_COLOR,
                    )
                alien = road.get_alien_face()
                if alien is not None:
                    self.drawer.text(
                        View.char_adj(View.pos_xy(alien, self.SCALE)),
                        "Al",
                        fill=self.CHAR_COLOR,
                    )
                hamburger = road.get_num_hamburger()
                self.drawer.text(
                    View.char_adj(View.pos_xy(road.get_edges()[0], self.SCALE)),
                    "Hb" * hamburger,
                    fill=self.CHAR_COLOR,
                )

    def _draw_road_number(self) -> None:
        """タイルの道の辺番号を描画"""
        for edge in range(4):
            self.drawer.text(
                View.pos_xy(edge, self.SCALE), str(edge), fill=self.CHAR_COLOR
            )

    def _draw_path_number(self, position) -> None:
        """町の道の辺番号を描画"""
        for edge in range(4):
            self.drawer.text(
                View.char_adj(
                    (
                        View.tile_x(position) + View.pos_x(edge, self.SCALE),
                        View.tile_y(position) + View.pos_y(edge, self.SCALE),
                    ),
                    2,
                ),
                str(position * 4 + edge).zfill(2),
                fill=self.CHAR_COLOR,
            )

    def _draw_position_number(self, position) -> None:
        """タイルの位置番号を描画"""
        self.drawer.text(
            View.tile_xy(position, self.OFFSET),
            "[" + str(position) + "]",
            fill=self.CHAR_COLOR,
        )

    def _draw_pseudo_tile_face(self) -> None:
        """疑似タイル面を描画"""
        self.image = Image.new("RGB", (self.TILE_SIZE, self.TILE_SIZE), self.BG_COLOR)
        self._set_drawer()
        self._draw_roads()
        self._draw_tile_objects()
        if self.view_number:
            self._draw_road_number()

    def _draw_pseudo_town(self) -> None:
        """疑似町を描画"""
        self._set_town_image()
        for position, tileface in enumerate(self.object.get_faces()):
            self.image.paste(
                View(tileface, view_number=self.view_number).get_image(),
                View.tile_xy(position),
            )
            if self.view_number:
                self._set_drawer()
                self._draw_position_number(position)

    def _draw_real_tile_face(self) -> None:
        """タイル面を描画"""
        tile, direction = self.object
        is_front = str(1 - int(int(direction) < 4))
        angle = int(direction) % 4
        self.image = Image.open(View.real_image(tile, is_front)).rotate(angle * 90)

    def _draw_real_town(self) -> None:
        """町を描画"""
        self._set_town_image()
        for position in range(NUM_TILE):
            tile = self.object[position]
            direction = self.object[position + NUM_TILE]
            tileface = View(tile + direction).get_image()
            self.image.paste(tileface, View.tile_xy(position), tileface)
            if self.view_number:
                self._set_drawer()
                self._draw_path_number(position)

    def get_image(self) -> Image:
        return self.image

    def draw(self) -> None:
        self.get_image().show()

    def save(self, *args) -> None:
        self.get_image().save(*args)


class Search:
    """探索系の関数を持つクラス"""

    # 文字列 s のインデックス n の文字を c に置換する関数
    replace = staticmethod(lambda s, n, c: s[:n] + str(c) + s[n + 1 :])

    # 文字列 s のインデックス n の文字を a だけ反転・回転する関数
    rotate = staticmethod(
        lambda s, n, a: s[:n]
        + str(((int(s[n]) // 4 + int(a) // 4) % 2) * 4 + (int(s[n]) % 4 + int(a)) % 4)
        + s[n + 1 :]
    )

    @staticmethod
    def write(text: str = "", output: str = OUT_FILENAME) -> None:
        if os.path.exists(output):
            write_mode = "a"
        else:
            write_mode = "w"
        with open(output, mode=write_mode) as f:
            f.write(text + "\n")

    @staticmethod
    def search_all(output: str = OUT_FILENAME) -> Generator[str, None, None]:
        """純粋に全探索（9! * 8^9 通り）"""
        for i in itertools.permutations(range(NUM_TILE)):
            position = "".join(map(str, i))
            for j in range(8 ** (NUM_TILE)):
                direction = str(oct(j))[2:].zfill(NUM_TILE)
                pattern = position + direction
                town = Town(pattern)
                if not town.has_failed():
                    if output is not None:
                        Search.write(pattern, output)
                    yield pattern

    @staticmethod
    def search_synonym(
        output: str = None,
        num_tiles: List[int] = [3, 4, 4, 4, 3],
        num_angle: List[int] = [1, 4, 2, 2, 1],
    ) -> Generator[str, None, None]:
        """道シノニムによる配置可能な町を探索

        道シノニムの重複順列を生成し、既定の枚数以下のとき、
        すべての回転の組合せについて道が繋がるか確認する

        Args:
            output (str): 配置可能な町シノニムを出力するファイル名
                出力しない時は None とする
            num_tiles (List[int]): 道シノニムの最大枚数のリスト
            num_angle (List[int]): 道シノニムのユニークな回転回数

        Returns:
            Generator[str]: 配置可能な町シノニムのパターン
        """

        num_synonym = len(num_tiles)
        tiles_synonym = Tile.get_synonym()

        # 道シノニムを要素とする重複順列を生成
        for permutation in itertools.product(range(num_synonym), repeat=NUM_TILE):
            position_synonym = "".join(map(str, permutation))

            # それぞれの道シノニムが最大枚数以下かどうかを確認
            for i in range(num_synonym):
                if position_synonym.count(str(i)) > num_tiles[i]:
                    under_num_tiles = False
                    break
                under_num_tiles = True

            if under_num_tiles:
                # 道シノニムの枚数上限以下の場合進む

                # 各タイルのいるインデックスを格納
                indices = []
                for i in range(num_synonym):
                    indices.append(
                        [c.start() for c in re.finditer(str(i), position_synonym)]
                    )

                # 道シノニムの取り得る向きの組合せを全て格納
                angles = [[] for _ in range(num_synonym)]
                for i in range(num_synonym):
                    for angle in itertools.product(
                        range(num_angle[i]), repeat=position_synonym.count(str(i))
                    ):
                        angles[i].append(angle)

                # 道シノニムの取り得る向きの組合せから選ぶ
                direction_synonym = "0" * NUM_TILE  # 向きの初期値は全て 0
                for angle_set in itertools.product(*angles):
                    for i in range(len(angle_set)):
                        for j in range(len(angle_set[i])):
                            direction_synonym = Search.replace(
                                direction_synonym, indices[i][j], angle_set[i][j]
                            )

                    # 町シノニムを作成して道が繋がるか確認
                    pattern = position_synonym + direction_synonym
                    town = Town(pattern, tiles_synonym)

                    # 道が繋がれば出力
                    if not town.has_failed():
                        if output is not None:
                            Search.write(pattern, output)
                        yield pattern

    @staticmethod
    def convert_synonym_original(pattern_synonym: str):
        """町シノニムのパターンから、original の町のパターンに変換

        5 種類の道を重複ありで順列を生成し、既定の枚数以下の場合に
        original のタイルをマッピングして、各タイル 1 枚ずつなら格納

        Args:
            pattern_synonym (str): 生成可能な町シノニムのパターン

        Returns:
            Generator[str]: 生成可能な町のパターン
        """

        # 道シノニムとオリジナルタイルとの対応（十の位：index、一の位：directon）
        # ; の後ろは alien, agent, humberger を考慮して除外した同じ得点になる置き方
        synonym_original_ref = {
            # 道無し, 1 回転; 01, 31, 55, 02, 32, 56, 03, 33, 57
            0: ["00", "30", "54"],
            # 1 曲線, 4 回転
            1: ["10", "26", "50", "80"],
            # 2 曲線, 2 回転
            2: ["04", "21", "41", "71", "06", "23", "43", "73"],
            # 1 直線, 2 回転; 36, 86
            3: ["34", "64", "74", "84", "66", "76"],
            # 2 直線, 1 回転; 46
            4: ["14", "44", "60", "15", "45", "61", "16", "62", "17", "47", "63"],
        }
        num_synonym = len(synonym_original_ref)
        position_synonym = pattern_synonym[:NUM_TILE]
        direction_synonym = pattern_synonym[NUM_TILE:]

        # 各タイルのいるインデックスを格納
        indices = []
        for i in range(num_synonym):
            indices.append([c.start() for c in re.finditer(str(i), position_synonym)])

        # 同じ町シノニムになり得るタイルの組合せを全て格納
        tilefaces = [[] for _ in range(num_synonym)]
        for i in range(num_synonym):
            for tileface in itertools.permutations(
                synonym_original_ref.get(i), position_synonym.count(str(i))
            ):
                tilefaces[i].append(tileface)

        # タイルのあり得る組合せを全て探索
        for tileface_set in itertools.product(*tilefaces):
            position = position_synonym
            direction = direction_synonym
            for i in range(len(tileface_set)):
                for j in range(len(tileface_set[i])):
                    position = Search.replace(
                        position, indices[i][j], tileface_set[i][j][0]
                    )
                    direction = Search.rotate(
                        direction, indices[i][j], tileface_set[i][j][1]
                    )

            # 各タイル 1 枚ずつかどうか確認
            no_dup_tile = True
            for i in range(NUM_TILE):
                if position.count(str(i)) != 1:
                    no_dup_tile = False
                    break

            # 1 枚ずつであれば出力
            if no_dup_tile:
                yield position + direction

    @staticmethod
    def search_town(output: str = None, synonym_output: str = None):
        """シノニムで町の生成可能性を確認して全ての町を探索する"""
        for pattern_synonym in Search.search_synonym(synonym_output):
            for pattern in Search.convert_synonym_original(pattern_synonym):
                if output is not None:
                    Search(pattern, output)
                yield pattern

    @staticmethod
    def search_point(output: str = None):
        """生成可能な町を取得してお題ごとの点数リストを返す"""
        for pattern in Search.search_town():
            points = Town(pattern).get_theme_point()
            if output is not None:
                Search.write(pattern + "," + ",".join(map(str, points)), output)
            yield pattern, points


class Sql:
    """SQL に関する処理をするクラス"""

    @staticmethod
    def init(dbname: str = OUT_DBNAME):
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        cur.execute(
            "create table positions("
            + "id integer primary key autoincrement, seq text unique)"
        )
        cur.execute(
            "create table directions("
            + "id integer primary key autoincrement, seq text unique)"
        )
        theme_cols = ["t" + str(i).zfill(2) for i in range(1, NUM_THEME + 1)]
        cur.execute(
            "create table points(id integer primary key autoincrement, "
            + " integer, ".join(theme_cols) + " integer, unique ("
            + ", ".join(theme_cols) + "))"
        )
        cur.execute("create table towns(\
            id integer primary key autoincrement, \
            pos_id integer, \
            dir_id integer, \
            scr_id integer, \
            foreign key(pos_id) references positions(id), \
            foreign key(dir_id) references directions(id)\
            foreign key(scr_id) references points(id)\
            )")
        cur.close()
        conn.close()

    @staticmethod
    def register(cur: sqlite3.Cursor, pattern: str, points: List[int] = None):
        # TODO: 町のパターンとスコアを投げて DB に登録する
        pass
