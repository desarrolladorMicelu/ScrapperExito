import json
import pandas as pd
from datetime import datetime

# Leer historial
try:
    with open('historial_cambios.json', 'r', encoding='utf-8') as f:
        historial = json.load(f)
except FileNotFoundError:
    print("❌ No existe historial_cambios.json todavía")
    exit()

if not historial:
    print("⚠ El historial está vacío")
    exit()

# Convertir a formato Excel
datos_excel = []

for cambio in historial:
    fila = {
        'Producto': cambio.get('producto'),
        'Código': cambio.get('codigo'),
        'URL': cambio.get('url'),
        'Fecha': cambio.get('fecha'),
        'Tipo Cambio': cambio.get('tipo_cambio'),
        'Micelu Top Anterior': cambio.get('micelu_posicion_anterior'),
        'Micelu Top Nuevo': cambio.get('micelu_posicion_nuevo'),
        'Micelu Precio Anterior': cambio.get('micelu_precio_anterior'),
        'Micelu Precio Nuevo': cambio.get('micelu_precio_nuevo'),
        'Pos1 Precio Anterior': cambio.get('posicion_1_anterior'),
        'Pos1 Precio Nuevo': cambio.get('posicion_1_nuevo')
    }
    datos_excel.append(fila)

# Crear DataFrame
df = pd.DataFrame(datos_excel)

# Guardar en Excel
nombre_archivo = f'historial_cambios_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
df.to_excel(nombre_archivo, index=False, engine='openpyxl')

print(f"✓ Excel creado: {nombre_archivo}")
print(f"✓ Total cambios de posición Micelu: {len(datos_excel)}")

