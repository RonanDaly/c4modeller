import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from c4modeller.gui import MainWindow


class ModelTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_visibility_toggle_does_not_rebuild_model_tree(self) -> None:
        window = MainWindow()
        try:
            item = window.model_tree.topLevelItem(0)
            self.assertIsNotNone(item)
            assert item is not None
            element_id = item.data(0, Qt.UserRole)
            refresh_model_tree_called = False

            def refresh_model_tree() -> None:
                nonlocal refresh_model_tree_called
                refresh_model_tree_called = True

            window.refresh_model_tree = refresh_model_tree

            item.setCheckState(0, Qt.Unchecked)

            self.assertFalse(refresh_model_tree_called)
            self.assertIs(item.treeWidget(), window.model_tree)
            self.assertFalse(window.workspace.is_element_checked(element_id))
            self.assertNotIn(element_id, window.element_items)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
