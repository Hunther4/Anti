import os
import subprocess

def process_data(user_input):
    # CRITICAL: Inyección de comandos via eval
    data = eval(user_input)
    
    # CRITICAL: Inyección via subprocess con shell=True
    subprocess.run(f"echo {user_input}", shell=True)
    
    # CRITICAL: Secreto hardcodeado
    slack_webhook = "https://hooks.example.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    
    try:
        os.system(f"cat {user_input}")
    except Exception:
        # WARNING: except vacío que silencia el error
        pass
    
    return data