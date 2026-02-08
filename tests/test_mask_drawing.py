
import unittest
import numpy as np
import os
import shutil
from src.core.scene import MaskEntity, EntityType
from src.core.project import ProjectManager

class TestMaskDrawing(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_project_mask_draw"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
    def test_mask_painting(self):
        mask = MaskEntity("DrawMask")
        mask.set_property("Type", "Draw")
        mask.set_property("Mask Resolution", 100)
        
        # Initial state: None
        self.assertIsNone(mask.mask_data)
        
        # Paint center
        # Terrain size 1000. Center is 0,0.
        # Radius 100.
        # Pixel coords: Center (50, 50). Radius 10 px.
        
        mask.paint(0, 0, 100.0, strength=1.0, opacity=1.0, terrain_size=1000.0)
        
        self.assertIsNotNone(mask.mask_data)
        self.assertEqual(mask.mask_data.shape, (100, 100))
        
        # Check center value
        # We need to copy to CPU if it's on GPU (it is)
        from src.core.backend import to_cpu
        data = to_cpu(mask.mask_data)
        
        self.assertGreater(data[50, 50], 0.0)
        self.assertEqual(data[0, 0], 0.0) # Corner should be empty
        
    def test_mask_persistence(self):
        # Create Project Manager
        pm = ProjectManager()
        pm.new_project()
        
        # Create Entity
        root = MaskEntity("RootMask") # Root can be anything actually, usually TerrainEntity
        child = MaskEntity("ChildMask")
        root.add_child(child)
        
        child.set_property("Type", "Draw")
        child.set_property("Mask Resolution", 64)
        
        # Paint on child
        child.paint(0, 0, 500.0, 1.0, 1.0, terrain_size=1000.0)
        
        # Save
        pm.save_project(root, self.test_dir)
        
        # Check file exists
        expected_file = os.path.join(self.test_dir, "masks", f"mask_{child.id}.npy")
        self.assertTrue(os.path.exists(expected_file))
        
        # Load
        loaded_root, msg = pm.load_project(os.path.join(self.test_dir, "test_project_mask_draw.terrano"))
        self.assertIsNotNone(loaded_root)
        
        # Find child
        loaded_child = loaded_root._children[0]
        self.assertEqual(loaded_child.name, "ChildMask")
        
        # Check data loaded
        self.assertIsNotNone(loaded_child.mask_data)
        self.assertEqual(loaded_child.mask_data.shape, (64, 64))
        
        from src.core.backend import to_cpu
        data = to_cpu(loaded_child.mask_data)
        self.assertGreater(data[32, 32], 0.0)

if __name__ == '__main__':
    unittest.main()
