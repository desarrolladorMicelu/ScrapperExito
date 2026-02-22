"""
Script para verificar dónde está el archivo en SharePoint
"""

from sharepoint_uploader import SharePointUploader
import requests

def verificar_archivo():
    print("\n" + "="*60)
    print("VERIFICANDO UBICACIÓN DEL ARCHIVO EN SHAREPOINT")
    print("="*60 + "\n")
    
    try:
        uploader = SharePointUploader()
        
        # Autenticar
        if not uploader.obtener_token():
            return
        
        # Obtener Site ID
        if not uploader.obtener_site_id():
            return
        
        # Listar archivos en la carpeta
        folder_path_encoded = uploader.folder_path.strip('/')
        url = f"https://graph.microsoft.com/v1.0/sites/{uploader.site_id}/drive/root:/{folder_path_encoded}:/children"
        
        headers = {
            'Authorization': f'Bearer {uploader.access_token}',
            'Accept': 'application/json'
        }
        
        print(f"📂 Buscando archivos en: {uploader.folder_path}\n")
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            archivos = data.get('value', [])
            
            if archivos:
                print(f"✓ Se encontraron {len(archivos)} archivo(s):\n")
                for archivo in archivos:
                    nombre = archivo.get('name')
                    tamano = archivo.get('size', 0) / 1024  # KB
                    fecha = archivo.get('lastModifiedDateTime', 'N/A')
                    web_url = archivo.get('webUrl', 'N/A')
                    
                    print(f"  📄 {nombre}")
                    print(f"     Tamaño: {tamano:.2f} KB")
                    print(f"     Modificado: {fecha}")
                    print(f"     URL: {web_url}\n")
            else:
                print("⚠ La carpeta está vacía\n")
        else:
            print(f"❌ Error al listar archivos: {response.status_code}")
            print(f"   Response: {response.text}\n")
            
            # Intentar listar carpetas disponibles
            print("📁 Intentando listar carpetas disponibles...\n")
            url_root = f"https://graph.microsoft.com/v1.0/sites/{uploader.site_id}/drive/root/children"
            response_root = requests.get(url_root, headers=headers)
            
            if response_root.status_code == 200:
                carpetas = response_root.json().get('value', [])
                print("Carpetas en la raíz del sitio:")
                for carpeta in carpetas:
                    if carpeta.get('folder'):
                        print(f"  📁 {carpeta.get('name')}")
                print()
        
    except Exception as e:
        print(f"❌ Error: {e}\n")

if __name__ == "__main__":
    verificar_archivo()
