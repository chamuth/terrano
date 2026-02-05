
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QWidget, 
                             QVBoxLayout, QPushButton, QSlider, QLabel, QGroupBox, QRadioButton, QFormLayout)
from PyQt6.QtCore import Qt

from src.core.terrain_data import TerrainData
from src.core.roads import RoadNetwork
from src.ui.viewport import TerrainViewport
from src.generators.noise_generator import PerlinNoiseGenerator

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Terrano: BeamNG Terrain Tool")
        self.resize(1200, 800)
        
        # Core Models
        self.terrain = TerrainData(size=256)
        self.road_net = RoadNetwork()
        
        # UI Setup
        self.init_ui()
        
        # State
        self.mode = "TERRAIN" # or "ROAD"

    def init_ui(self):
        self.viewport = TerrainViewport(self.terrain, self.road_net, on_click_callback=self.handle_viewport_click)
        self.setCentralWidget(self.viewport)
        
        # Tools Dock
        dock = QDockWidget("Toolkit", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Mode Switcher
        mode_grp = QGroupBox("Mode")
        mode_layout = QVBoxLayout()
        self.rb_terrain = QRadioButton("Terrain Inspection")
        self.rb_terrain.setChecked(True)
        self.rb_terrain.toggled.connect(lambda: self.set_mode("TERRAIN"))
        
        self.rb_road = QRadioButton("Road Placement")
        self.rb_road.toggled.connect(lambda: self.set_mode("ROAD"))
        
        mode_layout.addWidget(self.rb_terrain)
        mode_layout.addWidget(self.rb_road)
        mode_grp.setLayout(mode_layout)
        layout.addWidget(mode_grp)
        
        # Generator Controls
        gen_grp = QGroupBox("Generator (Perlin)")
        gen_layout = QFormLayout()
        
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(10, 500)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self.regenerate_terrain)
        gen_layout.addRow("Scale:", self.scale_slider)
        
        self.octaves_slider = QSlider(Qt.Orientation.Horizontal)
        self.octaves_slider.setRange(1, 10)
        self.octaves_slider.setValue(6)
        self.octaves_slider.valueChanged.connect(self.regenerate_terrain)
        gen_layout.addRow("Octaves:", self.octaves_slider)

        self.seed_slider = QSlider(Qt.Orientation.Horizontal)
        self.seed_slider.setRange(0, 100)
        self.seed_slider.setValue(0)
        self.seed_slider.valueChanged.connect(self.regenerate_terrain)
        gen_layout.addRow("Seed:", self.seed_slider)
        
        gen_grp.setLayout(gen_layout)
        layout.addWidget(gen_grp)

        # Terrain Actions
        bg_grp = QGroupBox("Terrain Tools")
        bg_layout = QVBoxLayout()
        btn_reset = QPushButton("Reset Terrain")
        btn_reset.clicked.connect(self.reset_terrain)
        bg_layout.addWidget(btn_reset)
        bg_grp.setLayout(bg_layout)
        layout.addWidget(bg_grp)
        
        # Road Actions
        road_grp = QGroupBox("Road Tools")
        road_layout = QVBoxLayout()
        
        btn_carve = QPushButton("Carve Road to Terrain")
        btn_carve.clicked.connect(self.carve_road)
        road_layout.addWidget(btn_carve)
        
        btn_export = QPushButton("Export to BeamNG")
        btn_export.clicked.connect(self.export_beamng)
        road_layout.addWidget(btn_export)
        
        road_grp.setLayout(road_layout)
        layout.addWidget(road_grp)
        
        layout.addStretch()
        widget.setLayout(layout)
        dock.setWidget(widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def set_mode(self, mode):
        self.mode = mode
        print(f"Mode set to: {mode}")

    def reset_terrain(self):
        self.terrain.reset()
        self.viewport.update_mesh()

    def handle_viewport_click(self, x, z):
        if self.mode == "ROAD":
            self.road_net.add_node(x, z)
            print(f"Added road node at {x:.2f}, {z:.2f}")
            self.viewport.update_mesh()

    def regenerate_terrain(self):
        # Lazy init generator if needed, or use self.generator if defined
        if not hasattr(self, 'generator'):
            self.generator = PerlinNoiseGenerator()
            
        scale = self.scale_slider.value()
        octaves = self.octaves_slider.value()
        seed = self.seed_slider.value()
        
        self.generator.generate(
            self.terrain, 
            scale=float(scale), 
            octaves=octaves, 
            seed=seed
        )
        self.viewport.update_mesh()

    def carve_road(self):
        points = self.road_net.get_spline_points(resolution=1000)
        if len(points) > 0:
            self.terrain.carve_road(points)
            self.viewport.update_mesh()

    def export_beamng(self):
        from src.exporters.beamng import BeamNGExporter
        import os
        
        exporter = BeamNGExporter()
        
        # Ensure output dir
        os.makedirs("output", exist_ok=True)
        
        # Export Heightmap
        meta = exporter.export_heightmap(self.terrain, "output/heightmap.png")
        print(f"Exported Heightmap. Meta: {meta}")
        
        # Export Roads
        exporter.export_roads(self.road_net, "output/roads.json")
        print("Exported Roads.")
