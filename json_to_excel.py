import json
import pandas as pd
from datetime import datetime

# Leer JSON
with open('iphones_exito.json', 'r', encoding='utf-8') as f:
    productos = json.load(f)

# Convertir a formato plano para Excel
datos_excel = []

for producto in productos:
    fila = {
        'Nombre': producto.get('nombre'),
        'Código': producto.get('codigo'),
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

# Guardar en Excel
nombre_archivo = f'iphones_exito_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
df.to_excel(nombre_archivo, index=False, engine='openpyxl')

print(f"✓ Excel creado: {nombre_archivo}")
print(f"✓ Total productos: {len(datos_excel)}")
