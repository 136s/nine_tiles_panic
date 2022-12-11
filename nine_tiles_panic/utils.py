#!/usr/bin/env python
"""
表示や探索などのツールに関するモジュール。

View クラス：タイル面や町を描画するクラス。
Search クラス：生成可能な町パターンを探索するクラス。
Sql クラス：探索結果の町や得点を計算して格納するクラス。
"""

import glob
from importlib import resources
import io
import itertools
import math
import os
import re
import sqlite3
from typing import Generator, List, Tuple, Union

from PIL import Image, ImageDraw

from nine_tiles_panic import config
from nine_tiles_panic import TileFace, Tile
from nine_tiles_panic import Town
import nine_tiles_panic.data.imgs as realimg

LEN_SIDE = config.LEN_SIDE
NUM_TILE = config.NUM_TILE
OUT_FILENAME = config.OUT_FILENAME
OUT_DBNAME = config.OUT_DBNAME
NUM_THEME = config.NUM_THEME


class View:
    """View クラス。

    TileFace または Town インスタンスを描画する。
    町パターンかタイル面パターンを入れたら本家タイル面で描画する。

    Attributes:
        object (Union[str, TileFace, Town]): 描画したいタイル面か町のイ
            ンスタンス、もしくは町パターンかタイル面パターンの文字列。
        image (Image): object を基に描画した Image のインスタンス。
        drawer (ImageDraw): 疑似町や番号を描画する用の ImageDraw。
        view_number (bool): タイル面や町に番号を描画する場合は True。
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
        """View クラスのコンストラクタ。

        フィールドを初期化する。

        Args:
            object (Union[str, TileFace, Town]): 描画したいタイル面か町
                のインスタンス、もしくは町パターンかタイル面パターンの文
                字列。
            does_display (bool, optional): View インスタンスを作って同時
                に描画もする場合は True。初期値は False。
            view_number (bool, optional): タイル面や町に番号を描画する場
                合は True。初期値は False
        """
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
                     But the length is {}.".format(
                        len(self.object)
                    )
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

    def real_image(tile: int, is_back: int) -> str:
        return resources.files(realimg).joinpath("tf{}{}.png".format(tile, is_back))

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
        is_back = 1 - (int(direction) < 4)
        angle = int(direction) % 4
        self.image = Image.open(View.real_image(tile, is_back)).rotate(angle * 90)

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

    # 町を回転させたときの position の対応表
    position_lookup = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8],
        [2, 5, 8, 1, 4, 7, 0, 3, 6],
        [8, 7, 6, 5, 4, 3, 2, 1, 0],
        [6, 3, 0, 7, 4, 1, 8, 5, 2],
    ]

    # 文字列 s のインデックス n の文字を c に置換する関数
    replace = staticmethod(lambda s, n, c: s[:n] + str(c) + s[n + 1 :])

    # 文字列 s のインデックス n の文字を a だけ反転・回転する関数
    rotate = staticmethod(
        lambda s, n, a: s[:n]
        + str(((int(s[n]) // 4 + int(a) // 4) % 2) * 4 + (int(s[n]) % 4 + int(a)) % 4)
        + s[n + 1 :]
    )

    @staticmethod
    def rotate_synonym_tile(tile_pat: str, angle: int) -> str:
        """道シノニムのタイルを方向付き 2 桁で入れて回転させる。

        Args:
            tile_pat (str): 道シノニムのタイルパターン
                （十の位: 0-4, 一の位: 0-3）。
            angle (int): 回転する角度 (0-3)。

        Returns:
            str: 回転したタイル面パターン
        """
        tile = tile_pat[0]
        dir = int(tile_pat[1])
        if tile in ("0", "4"):
            rot_pat = tile_pat
        elif tile == "1":
            rot_pat = tile + str((dir + angle) % 4)
        elif tile in ("2", "3"):
            rot_pat = tile + str((dir + angle) % 2)
        else:
            raise NotImplementedError("道シノニムを入力してください")
        return rot_pat

    @staticmethod
    def rotate_synonym_town(pattern: str, angle: int) -> str:
        """町シノニムを回転させる。

        Args:
            pattern (str): 町シノニムのパターン（18 桁）。
            angle (int): 回転する角度 (0-3)。

        Returns:
            str: 回転した町パターン
        """
        if angle != 0:
            tiles = [pattern[i] + pattern[i + NUM_TILE] for i in range(NUM_TILE)]
            r_tiles = [Search.rotate_synonym_tile(tile, angle) for tile in tiles]
            r_tiles_remap = [r_tiles[p] for p in Search.position_lookup[angle]]
            r_pattern = "".join([s[0] for s in r_tiles_remap]) + "".join(
                [s[1] for s in r_tiles_remap]
            )
        else:
            r_pattern = pattern
        return r_pattern

    @staticmethod
    def first_synonym_town(pattern: str) -> str:
        """町シノニムの回転町の中で最小の町を取得する。

        Args:
            pattern (str): 町シノニムのパターン（18 桁）。

        Returns:
            str: 回転町シノニムの辞書順で最初の町シノニムのパターン。
        """
        return str(
            min([int(Search.rotate_synonym_town(pattern, angle)) for angle in range(4)])
        ).zfill(NUM_TILE * 2)

    @DeprecationWarning
    @staticmethod
    def write(text: str = "", output: str = OUT_FILENAME) -> None:
        if os.path.exists(output):
            write_mode = "a"
        else:
            write_mode = "w"
        with open(output, mode=write_mode) as f:
            f.write(text + "\n")

    @staticmethod
    def text_io(output: str = OUT_FILENAME) -> io.TextIOWrapper:
        if not os.path.exists(output):
            f = open(output, mode="w")
            f.close()
        return open(output, mode="a")

    @staticmethod
    def search_all(output: str = OUT_FILENAME) -> Generator[str, None, None]:
        """純粋に全探索（9! * 8^9 通り）"""
        if output is not None:
            f = Search.text_io(output)
        for i in itertools.permutations(range(NUM_TILE)):
            position = "".join(map(str, i))
            for j in range(8 ** (NUM_TILE)):
                direction = str(oct(j))[2:].zfill(NUM_TILE)
                pattern = position + direction
                town = Town(pattern)
                if not town.has_failed():
                    if output is not None:
                        f.write(pattern)
                    yield pattern
        if output is not None:
            f.close()

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

        Yields:
            str: 配置可能な町シノニムのパターン
        """

        num_synonym = len(num_tiles)
        tiles_synonym = Tile.get_synonym()
        if output is not None:
            f = Search.text_io(output)

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

                    if not town.has_failed():
                        # 道が繋がれば、町ごと回転
                        first_synonym = Search.first_synonym_town(pattern)
                        if pattern == first_synonym:
                            # 回転町の中で辞書順で最初であれば出力
                            if output is not None:
                                f.write(pattern)
                            yield pattern
        if output is not None:
            f.close()

    @staticmethod
    def convert_synonym_original(pattern_synonym: str) -> Generator[str, None, None]:
        """町シノニムのパターンから、original の町のパターンに変換。

        5 種類の道を重複ありで順列を生成し、既定の枚数以下の場合に
        original のタイルをマッピングして、各タイル 1 枚ずつなら格納。

        Args:
            pattern_synonym (str): 生成可能な町シノニムのパターン。

        Yields:
            str: 生成可能な町のパターン。
        """

        # 道シノニムとオリジナルタイルとの対応（十の位：index、一の位：directon）
        # ; の後ろは alien, agent, humberger を考慮して除外した同じ得点になる置き方
        synonym_original_ref = {
            # 道無し, 1 回転; 01, 02, 03, 31, 32, 33, 55, 56, 57
            0: [["00"], ["30"], ["54"]],
            # 1 曲線, 4 回転
            1: [["10"], ["26"], ["50"], ["80"]],
            # 2 曲線, 2 回転
            2: [["04", "06"], ["21", "23"], ["41", "43"], ["71", "73"]],
            # 1 直線, 2 回転; 36, 86
            3: [["34"], ["64", "66"], ["74", "76"], ["84"]],
            # 2 直線, 1 回転; 46, 47
            4: [["14", "15", "16", "17"], ["44", "45"], ["60", "61", "62", "63"]],
        }
        num_synonym = len(synonym_original_ref)
        position_synonym = pattern_synonym[:NUM_TILE]
        direction_synonym = pattern_synonym[NUM_TILE:]

        # 各タイルのいるインデックスを格納
        indices = [[] for _ in range(num_synonym)]
        for i, p in enumerate(position_synonym):
            indices[int(p)].append(i)

        # 同じ町シノニムになり得るタイルの組合せを全て格納
        tilefaces = [[] for _ in range(num_synonym)]
        for i in range(num_synonym):
            for tileface_groups in itertools.permutations(
                synonym_original_ref.get(i), position_synonym.count(str(i))
            ):
                for tileface in itertools.product(*tileface_groups):
                    tilefaces[i].append(tileface)

        # タイルのあり得る組合せを全て探索
        for tileface_set in itertools.product(*tilefaces):
            # 使われてるタイルが 9 種類なら進む
            if len(set([t[0] for ts in tileface_set for t in ts])) == NUM_TILE:
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
                yield position + direction

    @staticmethod
    def search_town(
        output: str = None, synonym_output: str = None
    ) -> Generator[str, None, None]:
        """シノニムで町の生成可能性を確認して全ての町を探索する。

        Args:
            output (str, optional): 町のパターン文字列を出力するファイル。
                初期値は None。
            synonym_output (str, optional): 町シノニムのパターン文字列を
                出力するファイル。初期値は None。

        Yields:
            str: 生成可能な町のパターン。
        """
        if output is not None:
            f = Search.text_io(output)
        for pattern_synonym in Search.search_synonym(synonym_output):
            for pattern in Search.convert_synonym_original(pattern_synonym):
                if output is not None:
                    f.write(pattern)
                yield pattern
        if output is not None:
            f.close()

    @staticmethod
    def search_point(
        output: str = None,
    ) -> Generator[Tuple[str, List[int]], None, None]:
        """生成可能な町を取得してお題ごとの点数リストを返す。

        Args:
            output (str, optional): 町のパターン文字列を出力するファイル。
                初期値は None。

        Yields:
            str: 生成可能な町のパターン。
            List[int]: お題の点数。お題番号 - 1 の index に格納する。
        """
        if output is not None:
            f = Search.text_io(output)
        for pattern in Search.search_town():
            points = Town(pattern, is_completable=True).get_theme_point()
            if output is not None:
                f.write(pattern + "," + ",".join(map(str, points)), output)
            yield pattern, points
        if output is not None:
            f.close()

    @staticmethod
    def search_point_from_synonym(
        pattern_synonym: str,
    ) -> Generator[Tuple[str, List[int]], None, None]:
        """町シノニムからお題ごとの点数リストを返す（シノニムでも計算）。

        お題の性質に合わせて、3 ステップで得点を計算する。

        Args:
            pattern_synonym (str): 生成可能な町シノニムのパターン。

        Yields:
            str: 生成可能な町のパターン。
            List[int]: お題の点数。お題番号 - 1 の index に格納する。
        """

        synonym_themes = [4, 5, 6, 10, 11, 13, 15]  # 道の形状で計算できるお題
        tile_themes = [3, 7, 9, 12, 21, 22, 23, 24, 25, 26]  # タイル面で計算できるお題
        road_themes = [1, 2, 8, 14, 16, 17, 18, 19, 20]  # pattern ごとに計算するお題

        points = [0] * NUM_THEME
        synonym_town = Town(pattern_synonym, Tile.get_synonym())
        # 道から点数計算
        for theme in synonym_themes:
            points[theme - 1] = synonym_town.theme_point(theme)
        previous_position = ""
        for pattern in Search.convert_synonym_original(pattern_synonym):
            town = Town(pattern, is_completable=True)
            # 面から点数計算
            if (position := pattern[:NUM_TILE]) != previous_position:
                # タイル面が変わった時のみ計算する
                # 厳密には direction の方も確認が必要だが、
                # この順番の探索では pattern がひとつ前と同じなのに
                # position が不変のことはないので問題ない
                for theme in tile_themes:
                    points[theme - 1] = town.theme_point(theme)
                previous_position = position
            for theme in road_themes:
                points[theme - 1] = town.theme_point(theme)
            yield pattern, points

    @staticmethod
    def search_point_2(
        output: str = None, synonym_output: str = None
    ) -> Generator[Tuple[str, List[int]], None, None]:
        """生成可能な町を取得してお題ごとの点数リストを返す（シノニムでも計算）。

        Args:
            output (str, optional): 町のパターン文字列を出力するファイル。
                初期値は None。

        Yields:
            str: 生成可能な町のパターン。
            List[int]: お題の点数。お題番号 - 1 の index に格納する。
        """
        if output is not None:
            f = Search.text_io(output)
        for pattern_synonym in Search.search_synonym(synonym_output):
            for pattern, points in Search.search_point_from_synonym(pattern_synonym):
                if output is not None:
                    f.write(pattern + "," + ",".join(map(str, points)), output)
                yield pattern, points
        if output is not None:
            f.close()

    @staticmethod
    def search_point_from_pattern_file(
        pattern_synonym: str, dir: str = ""
    ) -> Generator[Tuple[str, List[int]], None, None]:
        """事前に得た生成可能な町のパターン文字列から点数計算。

        対応する町パターン文字列が1 行ずつ記録されている町シノニムのファ
        イル名 `{pattern_synonym}.txt` を入力とする。

        Args:
            pattern_synonym (str): 町シノニムのパターン文字列
            dir (str, optional): テキストファイルが格納されているディレ
                クトリ。初期値は ""。

        Yields:
            str: 生成可能な町のパターン。
            List[int]: お題の点数。お題番号 - 1 の index に格納する。
        """

        synonym_themes = [4, 5, 6, 10, 11, 13, 15]  # 道の形状で計算できるお題
        tile_themes = [3, 7, 9, 12, 21, 22, 23, 24, 25, 26]  # タイル面で計算できるお題
        road_themes = [1, 2, 8, 14, 16, 17, 18, 19, 20]  # pattern ごとに計算するお題

        points = [0] * NUM_THEME
        synonym_town = Town(pattern_synonym, Tile.get_synonym())
        # 道から点数計算
        for theme in synonym_themes:
            points[theme - 1] = synonym_town.theme_point(theme)
        previous_position = ""
        # パターンファイルから点数計算
        with open(os.path.join(dir, pattern_synonym + ".txt")) as f:
            for line in f:
                pattern = line.split("\n")[0]
                town = Town(pattern, is_completable=True)
                # 面から点数計算
                if (position := pattern[:NUM_TILE]) != previous_position:
                    # タイル面が変わった時のみ計算する
                    # 厳密には direction の方も確認が必要だが、
                    # この順番の探索では pattern がひとつ前と同じなのに
                    # position が不変のことはないので問題ない
                    for theme in tile_themes:
                        points[theme - 1] = town.theme_point(theme)
                    previous_position = position
                for theme in road_themes:
                    points[theme - 1] = town.theme_point(theme)
                yield pattern, points


