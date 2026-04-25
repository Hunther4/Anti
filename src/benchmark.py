import os
import json
import asyncio
from datetime import datetime

class SentinelGauntlet:
    def __init__(self, agent):
        self.agent = agent
        self.results = []
        self.model_name = "unknown-model"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(self.agent.base_dir, "workspace", "benchmarks")
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    async def run(self):
        # Identify model
        await self.agent.brain.sync_model_context()
        self.model_name = self.agent.brain.model
        
        print(f"\n[SENTINEL GAUNTLET] Iniciando evaluación para: {self.model_name}")
        
        tests = [
            {
                "id": "Test 1",
                "name": "Potencia Bruta (TPS & Latency)",
                "prompt": "Escribe una implementación completa en Python de un sistema de subastas en tiempo real usando WebSockets y FastAPI. Incluye manejo de estado y persistencia en memoria.",
            },
            {
                "id": "Test 2",
                "name": "Integridad Sentinel (Context Management)",
                "prompt": f"Analiza el archivo '{os.path.join(self.agent.base_dir, 'core', 'agent.py')}' y genera una documentación detallada de cada método. Luego, basándote en eso, sugiere 3 optimizaciones de rendimiento.",
            },
            {
                "id": "Test 3",
                "name": "Cognición Superior (Reasoning)",
                "prompt": "Explica la paradoja de la 'Nave de Teseo' aplicada a un sistema operativo que se actualiza a sí mismo bit a bit. ¿En qué punto deja de ser el sistema original? Usa tu modo reasoner.",
                "reasoner": True
            },
            {
                "id": "Test 4",
                "name": "Agencia y Herramientas (Action)",
                "prompt": "Busca en el workspace todos los archivos .py, lístalos, y crea un archivo llamado `architecture_summary.txt` con un diagrama de clases en formato texto basado en los imports que encuentres.",
            },
            {
                "id": "Test 5",
                "name": "El Alma Arquitectónica (Persona Check)",
                "prompt": "¿Qué opinas de los programadores que no usan tipado estático en Python? Dame tu veredicto como Senior Architect.",
            }
        ]
        
        for test in tests:
            print(f"\n>>> {test['id']}: {test['name']}...")
            
            # Reset history for each test
            original_history = self.agent.history.copy()
            self.agent.history = []
            
            # Toggle reasoner mode if specified
            original_reasoner = self.agent.reasoner_mode
            if test.get("reasoner"):
                self.agent.reasoner_mode = True
                print(f"[*] Modo Reasoner: ACTIVADO")
            
            start_time = datetime.now()
            response_data = await self.agent._process(test['prompt'])
            end_time = datetime.now()
            
            # Restore reasoner mode
            self.agent.reasoner_mode = original_reasoner
            
            duration = (end_time - start_time).total_seconds()
            usage = response_data.get("usage", {})
            
            result = {
                "id": test['id'],
                "name": test['name'],
                "prompt": test['prompt'],
                "response": response_data['response'],
                "usage": usage,
                "duration": duration,
                "tps": usage.get("tps", 0),
                "steps": len(response_data.get('steps', [])),
                "score": response_data.get("score", 0)
            }
            
            self.results.append(result)
            self.agent.history = original_history # Restore history
            
        return self.save_report()

    def save_report(self):
        filename = f"sentinel_{self.model_name.replace(':', '_')}_{self.timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        avg_tps = sum(r['tps'] for r in self.results) / len(self.results) if self.results else 0
        total_duration = sum(r['duration'] for r in self.results)
        
        report = [
            f"# Sentinel Gauntlet Report: {self.model_name}",
            f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Modelo Detectado:** `{self.model_name}`",
            f"**TPS Promedio:** {avg_tps:.2f} t/s",
            f"**Tiempo Total:** {total_duration:.2f}s",
            "\n## Resumen de Resultados\n",
            "| Test | TPS | Duración | Steps | Score |",
            "|:--- |:--- |:--- |:--- |:--- |"
        ]
        
        for r in self.results:
            report.append(f"| {r['id']} | {r['tps']:.2f} | {r['duration']:.2f}s | {r['steps']} | {r['score']} |")
            
        report.append("\n---\n")
        
        for r in self.results:
            report.append(f"### {r['id']}: {r['name']}")
            report.append(f"**Prompt:** *{r['prompt']}*\n")
            report.append("**Response:**")
            report.append(f"{r['response']}\n")
            report.append(f"**Metrics:** Prompt Tokens: {r['usage'].get('prompt_tokens', 0)} | Completion Tokens: {r['usage'].get('completion_tokens', 0)} | Speed: {r['tps']:.2f} t/s\n")
            report.append("---")
            
        content = "\n".join(report)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Update history.json
        history_path = os.path.join(self.output_dir, "history.json")
        history = []
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except: pass
            
        history.append({
            "model": self.model_name,
            "timestamp": self.timestamp,
            "avg_tps": avg_tps,
            "total_duration": total_duration,
            "report_file": filename
        })
        
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
            
        return filepath
