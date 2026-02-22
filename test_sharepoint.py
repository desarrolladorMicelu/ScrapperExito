"""
Script de prueba para verificar la conexión a SharePoint
Ejecutar: python test_sharepoint.py
"""

from sharepoint_uploader import SharePointUploader

def test_conexion():
    print("\n" + "="*60)
    print("TEST DE CONEXIÓN A SHAREPOINT")
    print("="*60 + "\n")
    
    try:
        uploader = SharePointUploader()
        
        print("✓ Configuración cargada:")
        print(f"  Tenant ID: {uploader.tenant_id[:8]}...")
        print(f"  Client ID: {uploader.client_id[:8]}...")
        print(f"  Site URL: {uploader.site_url}")
        print(f"  Folder: {uploader.folder_path}")
        print(f"  File: {uploader.file_name}\n")
        
        # Test 1: Autenticación
        print("Test 1: Autenticación con Microsoft Graph")
        if uploader.obtener_token():
            print("✓ Autenticación exitosa\n")
        else:
            print("❌ Error en autenticación")
            return False
        
        # Test 2: Obtener Site ID
        print("Test 2: Obtener Site ID de SharePoint")
        if uploader.obtener_site_id():
            print(f"✓ Site ID obtenido: {uploader.site_id}\n")
        else:
            print("❌ Error obteniendo Site ID")
            return False
        
        # Test 3: Verificar que existe iphones_exito.json
        import os
        if not os.path.exists('iphones_exito.json'):
            print("⚠ Advertencia: No existe iphones_exito.json")
            print("  Ejecuta el scraper primero o crea un archivo de prueba\n")
            return False
        
        print("✓ Archivo iphones_exito.json encontrado\n")
        
        # Test 4: Convertir a Excel
        print("Test 3: Convertir JSON a Excel")
        archivo_excel = uploader.convertir_json_a_excel()
        if archivo_excel:
            print(f"✓ Excel generado: {archivo_excel}\n")
        else:
            print("❌ Error generando Excel")
            return False
        
        # Test 5: Subir a SharePoint
        print("Test 4: Subir archivo a SharePoint")
        if uploader.subir_a_sharepoint(archivo_excel):
            print("✓ Archivo subido exitosamente\n")
        else:
            print("❌ Error subiendo archivo")
            return False
        
        # Limpiar archivo temporal
        try:
            os.remove(archivo_excel)
        except:
            pass
        
        print("="*60)
        print("✓ TODOS LOS TESTS PASARON")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error en test: {e}\n")
        return False

if __name__ == "__main__":
    test_conexion()
