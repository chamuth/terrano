use noise::{NoiseFn, Perlin};

#[derive(Clone)]
pub struct NoiseGenerator {
    noise: Perlin,
    scale: f64,
    octaves: usize,
    persistence: f64,
    lacunarity: f64,
    seed: u32,
}

impl NoiseGenerator {
    pub fn new(seed: u32) -> Self {
        Self {
            noise: Perlin::new(seed),
            scale: 50.0,
            octaves: 4,
            persistence: 0.5,
            lacunarity: 2.0,
            seed,
        }
    }
    
    pub fn with_scale(mut self, scale: f64) -> Self {
        self.scale = scale;
        self
    }
    
    pub fn with_octaves(mut self, octaves: usize) -> Self {
        self.octaves = octaves;
        self
    }
    
    pub fn with_persistence(mut self, persistence: f64) -> Self {
        self.persistence = persistence;
        self
    }
    
    pub fn with_lacunarity(mut self, lacunarity: f64) -> Self {
        self.lacunarity = lacunarity;
        self
    }
    
    /// Generate noise value at given coordinates using fractal Brownian motion
    pub fn generate(&self, x: f64, y: f64) -> f64 {
        let mut total = 0.0;
        let mut frequency = 1.0;
        let mut amplitude = 1.0;
        let mut max_value = 0.0;
        
        for _ in 0..self.octaves {
            let sample_x = x / self.scale * frequency;
            let sample_y = y / self.scale * frequency;
            
            let noise_value = self.noise.get([sample_x, sample_y]);
            total += noise_value * amplitude;
            
            max_value += amplitude;
            amplitude *= self.persistence;
            frequency *= self.lacunarity;
        }
        
        // Normalize to [0, 1]
        (total / max_value + 1.0) / 2.0
    }
    
    pub fn scale(&self) -> f64 {
        self.scale
    }
    
    pub fn octaves(&self) -> usize {
        self.octaves
    }
    
    pub fn persistence(&self) -> f64 {
        self.persistence
    }
    
    pub fn lacunarity(&self) -> f64 {
        self.lacunarity
    }
    
    pub fn seed(&self) -> u32 {
        self.seed
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_noise_generation() {
        let generator = NoiseGenerator::new(42);
        let value = generator.generate(0.0, 0.0);
        assert!(value >= 0.0 && value <= 1.0);
    }
    
    #[test]
    fn test_noise_deterministic() {
        let gen1 = NoiseGenerator::new(42);
        let gen2 = NoiseGenerator::new(42);
        
        let val1 = gen1.generate(10.0, 20.0);
        let val2 = gen2.generate(10.0, 20.0);
        
        assert_eq!(val1, val2);
    }
}
