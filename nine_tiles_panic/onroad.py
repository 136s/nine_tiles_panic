#!/usr/bin/env python

from typing import List


class Agent:
    """Agent クラス

    町の道にいるエージェントのクラス

    Attributes:
        face (int): 向いている Path の辺番号 (0-35)
        dir (str): 向いている Path の端点 (left or right)
        is_capturing (bool): 宇宙人を捕まえていたら True
        capturing_alien (int): 捕まえている宇宙人の Path の index 番号
    """

    def __init__(self, face: int) -> None:
        """Agent クラスのコンストラクタ。

        フィールドを初期化する。

        Args:
            face (int): 向いている Path の辺番号 (0-35)
        """
        self.face: int = face
        self.dir: str = ""
        self.is_capturing: bool = False
        self.capturing_alien: int = None

    def __str__(self) -> str:
        return "<Agent({}, {}) {}.>".format(
            self.face,
            self.dir,
            "captures an alien[{}]".format(self.capturing_alien)
            if self.is_capturing
            else "is free",
        )

    def __repr__(self) -> str:
        # コンストラクタで入力しない情報が多いので str で対応
        return str(self)

    def get_face(self) -> int:
        return self.face

    def rotate(self, angle: int = 0) -> None:
        if angle != 0:
            self.face = (self.face + angle) % 4

    def set_dir(self, direction: str) -> None:
        self.dir = direction
        return self

    def get_dir(self) -> str:
        return self.dir

    def capture(self, capturing_alien: int = None) -> None:
        self.is_capturing = True
        self.capturing_alien = capturing_alien

    def is_free(self) -> bool:
        return not self.is_capturing


class Alien:
    """Alien クラス

    町の道にいる宇宙人のクラス

    Attributes:
        face (int): 向いている Path の辺番号 (0-35)
        dir (str): 向いている Path の端点 (left or right)
        is_captured (bool): エージェントに捕まっていたら True
        captured_agent (int): 捕らえられたエージェントの Path の index 番号
        eating (bool): ハンバーガーを食べていたら True
        eating_hamburger (int): 食べているハンバーガーの Path の index 番号
    """

    def __init__(self, face: int) -> None:
        """Alien クラスのコンストラクタ。

        フィールドを初期化する。

        Args:
            face (int): 向いている Path の辺番号 (0-35)
        """
        self.face: int = face
        self.dir: str = ""
        self.is_captured: bool = False
        self.captured_agent: int = None
        self.eating: bool = False
        self.eating_hamburger: int = None

    def __str__(self) -> str:
        return "<Alien({}, {}) {} and {}.>".format(
            self.face,
            self.dir,
            "is captured by an agent[{}]".format(self.captured_agent)
            if self.is_captured
            else "is free",
            "eats a hamburger[{}]".format(self.eating_hamburger)
            if self.eating
            else "is hangry",
        )

    def __repr__(self) -> str:
        # コンストラクタで入力しない情報が多いので str で対応
        return str(self)

    def get_face(self) -> int:
        return self.face

    def rotate(self, angle: int = 0) -> None:
        if angle != 0:
            self.face = (self.face + angle) % 4

    def set_dir(self, direction: str) -> None:
        self.dir = direction
        return self

    def get_dir(self) -> str:
        return self.dir

    def captured(self, captured_agent: int = None) -> None:
        self.is_captured = True
        self.captured_agent = captured_agent

    def is_free(self) -> bool:
        return not self.is_captured

    def eat(self, eating_hamburger: int = None) -> None:
        self.eating = True
        self.eating_hamburger = eating_hamburger

    def is_hangry(self) -> bool:
        return not self.eating


class Hamburger:
    """Hamburger クラス

    町の道にあるハンバーガーのクラス

    Attributes:
        is_eaten (bool): 宇宙人に食べられていたら True
        ate_alien (List[int]): 食べられた宇宙人の Path の index 番号
            （ハンバーガーは左右 1 体ずつの宇宙人から食べられうる）
    """

    def __init__(self) -> None:
        """Hamburger クラスのコンストラクタ。"""
        self.is_eaten: bool = False
        self.ate_alien: List[int] = []

    def __str__(self) -> str:
        return "<Hamburger is {}.>".format(
            "aten by aliens" + str(self.ate_alien) if self.is_eaten else "free"
        )

    def __repr__(self) -> str:
        # コンストラクタでは何も入力しないので str で対応
        return str(self)

    def get_face(self) -> int:
        raise NotImplementedError("Hamburger has no face.")

    def set_dir(self, direction: str) -> None:
        raise NotImplementedError("Hamburger has no face.")

    def eaten(self, ate_alien: int = None) -> None:
        self.is_eaten = True
        self.ate_alien.append(ate_alien)

    def is_free(self) -> bool:
        return not self.is_eaten
