import secrets
import string
import hmac
import hashlib
import base64
import os
import pathlib

def generate_key():
    parts = []
    for _ in range(3):
        part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        parts.append(part)
    return f"POSEIDON-{'-'.join(parts)}"

def make_sig(secret: str, key: str, plan: str) -> str:
    mac = hmac.new(secret.encode(), f"{key}|{plan}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode().rstrip("=")

def main():
    print("=== Generador de Licencias PoseidonUI ===")
    
    # 1. Plan
    print("\nSelecciona el plan:")
    print("1. Basic (Status, Guardian)")
    print("2. Pro (Basic + Tickets, Niveles, Economía, Anti-Spam)")
    print("3. Elite (Pro + Ofertas, Sorteos, LoL, Web, Soporte VIP)")
    print("4. Custom")
    
    choice = input("Opción [1-3]: ").strip()
    plan_map = {"1": "basic", "2": "pro", "3": "elite", "4": "custom"}
    plan = plan_map.get(choice, "basic")
    
    # 2. Generar Key
    key = generate_key()
    print(f"\nClave Generada: {key}")
    print(f"Plan: {plan.upper()}")
    
    # 3. Firma (Opcional)
    secret = os.getenv("LICENSE_SIGNING_SECRET", "")
    # Intentar leer .env manualmente
    if not secret and pathlib.Path(".env").exists():
        try:
            for line in pathlib.Path(".env").read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("LICENSE_SIGNING_SECRET="):
                    secret = line.split("=", 1)[1].strip()
                    break
        except:
            pass
            
    signature = ""
    if secret:
        print(f"\nSecreto detectado: {secret[:3]}***")
        do_sign = input("¿Firmar licencia? [S/n]: ").lower() != "n"
        if do_sign:
            signature = make_sig(secret, key, plan)
            print(f"Firma: {signature}")
    else:
        print("\nNo se detectó LICENSE_SIGNING_SECRET en .env.")
        print("La licencia se generará SIN FIRMA (plana).")
        print("Nota: Asegúrate de que ALLOW_PLAIN_LICENSES=1 esté en el .env del bot si usas licencias sin firma.")
        
    # 4. Resultado
    line_entry = f"{key}|{plan}"
    if signature:
        line_entry += f"|{signature}"
        
    print("\n--- Copia esta línea en licenses_plans.txt ---")
    print(line_entry)
    print("---------------------------------------------")
    
    # 5. Guardado automático
    save = input("\n¿Añadir automáticamente a licenses_plans.txt? [S/n]: ").lower() != "n"
    if save:
        try:
            with open("licenses_plans.txt", "a", encoding="utf-8") as f:
                f.write(line_entry + "\n")
            print("✅ Guardado correctamente en licenses_plans.txt.")
        except Exception as e:
            print(f"❌ Error al guardar: {e}")
            
    input("\nPresiona Enter para salir...")

if __name__ == "__main__":
    main()
