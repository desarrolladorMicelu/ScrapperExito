from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import json
import boto3
from botocore.client import Config
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__, static_folder='.')
CORS(app)

# Configuración Cloudflare R2
R2_ENDPOINT = os.getenv('CLOUDFLARE_R2_ENDPOINT_URL')
R2_ACCESS_KEY = os.getenv('CLOUDFLARE_R2_ACCESS_KEY_ID')
R2_SECRET_KEY = os.getenv('CLOUDFLARE_R2_SECRET_ACCESS_KEY')
R2_BUCKET = os.getenv('CLOUDFLARE_R2_BUCKET_NAME')

# Cliente S3 para R2
r2_client = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4')
)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/upload-excel', methods=['POST'])
def upload_excel():
    """Recibe Excel, lo convierte a JSON y sube a R2"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió archivo'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Archivo vacío'}), 400
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Solo se permiten archivos Excel'}), 400
        
        # Leer Excel
        df = pd.read_excel(file)
        
        # Limpiar nombres de columnas (quitar espacios extra)
        df.columns = df.columns.str.strip()
        
        print(f"Columnas encontradas: {list(df.columns)}")
        
        # Mapeo flexible de columnas
        columnas_map = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'ean' in col_lower:
                columnas_map['ean'] = col
            elif 'nombre' in col_lower and 'producto' in col_lower:
                columnas_map['nombre'] = col
            elif 'codigo' in col_lower and 'ofim' in col_lower:
                columnas_map['codigo_ofim'] = col
            elif 'color' in col_lower and 'ofim' in col_lower:
                columnas_map['color_ofim'] = col
        
        # Validar que se encontraron todas las columnas
        requeridas = ['ean', 'nombre', 'codigo_ofim', 'color_ofim']
        faltantes = [r for r in requeridas if r not in columnas_map]
        
        if faltantes:
            return jsonify({
                'error': f'No se encontraron columnas: {", ".join(faltantes)}',
                'columnas_encontradas': list(df.columns)
            }), 400
        
        # Convertir a lista de productos
        productos = []
        for _, row in df.iterrows():
            producto = {
                'ean': str(row[columnas_map['ean']]).strip(),
                'nombre': str(row[columnas_map['nombre']]).strip(),
                'codigo_ofim': str(row[columnas_map['codigo_ofim']]).strip(),
                'color_ofim': str(row[columnas_map['color_ofim']]).strip()
            }
            productos.append(producto)
        
        # Crear JSON
        productos_json = {
            'productos': productos,
            'total': len(productos),
            'fecha_actualizacion': pd.Timestamp.now().isoformat()
        }
        
        # Guardar localmente
        with open('productos_monitorear.json', 'w', encoding='utf-8') as f:
            json.dump(productos_json, f, indent=2, ensure_ascii=False)
        
        # Subir a R2
        r2_client.upload_file(
            'productos_monitorear.json',
            R2_BUCKET,
            'productos_monitorear.json',
            ExtraArgs={'ContentType': 'application/json'}
        )
        
        return jsonify({
            'success': True,
            'message': f'{len(productos)} productos cargados correctamente',
            'productos': len(productos)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/productos-actuales', methods=['GET'])
def productos_actuales():
    """Obtiene la lista actual de productos desde R2"""
    try:
        # Descargar de R2
        r2_client.download_file(
            R2_BUCKET,
            'productos_monitorear.json',
            'productos_monitorear_temp.json'
        )
        
        with open('productos_monitorear_temp.json', 'r', encoding='utf-8') as f:
            productos = json.load(f)
        
        os.remove('productos_monitorear_temp.json')
        
        return jsonify(productos)
        
    except Exception as e:
        return jsonify({'error': str(e), 'productos': []}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
