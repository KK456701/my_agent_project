"""验证简化后的图"""
import sys
sys.path.insert(0, '.')
from src.graph.debate_graph import build_debate_graph

g = build_debate_graph()
print("Graph built OK")
print(f"Compiled graph ready")
