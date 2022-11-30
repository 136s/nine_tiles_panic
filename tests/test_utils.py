#!/usr/bin/env python

import filecmp
import os
import shutil
import unittest

import numpy as np
from PIL import Image

from nine_tiles_panic import Tile
from nine_tiles_panic import Town
from nine_tiles_panic import Search, View

INPUT_DIR = "./tests/input/"
EXPECTED_DIR = "./tests/expected/"
TEMP_DIR = "./test_temp/"


class TestView(unittest.TestCase):
    def test__draw_real_town(self) -> None:
        pattern = "206745813361230035"
        actual = np.array(View(pattern).get_image())
        expected = np.array(Image.open(EXPECTED_DIR + pattern + ".png"))
        self.assertTrue(np.array_equal(actual, expected))

    def test__draw_pseudo_town(self) -> None:
        pattern = "206745813361230035"
        actual = np.array(View(Town(pattern)).get_image())
        expected = np.array(Image.open(EXPECTED_DIR + pattern + "_p.png"))
        self.assertTrue(np.array_equal(actual, expected))

    def test__draw_pseudo_town_synonym(self) -> None:
        pattern = "224221113000100031"
        actual = np.array(View(Town(pattern, Tile.get_synonym())).get_image())
        expected = np.array(Image.open(EXPECTED_DIR + pattern + "_p.png"))
        self.assertTrue(np.array_equal(actual, expected))


class TestSearch(unittest.TestCase):
    def setUp(self) -> None:
        os.makedirs(TEMP_DIR, exist_ok=True)

    def test_convert_synonym_original(self) -> None:
        print("町シノニムからオリジナルタイルに変換します（約 30 秒間）")
        pattern_synonym = "224221113000100031"
        filename = "town_points_{}.txt".format(pattern_synonym)
        temp_file = os.path.join(TEMP_DIR, filename)
        with Search.text_io(temp_file) as f:
            for pattern in Search.convert_synonym_original(pattern_synonym):
                points = Town(pattern).get_theme_point()
                f.write(pattern + str(points) + "\n")
        self.assertTrue(filecmp.cmp(temp_file, EXPECTED_DIR + filename, shallow=False))

    @unittest.skip("needs long time")
    def test_search_synonym(self) -> None:
        print("道シノニムによる配置可能な町を生成します（約 20 時間）")
        temp_file = os.path.join(TEMP_DIR, "synonym_pattern.txt")
        for _ in Search.search_synonym(temp_file):
            pass
        self.assertTrue(
            filecmp.cmp(temp_file, EXPECTED_DIR + "synonym_pattern.txt", shallow=False)
        )

    def test_search_point_from_pattern_file(self) -> None:
        pattern_synonym = "000113123000121301"
        filename = "town_points_{}.txt".format(pattern_synonym)
        temp_file = os.path.join(TEMP_DIR, filename)
        with Search.text_io(temp_file) as f:
            for pattern, points in Search.search_point_from_pattern_file(
                pattern_synonym, INPUT_DIR
            ):
                f.write(pattern + str(points) + "\n")
        self.assertTrue(filecmp.cmp(temp_file, EXPECTED_DIR + filename, shallow=False))

    def tearDown(self) -> None:
        shutil.rmtree(TEMP_DIR)
