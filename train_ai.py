from ai_env import LunarAutonomousEnv
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env

# 1. Validace prostředí (Ujistíme se, že naše fyzika komunikuje s AI správně)
env = LunarAutonomousEnv()
check_env(env)
print("✅ Prostředí úspěšně prošlo validací. Matrix je připraven.")

# 2. Vytvoření neuronové sítě
# MlpPolicy znamená Multi-Layer Perceptron (klasická "černá skříňka")
print("🚀 Sestavuji strukturu PPO Agenta...")
model = PPO("MlpPolicy", env, verbose=1, learning_rate=0.0005)

# 3. Spuštění hlubokého učení
print("🧠 START TRÉNINKU (Proběhne 100 000 kroků. Může to trvat pár minut.)")
print("Sleduj hodnotu 'ep_rew_mean' v terminálu - čím je vyšší, tím je AI chytřejší!")
model.learn(total_timesteps=100000)

# 4. Uložení vytrénovaného mozku
model.save("lunar_autopilot_v1")
print("💾 TRÉNINK DOKONČEN! Model 'lunar_autopilot_v1.zip' uložen na disk.")