"""Offline input and isolation checks; Unreal runtime import is verified separately."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('mesh_importer', Path(__file__).with_name('import_meshy_unreal.py'))
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / 'character.fbx').write_bytes(b'fixture path, not a real FBX')
        (self.folder / 'normal.png').write_bytes(b'fixture path')
        self.data = {'asset_name': 'TownCandidate', 'fbx_path': 'character.fbx', 'asset_type': 'skeletal'}

    def validate(self, **changes):
        data = dict(self.data, **changes)
        path = self.folder / 'manifest.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return importer.validate_manifest(path)

    def test_relative_sources_and_safe_defaults(self):
        result = self.validate(textures={'normal': 'normal.png'})
        self.assertEqual(result['fbx_path'], str((self.folder / 'character.fbx').resolve()))
        self.assertEqual(result['candidate_folder'], '/Game/Characters/Meshy/TownCandidate/candidate_v001')
        self.assertEqual(result['target_height_cm'], 170)
        self.assertEqual(result['normal_convention'], 'DirectX')
        self.assertFalse(result['create_placement_blueprint'])

    def test_static_opengl_and_optional_blueprint(self):
        result = self.validate(asset_type='static', normal_convention='OpenGL', create_placement_blueprint=True)
        self.assertEqual(result['asset_type'], 'static')
        self.assertTrue(result['create_placement_blueprint'])

    def test_production_paths_and_path_traversal_are_rejected(self):
        for destination in ('/Game/Characters/Main/TownKeeper', '/Game/Characters/Meshy/../Main', '/Game/Characters/Meshy/X/', '/Game/Characters/MeshyEvil/X'):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                self.validate(destination=destination)
        for key in ('asset_name', 'candidate_version'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(**{key: '../TownKeeper'})

    def test_invalid_height_types_and_nonfinite_numbers_are_rejected(self):
        for height in (True, 0, -1, '170', float('nan'), float('inf')):
            with self.subTest(height=height), self.assertRaises(ValueError):
                self.validate(target_height_cm=height)

    def test_missing_local_inputs_are_rejected(self):
        with self.assertRaises(FileNotFoundError):
            self.validate(fbx_path='missing.fbx')
        with self.assertRaises(FileNotFoundError):
            self.validate(textures={'basecolor': 'missing.png'})
        with self.assertRaises(ValueError):
            self.validate(fbx_path='https://example.com/model.fbx')

    def test_typo_or_unsupported_options_are_rejected(self):
        for changes in ({'asset_type': 'animation'}, {'normal_convention': 'Unknown'}, {'textures': {'metallic': 'normal.png'}}, {'textures': []}, {'target_height': 170}, {'create_placement_blueprint': 'true'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.validate(**changes)

    def test_candidate_cannot_overwrite_existing_asset(self):
        importer.ensure_empty_candidate([])
        with self.assertRaises(ValueError):
            importer.ensure_empty_candidate(['/Game/Characters/Meshy/TownCandidate/candidate_v001/SK_TownCandidate'])

    def test_multiple_texture_sets_cannot_be_silently_flattened(self):
        importer.validate_material_slots(['Atlas'], True)
        importer.validate_material_slots([], False)
        for slots, textured in [(['Hair', 'Body'], True), (['Hair', 'Body'], False), ([], True)]:
            with self.subTest(slots=slots, textured=textured), self.assertRaises(ValueError):
                importer.validate_material_slots(slots, textured)

    def test_windows_commandline_quoted_path(self):
        self.assertEqual(importer.unreal_manifest_argument('-run=pythonscript -MeshyManifest="C:/My Files/manifest.json" -unattended'), 'C:/My Files/manifest.json')
        with self.assertRaises(ValueError):
            importer.unreal_manifest_argument('-run=pythonscript')


if __name__ == '__main__':
    unittest.main()
