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


class TestView(unittest.TestCase):
    def test__draw_real_town(self) -> None:
        actual = np.array(Image.open(View("206745813361230035")))
        expected = np.array(Image.open("tests/expected/206745813361230035.png"))
        self.assertTrue(np.array_equal(actual, expected))

    def test__draw_pseudo_town(self) -> None:
        actual = np.array(Image.open(View(Town("206745813361230035"))))
        expected = np.array(Image.open("tests/expected/206745813361230035_p.png"))
        self.assertTrue(np.array_equal(actual, expected))

    def test__draw_pseudo_town_synonym(self) -> None:
        actual = np.array(
            Image.open(View(Town("224221113000100031", Tile.get_synonym())))
        )
        expected = np.array(Image.open("tests/expected/224221113000100031_p.png"))
        self.assertTrue(np.array_equal(actual, expected))


class TestSearch(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = "../test_temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    @unittest.skip("needs long time")
    def test_search_synonym(self) -> None:
        print("道シノニムによる配置可能な町を生成します (約 20 時間)")
        temp_file = os.path.join(self.temp_dir, "synonym_pattern.txt")
        for _ in Search.search_synonym(temp_file):
            pass
        self.assertTrue(
            filecmp.cmp(temp_file, "tests/expected/synonym_pattern.txt", shallow=False)
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)
