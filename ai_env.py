import gymnasium as gym
from gymnasium import spaces
import numpy as np
import math

class LunarAutonomousEnv(gym.Env):
    """
    Gymnasium prostředí pro výcvik LunarATC Autopilota.
    """
    def __init__(self):
        super().__init__()
        self.R_EQ = 1737400.0
        self.MU = 4.9048695e12
        self.time_step = 20.0
        
        # Akce: 0 = Nic, 1 = Zážeh Prograde (+10m/s), 2 = Zážeh Retrograde (-10m/s)
        self.action_space = spaces.Discrete(3)
        
        # Pozorování (Senzory): [X, Y, Z, VX, VY, VZ, Palivo]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(7,), dtype=np.float32)
        
        self.state = None
        self.steps_survived = 0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps_survived = 0
        
        # Hodíme loď náhodně do výšky 100km - 500km s lehce chybnou rychlostí
        alt = np.random.uniform(100000.0, 500000.0)
        perfect_v = math.sqrt(self.MU / (self.R_EQ + alt))
        start_v = perfect_v * np.random.uniform(0.8, 1.2) # Úmyslná chyba, ať to musí AI srovnat
        
        self.state = np.array([self.R_EQ + alt, 0.0, 0.0, 0.0, start_v, 0.0, 1000.0], dtype=np.float32)
        return self.state, {}

    def calculate_gravity(self, x, y, z):
        r = math.sqrt(x**2 + y**2 + z**2)
        if r == 0: return 0, 0, 0
        a = -self.MU / (r**2)
        return a * (x/r), a * (y/r), a * (z/r)

    def step(self, action):
        x, y, z, vx, vy, vz, fuel = self.state
        
        # 1. Zpracování zážehu od AI
        if action == 1 and fuel >= 10.0:
            v_mag = math.sqrt(vx**2 + vy**2 + vz**2)
            if v_mag > 0:
                vx *= (v_mag + 10.0)/v_mag; vy *= (v_mag + 10.0)/v_mag; vz *= (v_mag + 10.0)/v_mag
            fuel -= 10.0
        elif action == 2 and fuel >= 10.0:
            v_mag = math.sqrt(vx**2 + vy**2 + vz**2)
            if v_mag > 0:
                # Ošetření, abychom nenásobili nulou/záporem
                vx *= max(0.1, (v_mag - 10.0))/v_mag; vy *= max(0.1, (v_mag - 10.0))/v_mag; vz *= max(0.1, (v_mag - 10.0))/v_mag
            fuel -= 10.0

        # 2. Posun fyziky
        gx, gy, gz = self.calculate_gravity(x, y, z)
        vx += gx * self.time_step; vy += gy * self.time_step; vz += gz * self.time_step
        x += vx * self.time_step; y += vy * self.time_step; z += vz * self.time_step
        
        self.steps_survived += 1
        self.state = np.array([x, y, z, vx, vy, vz, fuel], dtype=np.float32)
        
        # 3. Odměňovací systém (Tohle AI formuje)
        reward = 0.0
        terminated = False
        truncated = False
        
        r = math.sqrt(x**2 + y**2 + z**2)
        altitude = r - self.R_EQ
        
        if altitude <= 0:
            reward = -1000.0 # Trest za smrt
            terminated = True
        elif altitude > 2000000.0:
            reward = -500.0 # Trest za odlet z radaru
            terminated = True
        else:
            reward = 1.0 # Žije
            if action == 0:
                reward += 0.5 # Odměna za šetření paliva
                
        # Limit epizody (1000 ticků = úspěšný let)
        if self.steps_survived >= 1000:
            truncated = True
            reward += 500.0 # Ultimátní odměna za zvládnutí stabilní dráhy
            
        return self.state, reward, terminated, truncated, {}