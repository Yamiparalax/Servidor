import os
import sys
import zipfile
import shutil
import requests
from pathlib import Path

# URL do Node.js (Github Releases costuma ser menos bloqueado que nodejs.org em algumas empresas, 
# mas vamos tentar direto do site oficial com SSL ignore, pois o Python consegue baixar)
# Versão LTS recente (v20.10.0)
NODE_URL = "https://nodejs.org/dist/v20.10.0/node-v20.10.0-win-x64.zip"
ZIP_NAME = "node_bin.zip"
EXTRACT_DIR = Path("node_bin")

def download_file():
    print(f"Iniciando download de: {NODE_URL}")
    print("IGNORANDO ERROS DE SSL (Necessario para rede corporativa)...")
    
    try:
        # verify=False é o segredo para baixar na rede da empresa sem configurar CA
        response = requests.get(NODE_URL, stream=True, verify=False)
        response.raise_for_status()
        
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
        print(f"\nERRO CRITICO NO DOWNLOAD: {e}")
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
            expected_folder = ZIP_NAME.replace(".zip", "") # node-v20.10.0-win-x64
            
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
    npm_path = EXTRACT_DIR / "npm.cmd"
    if npm_path.exists():
        # Cria um .npmrc na pasta do projeto para garantir
        with open(".npmrc", "w") as f:
            f.write("strict-ssl=false\n")
            f.write("registry=http://registry.npmjs.org/\n")
        print("Arquivo .npmrc criado com settings permissivas.")
    else:
        print("NPM nao encontrado para configurar.")

if __name__ == "__main__":
    if download_file():
        if extract_file():
            configure_npm_ssl()
            print("\n=================================================")
            print("INSTALACAO DO NODE PORTATIL CONCLUIDA!")
            print("Agora execute o arquivo: run_with_portable_node.bat")
            print("=================================================")
            
            # Tenta limpar o zip
            try: os.remove(ZIP_NAME)
            except: pass
        else:
            print("Falha na extracao.")
    else:
        print("Falha no download.")
