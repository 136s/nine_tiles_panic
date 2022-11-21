#!/usr/bin/env python

import filecmp
import os
import shutil
import unittest

import numpy as np
from PIL import Image

from nine_tiles_panic.tile import Tile
from nine_tiles_panic.town import Town
from nine_tiles_panic.utils import Search, View

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

    @unittest.skip("needs long time")
    def test_search_synonym(self) -> None:
        print("道シノニムによる配置可能な町を生成します (約 20 時間)")
        temp_file = os.path.join(TEMP_DIR, "synonym_pattern.txt")
        for _ in Search.search_synonym(temp_file):
            pass
        self.assertTrue(
            filecmp.cmp(temp_file, EXPECTED_DIR + "synonym_pattern.txt", shallow=False)
        )

    def tearDown(self) -> None:
        shutil.rmtree(TEMP_DIR)
