"""
Configuração global de testes.

Substitui pyautogui e pygetwindow por mocks ANTES de qualquer import de instal,
permitindo que os testes rodem em qualquer plataforma (Linux/Mac/CI headless).
"""

import sys
from unittest.mock import MagicMock


class FakeImageNotFoundException(Exception):
    pass


class FakeFailSafeException(Exception):
    pass


_pyautogui_mock = MagicMock()
_pyautogui_mock.ImageNotFoundException = FakeImageNotFoundException
_pyautogui_mock.FailSafeException = FakeFailSafeException
_pyautogui_mock.FAILSAFE = True

sys.modules["pyautogui"] = _pyautogui_mock
sys.modules["pygetwindow"] = MagicMock()
