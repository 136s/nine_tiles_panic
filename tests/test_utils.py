#!/usr/bin/env python

import filecmp
import os
import shutil
import unittest

from nine_tiles_panic.utils import Search


class TestSearch(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = "../test_temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    @unittest.skip("needs long time")
    def test_search_synonym(self):
        print("道シノニムによる配置可能な町を生成します (約 20 時間)")
        temp_file = os.path.join(self.temp_dir, "synonym_pattern.txt")
        for _ in Search.search_synonym(temp_file):
            pass
        self.assertTrue(
            filecmp.cmp(temp_file, "tests/expected/synonym_pattern.txt", shallow=False)
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)
