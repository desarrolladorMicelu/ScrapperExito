import os
import json
import pandas as pd
from datetime import datetime
import msal
import requests
from dotenv import load_dotenv

load_dotenv()

class SharePointUploader:
    """Clase para subir archivos Excel a SharePoint usando Microsoft Graph API"""
    
    def __init__(self):
        # Credenciales de Azure AD
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        
        # Configuración de SharePoint
        self.site_url = os.getenv('SHAREPOINT_SITE_URL')
        self.folder_path = os.getenv('SHAREPOINT_FOLDER_PATH')
        self.file_name = os.getenv('SHAREPOINT_FILE_NAME', 'productos_exito.xlsx')
        
        # Validar configuración
        if not all([self.tenant_id, self.client_id, self.client_secret, self.site_url, self.folder_path]):
            raise ValueError("Faltan credenciales de SharePoint en .env")
        
        self.access_token = None
        self.site_id = None
    
    def obtener_token(self):
        """Obtiene token de acceso de Microsoft Graph"""
        try:
            authority = f"https://login.microsoftonline.com/{self.tenant_id}"
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=authority,
                client_credential=self.client_secret
            )
            
            result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                return True
            else:
                print(f"❌ Error obteniendo token: {result.get('error_description', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"❌ Error en autenticación: {e}")
            return False
    
    def obtener_site_id(self):
        """Obtiene el ID del sitio de SharePoint"""
        try:
            # Extraer hostname y path del site_url
            # Ejemplo: https://micelu.sharepoint.com/sites/ProyectosMICELU
            parts = self.site_url.replace('https://', '').split('/')
            hostname = parts[0]
            site_path = '/' + '/'.join(parts[1:]) if len(parts) > 1 else ''
            
            url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:{site_path}"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            self.site_id = response.json()['id']
            return True
        except Exception as e:
            print(f"❌ Error obteniendo Site ID: {e}")
            return False
    
    def convertir_json_a_excel(self, json_file='iphones_exito.json'):
        """Convierte el JSON de productos a Excel"""
        try:
            # Leer JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                productos = json.load(f)
            
            if not productos:
                print("⚠ No hay productos para convertir")
                return None
            
            # Convertir a formato plano para Excel
            datos_excel = []
            
            for producto in productos:
                fila = {
                    'Nombre': producto.get('nombre'),
                    'Código': producto.get('codigo'),
                    'Código OFIM': producto.get('codigo_ofim'),
                    'Color OFIM': producto.get('color_ofim'),
                    'URL': producto.get('url'),
                    'Fecha Consulta': producto.get('fecha_consulta'),
                    'Fecha Actualización': producto.get('fecha_actualizacion'),
                    'Total Vendedores': producto.get('total_vendedores'),
                    
                    # Posición #1
                    'Pos1 Vendedor': producto.get('posicion_1', {}).get('vendedor'),
                    'Pos1 Precio': producto.get('posicion_1', {}).get('precio'),
                    'Pos1 Precio Numérico': producto.get('posicion_1', {}).get('precio_numerico'),
                    
                    # Micelu
                    'Micelu Existe': 'SÍ' if producto.get('micelu', {}).get('existe') else 'NO',
                    'Micelu Posición': producto.get('micelu', {}).get('posicion'),
                    'Micelu Precio': producto.get('micelu', {}).get('precio'),
                    'Micelu Precio Numérico': producto.get('micelu', {}).get('precio_numerico'),
                    'Micelu Diferencia vs Pos1': producto.get('micelu', {}).get('diferencia_vs_posicion1'),
                    'Micelu Diferencia %': producto.get('micelu', {}).get('diferencia_porcentaje'),
                }
                
                datos_excel.append(fila)
            
            # Crear DataFrame
            df = pd.DataFrame(datos_excel)
            
            # Guardar temporalmente
            temp_file = 'temp_productos_exito.xlsx'
            df.to_excel(temp_file, index=False, engine='openpyxl')
            
            print(f"✓ Excel generado: {len(datos_excel)} productos")
            return temp_file
            
        except Exception as e:
            print(f"❌ Error convirtiendo JSON a Excel: {e}")
            return None
    
    def subir_a_sharepoint(self, archivo_local):
        """Sube el archivo Excel a SharePoint (reemplaza si existe)"""
        try:
            # Leer archivo
            with open(archivo_local, 'rb') as f:
                file_content = f.read()
            
            # Construir URL para subir archivo
            # Formato: /sites/{site-id}/drive/root:/{folder-path}/{filename}:/content
            folder_path_encoded = self.folder_path.strip('/')
            url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{folder_path_encoded}/{self.file_name}:/content"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            
            # Subir archivo (PUT reemplaza si existe)
            response = requests.put(url, headers=headers, data=file_content)
            response.raise_for_status()
            
            result = response.json()
            web_url = result.get('webUrl', 'N/A')
            
            print(f"✓ Archivo subido a SharePoint: {self.file_name}")
            print(f"  URL: {web_url}")
            
            return True
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ Error HTTP subiendo a SharePoint: {e}")
            print(f"   Response: {e.response.text if e.response else 'N/A'}")
            return False
        except Exception as e:
            print(f"❌ Error subiendo a SharePoint: {e}")
            return False
    
    def ejecutar(self):
        """Ejecuta el proceso completo: convertir JSON a Excel y subir a SharePoint"""
        print(f"\n{'='*60}")
        print("SUBIENDO EXCEL A SHAREPOINT")
        print(f"{'='*60}\n")
        
        # 1. Obtener token
        print("🔐 Autenticando con Microsoft Graph...")
        if not self.obtener_token():
            return False
        print("✓ Token obtenido\n")
        
        # 2. Obtener Site ID
        print("🔍 Obteniendo Site ID...")
        if not self.obtener_site_id():
            return False
        print(f"✓ Site ID: {self.site_id}\n")
        
        # 3. Convertir JSON a Excel
        print("📊 Convirtiendo JSON a Excel...")
        archivo_excel = self.convertir_json_a_excel()
        if not archivo_excel:
            return False
        
        # 4. Subir a SharePoint
        print(f"\n📤 Subiendo a SharePoint...")
        print(f"   Sitio: {self.site_url}")
        print(f"   Carpeta: {self.folder_path}")
        print(f"   Archivo: {self.file_name}\n")
        
        exito = self.subir_a_sharepoint(archivo_excel)
        
        # 5. Limpiar archivo temporal
        try:
            os.remove(archivo_excel)
        except:
            pass
        
        if exito:
            print(f"\n{'='*60}")
            print("✓ PROCESO COMPLETADO EXITOSAMENTE")
            print(f"{'='*60}\n")
        
        return exito


def subir_excel_a_sharepoint():
    """Función helper para llamar desde otros módulos"""
    try:
        uploader = SharePointUploader()
        return uploader.ejecutar()
    except Exception as e:
        print(f"❌ Error en proceso de SharePoint: {e}")
        return False


if __name__ == "__main__":
    # Ejecutar directamente
    subir_excel_a_sharepoint()
