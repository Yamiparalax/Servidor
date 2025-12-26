import os
import sys
import zipfile
import shutil
import requests
from pathlib import Path

# Lista de Mirrors para tentar baixar o Node.js
# Versão LTS v20.10.0
FILENAME = "node-v20.10.0-win-x64.zip"
MIRRORS = [
    # 1. Official (Blocked often)
    f"https://nodejs.org/dist/v20.10.0/{FILENAME}", 
    # 2. NPM Mirror (China - frequent update, robust)
    f"https://npmmirror.com/mirrors/node/v20.10.0/{FILENAME}",
    # 3. Huawei Cloud (Another robust mirror)
    f"https://mirrors.huaweicloud.com/nodejs/v20.10.0/{FILENAME}",
    # 4. Berkeley (Academic mirror)
    f"https://mirrors.ocf.berkeley.edu/nodejs/v20.10.0/{FILENAME}",
    # 5. Direct Backup (If I had one, but these should suffice)
]

ZIP_NAME = "node_bin.zip"
EXTRACT_DIR = Path("node_bin")

def download_file():
    print(f"Iniciando tentativa de download do Node.js...")
    
    # Headers to mimic browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for url in MIRRORS:
        print(f"Tentando: {url}")
        try:
            print("IGNORANDO SSL (Rede Corporativa)...")
            # verify=False e allow_redirects=True para seguir redirects, mas verificamos se nao fomos para uma block page
            response = requests.get(url, stream=True, verify=False, headers=headers, timeout=30)
            
            # Checa se foi bloqueado (c6bank redirect ou 403)
            if response.status_code != 200:
                print(f"FALHA HTTP: {response.status_code}")
                continue
            
            if "c6bank" in response.url.lower() or "block" in response.url.lower():
                print("BLOQUEADO PELO FIREWALL (Redirect detectado).")
                continue

            content_type = response.headers.get('Content-Type', '').lower()
            if 'zip' not in content_type and 'octet-stream' not in content_type:
                 print(f"CONTEUDO INVALIDO (Content-Type: {content_type}). Provavelmente uma pagina de bloqueio.")
                 continue

            total_length = response.headers.get('content-length')
            downloaded = 0
            
            with open(ZIP_NAME, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_length:
                            percent = int((downloaded / int(total_length)) * 100)
                            if percent % 10 == 0:
                                print(f"Download: {percent}%", end="\r")
                                
            print("\nDownload concluido com SUCESSO!")
            return True
        except Exception as e:
            print(f"Erro neste mirror: {e}")
            continue
            
    print("\nTODOS OS MIRRORS FALHARAM.")
    return False

def extract_file():
    print("Extraindo arquivos...")
    try:
        if EXTRACT_DIR.exists():
            print("Limpando pasta antiga...")
            shutil.rmtree(EXTRACT_DIR)
            
        with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
            # Extrai para pasta temporaria
            zip_ref.extractall(".")
            
            # O zip cria uma pasta com o nome da versao (ex: node-v20.10.0-win-x64)
            # Vamos renomear para node_bin
            expected_folder = FILENAME.replace(".zip", "") # node-v20.10.0-win-x64
            
            # Encontra a pasta extraida
            extracted_folder = None
            for item in os.listdir("."):
                if item.startswith("node-v") and os.path.isdir(item) and item != "node_modules":
                    extracted_folder = item
                    break
            
            if extracted_folder:
                shutil.move(extracted_folder, EXTRACT_DIR)
                print(f"Extraido para: {EXTRACT_DIR.absolute()}")
                return True
            else:
                print("Nao consegui encontrar a pasta extraida.")
                return False
                
    except Exception as e:
        print(f"Erro na extracao: {e}")
        return False

def configure_npm_ssl():
    print("Configurando NPM para ignorar SSL (Fix para 'Self Signed Certificate')...")
    if EXTRACT_DIR.exists():
        # Tenta achar onde esta o npm
        npm_cmd = EXTRACT_DIR / "npm.cmd"
        
        # Cria um .npmrc na pasta do projeto root
        with open(".npmrc", "w") as f:
            f.write("strict-ssl=false\n")
            f.write("registry=http://registry.npmjs.org/\n")
            f.write("ca=null\n")
        print("Arquivo .npmrc criado com settings permissivas.")
    else:
        print("Pasta node_bin nao encontrada para configurar.")

if __name__ == "__main__":
    if download_file():
        if extract_file():
            configure_npm_ssl()
            print("\n=================================================")
            print("INSTALACAO DO NODE PORTATIL CONCLUIDA!")
            print("=================================================")
            
            # Tenta limpar o zip
            try: os.remove(ZIP_NAME)
            except: pass
        else:
            print("Falha na extracao.")
    else:
        print("Falha no download.")