class Sql:
    """SQL に関する処理をするクラス"""

    theme_cols = ["t" + str(i).zfill(2) for i in range(1, NUM_THEME + 1)]

    @staticmethod
    def init(dbname: str = OUT_DBNAME) -> None:
        """データベースファイルを作成する。

        Args:
            dbname (str, optional): ファイル名。
                初期値は `config.OUT_DBNAME`。
        """
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        cur.execute(
            "create table towns(\
            id integer primary key autoincrement, \
            pos text, \
            dir text, "
            + " integer, ".join(Sql.theme_cols)
            + " integer)"
        )
        cur.close()
        conn.close()

    @staticmethod
    def register_town(cur: sqlite3.Cursor, pattern: str, pnt: List[int]) -> None:
        """データベースに 1 つの町と得点を登録する。

        Args:
            cur (sqlite3.Cursor): カーソルオブジェクト。
            pattern (str): 町のパターン文字列。
            pnt (List[int]): お題の点数。
        """
        cur.execute(
            "insert into towns values(NULL, {}, {}, {})".format(
                pattern[:NUM_TILE], pattern[NUM_TILE:], ", ".join(map(str, pnt))
            )
        )

    @staticmethod
    def register(
        dbname: str = OUT_DBNAME,
        pattern_file: str = None,
        synonym_file: str = None,
        pattern_files_dir: str = None,
    ) -> None:
        """全ての生成可能な町とその全てのお題の点数を登録する。

        データベースファイル名以外に事前の計算情報を与えること段階的な探
        索が可能。何も事前情報がない場合は 0 から探索する。

        Args:
            dbname (str, optional): データベースファイル名。
                初期値は `config.OUT_DBNAME`。
            pattern_file (str, optional): 町パターンのテキストファイル。
            synonym_file (str, optional): 町シノニムのテキストファイル。
            pattern_files_dir (str, optional): 町シノニムのファイル名に
                対応町パターンが記録されたテキストファイル群のディレクト
                リ。
        """
        if not os.path.exists(dbname):
            Sql.init(dbname)
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        try:
            if pattern_file:
                # 先にパターンファイル作ってる場合はそれを読んで記録
                with open(pattern_file) as f:
                    for line in f:
                        pattern = line.split("\n")[0]
                        points = Town(pattern).get_theme_point()
                        Sql.register_town(cur, pattern, points)
            elif synonym_file:
                # 先に道シノニムのファイル作ってる場合はそれを読んで記録
                with open(synonym_file) as f:
                    for line in f:
                        pattern_synonym = line.split("\n")[0]
                        for pattern, points in Search.search_point_from_synonym(
                            pattern_synonym
                        ):
                            Sql.register_town(cur, pattern, points)
            elif pattern_files_dir:
                # 道シノニム.txt にパターンが入ってる場合はそれを読んで記録
                for pattern_file in glob.glob(os.path.join(pattern_files_dir, "*.txt")):
                    for pattern, points in Search.search_point_from_pattern_file(
                        os.path.basename(pattern_file).split(".", 1)[0],
                        pattern_files_dir,
                    ):
                        Sql.register_town(cur, pattern, points)
            else:
                # パターンファイルがない場合は探索から実行して記録
                for pattern, points in Search.search_point_2():
                    Sql.register_town(cur, pattern, points)
        except:  # noqa: E722
            print("町・得点の記録においてエラーが発生しました")
        finally:
            conn.commit()
            cur.close()
            conn.close()
            print("町・得点の記録は終了しました")

    @staticmethod
    def select_town(town_id: int, dbname: str = OUT_DBNAME) -> Tuple[str, Tuple[int]]:
        """データベースから町とその点数を選択する。

        Args:
            town_id (int): 町の id。
            dbname (str, optional): ファイル名。
                初期値は `config.OUT_DBNAME`。
        Returns:
            str: 生成可能な町のパターン。
            List[int]: お題の点数。
        """
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        try:
            record = cur.execute(
                "select * from towns where id = " + str(town_id)
            ).fetchone()
            pattern = record[1].zfill(NUM_TILE) + record[2].zfill(NUM_TILE)
            points = record[3:]
        except:  # noqa: E722
            print("町・得点の取得においてエラーが発生しました")
        finally:
            cur.close()
            conn.close()
        return pattern, points
