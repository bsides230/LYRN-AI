import unittest
import os
import shutil
import json
from services import index_manager

class TestIndexManager(unittest.TestCase):
    def setUp(self):
        # Override INDEXES_DIR for testing to not pollute actual data
        self.test_dir = "test_runtime_indexes"
        index_manager.INDEXES_DIR = self.test_dir
        index_manager.STORAGE_DIR = os.path.join(self.test_dir, "storage")
        index_manager.SETTINGS_FILE = os.path.join(self.test_dir, "settings.json")
        index_manager.CATEGORIES_FILE = os.path.join(self.test_dir, "categories.csv")

        os.makedirs(self.test_dir, exist_ok=True)
        # Create a mock settings file
        with open(index_manager.SETTINGS_FILE, "w") as f:
            json.dump({"default_recall_limit": 2}, f)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_store_and_recall_index(self):
        category = "test_cat"

        # Test Case 1: First store
        pipe_string_1 = '{"key": "val1"}|log1|md1'
        index_manager.store_index_string(category, pipe_string_1)

        recalled_1 = index_manager.recall_index_string(category)
        self.assertEqual(recalled_1, pipe_string_1)

        # Test Case 2: Second store, should prepend and replace static
        pipe_string_2 = '{"key": "val2"}|log2|md2'
        index_manager.store_index_string(category, pipe_string_2)

        recalled_2 = index_manager.recall_index_string(category)
        expected_2 = '{"key": "val2"}|log2,log1|md2\nmd1'
        self.assertEqual(recalled_2, expected_2)

        # Test Case 3: Third store, should hit the limit of 2 set in setUp
        pipe_string_3 = '{"key": "val3"}|log3|md3'
        index_manager.store_index_string(category, pipe_string_3)

        recalled_3 = index_manager.recall_index_string(category)
        # Should only return log3, log2 and md3, md2 because limit is 2
        expected_3 = '{"key": "val3"}|log3,log2|md3\nmd2'
        self.assertEqual(recalled_3, expected_3)

if __name__ == '__main__':
    unittest.main()
