import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from profix.prefix import _normalize_windows_path, create_proton_prefix


class PrefixCreationTests(unittest.TestCase):
    def test_normalize_windows_path_accepts_c_drive(self):
        self.assertEqual(
            _normalize_windows_path(r"C:\Program Files\My Game"),
            Path("Program Files") / "My Game",
        )

    def test_normalize_windows_path_rejects_escape(self):
        with self.assertRaises(ValueError):
            _normalize_windows_path("C:/Program Files/../Secrets")

    def test_create_proton_prefix_creates_symlinked_game_path(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            prefix_path = temp_path / "prefix"
            game_path = temp_path / "My Game"
            game_path.mkdir()

            created_links = create_proton_prefix(
                prefix_path,
                [f"C:/Program Files/My Game={game_path}"],
            )

            self.assertEqual(len(created_links), 1)
            self.assertTrue((prefix_path / "dosdevices" / "c:").is_symlink())
            self.assertTrue((prefix_path / "dosdevices" / "z:").is_symlink())

            link_path = prefix_path / "drive_c" / "Program Files" / "My Game"
            self.assertTrue(link_path.is_symlink())
            self.assertEqual(link_path.resolve(), game_path.resolve())

    def test_create_proton_prefix_is_idempotent_for_matching_symlinks(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            prefix_path = temp_path / "prefix"
            game_path = temp_path / "My Game"
            game_path.mkdir()
            link_spec = f"C:/Program Files/My Game={game_path}"

            create_proton_prefix(prefix_path, [link_spec])
            created_links = create_proton_prefix(prefix_path, [link_spec])

            self.assertEqual(len(created_links), 1)


if __name__ == "__main__":
    unittest.main()
