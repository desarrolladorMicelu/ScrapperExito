import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup
import time
import re
import hashlib
from azure.communication.email import EmailClient
import boto3
from botocore.client import Config
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class ExitoScraper:
    def __init__(self, api_key, email_destinatario=None):
        self.api_key = api_key
        self.scraper_url = "http://api.scraperapi.com"
        self.data_file = "iphones_exito.json"
        self.cache_file = "cache_productos.json"
        self.historial_file = "historial_cambios.json"
        self.api_catalog = "https://www.exito.com/api/catalog_system/pub/products/search"
        
        # Configuración de email Azure
        self.connection_string = os.getenv('AZURE_EMAIL_CONNECTION_STRING')
        self.sender_address = os.getenv('AZURE_EMAIL_SENDER')
        self.email_destinatario = email_destinatario
        
        # Configuración Cloudflare R2
        self.r2_endpoint = os.getenv('CLOUDFLARE_R2_ENDPOINT_URL')
        self.r2_access_key = os.getenv('CLOUDFLARE_R2_ACCESS_KEY_ID')
        self.r2_secret_key = os.getenv('CLOUDFLARE_R2_SECRET_ACCESS_KEY')
        self.r2_bucket = os.getenv('CLOUDFLARE_R2_BUCKET_NAME')
        self.r2_public_url = os.getenv('CLOUDFLARE_R2_PUBLIC_URL')
        
        # Cliente S3 para R2
        self.r2_client = boto3.client(
            's3',
            endpoint_url=self.r2_endpoint,
            aws_access_key_id=self.r2_access_key,
            aws_secret_access_key=self.r2_secret_key,
            config=Config(signature_version='s3v4')
        )
        
        self.load_data()
        self.load_cache()
        self.load_historial()
        
        # Configuración de intervalos (en segundos)
        self.intervalo_criticos = 30 * 60      # 30 minutos
        self.intervalo_medios = 3 * 60 * 60    # 3 horas
        self.intervalo_bajos = 12 * 60 * 60    # 12 horas
    
    def load_data(self):
        """Carga datos existentes o crea estructura inicial"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.productos = json.load(f)
        except FileNotFoundError:
            self.productos = []
    
    def load_cache(self):
        """Carga cache de última actualización por producto"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
        except FileNotFoundError:
            self.cache = {}
    
    def load_historial(self):
        """Carga historial de cambios"""
        try:
            with open(self.historial_file, 'r', encoding='utf-8') as f:
                self.historial = json.load(f)
        except FileNotFoundError:
            self.historial = []
    
    def save_data(self):
        """Guarda datos en JSON local y sube a R2"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.productos, f, indent=2, ensure_ascii=False)
        
        # Subir a Cloudflare R2
        self.subir_a_r2(self.data_file, 'iphones_exito.json')
    
    def save_cache(self):
        """Guarda cache de actualizaciones"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2)
    
    def save_historial(self):
        """Guarda historial de cambios local y sube a R2"""
        with open(self.historial_file, 'w', encoding='utf-8') as f:
            json.dump(self.historial, f, indent=2, ensure_ascii=False)
        
        # Subir a Cloudflare R2
        self.subir_a_r2(self.historial_file, 'historial_cambios.json')
    
    def subir_a_r2(self, archivo_local, nombre_r2):
        """Sube archivo a Cloudflare R2"""
        try:
            self.r2_client.upload_file(
                archivo_local,
                self.r2_bucket,
                nombre_r2,
                ExtraArgs={'ContentType': 'application/json'}
            )
            print(f"✓ Subido a R2: {nombre_r2}")
        except Exception as e:
            print(f"⚠ Error subiendo a R2: {e}")
    
    def enviar_email_cambios(self, cambios_posicion):
        """Envía email con cambios de posición de Micelu"""
        if not self.email_destinatario or not cambios_posicion:
            return
        
        try:
            # Crear contenido HTML del email
            html_content = self.generar_html_email(cambios_posicion)
            
            # Configurar cliente de email
            email_client = EmailClient.from_connection_string(self.connection_string)
            
            # Preparar lista de destinatarios
            destinatarios = []
            if isinstance(self.email_destinatario, list):
                destinatarios = [{"address": email} for email in self.email_destinatario]
            else:
                destinatarios = [{"address": self.email_destinatario}]
            
            # Preparar mensaje
            message = {
                "senderAddress": self.sender_address,
                "recipients": {
                    "to": destinatarios
                },
                "content": {
                    "subject": f"Alerta: {len(cambios_posicion)} cambio(s) de posición - Éxito Marketplace",
                    "html": html_content
                }
            }
            
            # Enviar email
            poller = email_client.begin_send(message)
            result = poller.result()
            
            emails_str = ", ".join([d["address"] for d in destinatarios])
            print(f"\n✉ Email enviado a: {emails_str}")
            
        except Exception as e:
            print(f"\n⚠ Error enviando email: {e}")
    
    def generar_html_email(self, cambios):
        """Genera HTML profesional y minimalista para el email"""
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .header {{
            background-color: #4a5568;
            color: #ffffff;
            padding: 25px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 20px;
            font-weight: 600;
        }}
        .header p {{
            margin: 0;
            font-size: 13px;
            opacity: 0.9;
        }}
        .content {{
            padding: 20px;
        }}
        .cambio {{
            background-color: #faf8f5;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
            border-left: 4px solid #4a5568;
        }}
        .cambio.empeoro {{
            border-left-color: #dc3545;
            background-color: #faf8f5;
        }}
        .cambio.mejoro {{
            border-left-color: #28a745;
            background-color: #faf8f5;
        }}
        .producto-nombre {{
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 12px;
            line-height: 1.4;
        }}
        .posicion-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        .posicion-badge.empeoro {{
            background-color: #dc3545;
            color: #ffffff;
        }}
        .posicion-badge.mejoro {{
            background-color: #28a745;
            color: #ffffff;
        }}
        .posicion-badge.nuevo {{
            background-color: #4a5568;
            color: #ffffff;
        }}
        .info-grid {{
            display: table;
            width: 100%;
            margin: 12px 0;
        }}
        .info-row {{
            display: table-row;
        }}
        .info-label {{
            display: table-cell;
            padding: 8px 12px 8px 0;
            color: #7f8c8d;
            font-size: 13px;
            font-weight: 500;
            width: 40%;
        }}
        .info-valor {{
            display: table-cell;
            padding: 8px 0;
            color: #2c3e50;
            font-size: 14px;
            font-weight: 600;
        }}
        .btn-producto {{
            display: inline-block;
            margin-top: 12px;
            padding: 10px 20px;
            background-color: #4a5568;
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
        }}
        .footer {{
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #95a5a6;
            border-top: 1px solid #ecf0f1;
        }}
        @media only screen and (max-width: 600px) {{
            body {{
                padding: 10px;
            }}
            .header {{
                padding: 20px 15px;
            }}
            .header h1 {{
                font-size: 18px;
            }}
            .content {{
                padding: 15px;
            }}
            .cambio {{
                padding: 15px;
            }}
            .producto-nombre {{
                font-size: 15px;
            }}
            .info-label {{
                font-size: 12px;
                width: 45%;
            }}
            .info-valor {{
                font-size: 13px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Cambios de Posición - Éxito Marketplace</h1>
            <p>Micelu · {fecha_actual}</p>
        </div>
        <div class="content">
"""
        
        for cambio in cambios:
            pos_anterior = cambio.get('micelu_posicion_anterior')
            pos_nueva = cambio.get('micelu_posicion_nuevo')
            
            # Determinar clase y texto
            if pos_anterior is None:
                clase_cambio = "nuevo"
                texto_cambio = f"Posición: #{pos_nueva}"
                clase_badge = "nuevo"
            elif pos_nueva is None:
                clase_cambio = "empeoro"
                texto_cambio = "Sin posición"
                clase_badge = "empeoro"
            elif pos_nueva < pos_anterior:
                clase_cambio = "mejoro"
                texto_cambio = f"Top #{pos_anterior} → Top #{pos_nueva}"
                clase_badge = "mejoro"
            else:
                clase_cambio = "empeoro"
                texto_cambio = f"Top #{pos_anterior} → Top #{pos_nueva}"
                clase_badge = "empeoro"
            
            html += f"""
            <div class="cambio {clase_cambio}">
                <div class="producto-nombre">{cambio.get('producto')}</div>
                <span class="posicion-badge {clase_badge}">{texto_cambio}</span>
                
                <div class="info-grid">
                    <div class="info-row">
                        <div class="info-label">Precio Micelu:</div>
                        <div class="info-valor">{cambio.get('micelu_precio_nuevo') or 'N/A'}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">Precio Top #1:</div>
                        <div class="info-valor">{cambio.get('posicion_1_nuevo')}</div>
                    </div>
                </div>
                
                <a href="{cambio.get('url')}" class="btn-producto">Ver en Éxito</a>
            </div>
"""
        
        html += """
        </div>
        <div class="footer">
            <p>Sistema de Monitoreo Automático · Micelu</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def clasificar_producto(self, producto):
        """Clasifica producto según prioridad basado en posición de Micelu"""
        if not producto.get('micelu', {}).get('existe'):
            return 'bajo'  # Micelu no aparece
        
        posicion = producto['micelu'].get('posicion', 999)
        
        if posicion <= 3:
            return 'critico'  # Top 3
        elif posicion <= 10:
            return 'medio'    # Top 4-10
        else:
            return 'bajo'     # Más de top 10
    
    def necesita_actualizacion(self, codigo, prioridad):
        """Determina si un producto necesita ser actualizado según su prioridad"""
        ahora = time.time()
        
        # Obtener última actualización
        ultima_actualizacion = self.cache.get(codigo, 0)
        tiempo_transcurrido = ahora - ultima_actualizacion
        
        # Determinar intervalo según prioridad
        if prioridad == 'critico':
            return tiempo_transcurrido >= self.intervalo_criticos
        elif prioridad == 'medio':
            return tiempo_transcurrido >= self.intervalo_medios
        else:  # bajo
            return tiempo_transcurrido >= self.intervalo_bajos
    
    def calcular_hash_producto(self, producto_json):
        """Calcula hash del producto para detectar cambios sin procesar todo"""
        try:
            items = producto_json.get('items', [])
            if not items:
                return None
            
            sellers = items[0].get('sellers', [])
            sellers_data = []
            
            for seller in sellers:
                offer = seller.get('commertialOffer', {})
                precio = offer.get('Price') or offer.get('ListPrice')
                disponible = offer.get('AvailableQuantity', 0)
                
                if precio and disponible > 0:
                    sellers_data.append({
                        'seller': seller.get('sellerName', '').lower(),
                        'price': precio
                    })
            
            sellers_data.sort(key=lambda x: x['price'])
            hash_string = json.dumps(sellers_data, sort_keys=True)
            return hashlib.md5(hash_string.encode()).hexdigest()
        except:
            return None
    
    def cargar_productos_monitorear(self):
        """Carga lista de productos a monitorear desde R2"""
        try:
            # Descargar de R2
            self.r2_client.download_file(
                self.r2_bucket,
                'productos_monitorear.json',
                'productos_monitorear_temp.json'
            )
            
            with open('productos_monitorear_temp.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            import os
            os.remove('productos_monitorear_temp.json')
            
            return data.get('productos', [])
        except:
            # Si no existe, retornar lista vacía
            return []
    
    def buscar_producto_individual(self, producto_config, headers):
        """Busca un producto individual (para paralelización)"""
        ean = producto_config.get('ean', '')
        nombre = producto_config.get('nombre', '')
        
        # Intentar buscar por EAN primero
        producto_encontrado = None
        
        if ean:
            url_api = f"{self.api_catalog}/{ean}"
            try:
                response = requests.get(url_api, headers=headers, timeout=30)
                response.raise_for_status()
                productos = response.json()
                
                if productos and len(productos) > 0:
                    producto_encontrado = productos[0]
            except:
                pass
        
        # Si no se encontró por EAN, buscar por nombre
        if not producto_encontrado and nombre:
            nombre_busqueda = nombre.replace(' ', '%20')
            url_api = f"{self.api_catalog}/{nombre_busqueda}"
            
            try:
                response = requests.get(url_api, headers=headers, timeout=30)
                response.raise_for_status()
                productos = response.json()
                
                if productos and len(productos) > 0:
                    producto_encontrado = productos[0]
            except:
                pass
        
        if producto_encontrado:
            # Agregar info de OFIM al producto
            producto_encontrado['codigo_ofim'] = producto_config.get('codigo_ofim', '')
            producto_encontrado['color_ofim'] = producto_config.get('color_ofim', '')
            return producto_encontrado
        
        return None
    
    def obtener_productos_api(self):
        """Obtiene productos desde la API pública de Éxito con paralelización"""
        print(f"\n{'='*60}")
        print(f"Obteniendo productos desde API de Éxito")
        print(f"{'='*60}\n")
        
        # Cargar productos a monitorear
        productos_monitorear = self.cargar_productos_monitorear()
        
        if not productos_monitorear:
            print("⚠ No hay productos configurados para monitorear")
            print("  Sube un Excel desde la página web para comenzar")
            return []
        
        print(f"📋 {len(productos_monitorear)} productos configurados")
        print(f"🚀 Procesando con paralelización (10 threads)...\n")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'es-CO,es;q=0.9'
        }
        
        productos_api = []
        encontrados = 0
        no_encontrados = 0
        
        # Procesar en paralelo con ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Enviar todas las tareas
            futures = {
                executor.submit(self.buscar_producto_individual, prod, headers): prod 
                for prod in productos_monitorear
            }
            
            # Procesar resultados a medida que completan
            for future in as_completed(futures):
                producto_config = futures[future]
                try:
                    resultado = future.result()
                    if resultado:
                        productos_api.append(resultado)
                        encontrados += 1
                        print(f"✓ {encontrados}/{len(productos_monitorear)} - {producto_config.get('nombre', 'N/A')[:50]}")
                    else:
                        no_encontrados += 1
                        print(f"✗ No encontrado: {producto_config.get('nombre', 'N/A')[:50]}")
                except Exception as e:
                    no_encontrados += 1
                    print(f"✗ Error: {producto_config.get('nombre', 'N/A')[:50]}")
        
        # Eliminar duplicados por productId
        productos_unicos = {}
        for p in productos_api:
            prod_id = p.get('productId')
            if prod_id and prod_id not in productos_unicos:
                productos_unicos[prod_id] = p
        
        print(f"\n{'='*60}")
        print(f"✓ Encontrados: {encontrados}")
        print(f"✗ No encontrados: {no_encontrados}")
        print(f"📦 Total únicos: {len(productos_unicos)}")
        print(f"{'='*60}\n")
        
        return list(productos_unicos.values())

    def es_iphone_valido(self, nombre):
        """Verifica si el producto es un iPhone real (no accesorio)"""
        nombre_lower = nombre.lower()
        
        # Debe contener "iphone"
        if 'iphone' not in nombre_lower:
            return False
        
        # Excluir accesorios y cases
        palabras_excluir = [
            'case', 'carcasa', 'funda', 'protector', 'vidrio', 'mica',
            'cable', 'cargador', 'audifono', 'airpod', 'earpod',
            'correa', 'banda', 'watch', 'iwatch', 'apple watch',
            'adaptador', 'soporte', 'base', 'holder', 'grip',
            'skin', 'sticker', 'lamina', 'film', 'cover',
            'auricular', 'manos libres', 'bluetooth', 'parlante',
            'bateria', 'power bank', 'cargador inalambrico',
            'tom lambert', 'tomlambert', 'spigen', 'otterbox',
            'kit', 'combo', 'paquete', 'accesorio'
        ]
        
        for palabra in palabras_excluir:
            if palabra in nombre_lower:
                return False
        
        # Debe tener indicadores de ser un iPhone real
        # Buscar patrones como: "128gb", "256gb", "pro", "max", "plus", colores
        indicadores_validos = [
            'gb', 'pro', 'max', 'plus', 'mini',
            'negro', 'blanco', 'azul', 'rojo', 'verde', 'morado', 'rosa',
            'amarillo', 'dorado', 'plateado', 'grafito', 'oro', 'plata',
            'medianoche', 'estelar', 'espacial', 'titanio',
            'reacondicionado', 'nuevo', 'sellado'
        ]
        
        tiene_indicador = any(indicador in nombre_lower for indicador in indicadores_validos)
        
        return tiene_indicador
    
    def extraer_info_producto(self, producto_json):
        """Extrae información relevante del JSON de producto incluyendo posición #1 y Micelu"""
        try:
            nombre = producto_json.get('productName', 'N/A')
            
            # FILTRO: Verificar que sea un iPhone válido
            if not self.es_iphone_valido(nombre):
                return None
            
            link = producto_json.get('link', '')
            product_id = producto_json.get('productId', 'N/A')
            
            items = producto_json.get('items', [])
            vendedores_info = []
            
            if items and len(items) > 0:
                sellers = items[0].get('sellers', [])
                
                for seller in sellers:
                    comercial_offer = seller.get('commertialOffer', {})
                    disponible = comercial_offer.get('AvailableQuantity', 0)
                    if disponible <= 0:
                        continue
                    
                    precio_valor = comercial_offer.get('Price')
                    if precio_valor is None:
                        precio_valor = comercial_offer.get('ListPrice')
                    
                    if precio_valor and precio_valor > 0:
                        vendedor_nombre = seller.get('sellerName', 'Desconocido').lower()
                        vendedores_info.append({
                            'nombre': vendedor_nombre,
                            'precio': precio_valor,
                            'precio_formateado': f"${precio_valor:,.0f}".replace(',', '.')
                        })
            
            if not vendedores_info:
                return None
            
            vendedores_info.sort(key=lambda x: x['precio'])
            posicion_1 = vendedores_info[0]
            
            # Buscar Micelu
            micelu_info = None
            micelu_posicion = None
            
            for i, vendedor in enumerate(vendedores_info, 1):
                if 'micelu' in vendedor['nombre']:
                    micelu_info = vendedor
                    micelu_posicion = i
                    break
            
            # Calcular diferencia
            diferencia_precio = None
            diferencia_porcentaje = None
            
            if micelu_info:
                diferencia_precio = micelu_info['precio'] - posicion_1['precio']
                if posicion_1['precio'] > 0:
                    diferencia_porcentaje = (diferencia_precio / posicion_1['precio']) * 100
            
            # Limpiar URL
            url_limpia = "N/A"
            if link:
                # Remover https://tienda.exito.com si existe
                link_limpio = link.replace('https://tienda.exito.com', '')
                # Construir URL correcta
                url_limpia = f"https://www.exito.com{link_limpio}"
            
            return {
                'nombre': nombre,
                'codigo': product_id,
                'codigo_ofim': producto_json.get('codigo_ofim', ''),
                'color_ofim': producto_json.get('color_ofim', ''),
                'url': url_limpia,
                'fecha_consulta': datetime.now().isoformat(),
                'fecha_actualizacion': None,  # Se actualiza solo cuando hay cambios
                'total_vendedores': len(vendedores_info),
                'posicion_1': {
                    'vendedor': posicion_1['nombre'],
                    'precio': posicion_1['precio_formateado'],
                    'precio_numerico': posicion_1['precio']
                },
                'micelu': {
                    'existe': micelu_info is not None,
                    'posicion': micelu_posicion,
                    'precio': micelu_info['precio_formateado'] if micelu_info else None,
                    'precio_numerico': micelu_info['precio'] if micelu_info else None,
                    'diferencia_vs_posicion1': f"${diferencia_precio:,.0f}".replace(',', '.') if diferencia_precio else None,
                    'diferencia_porcentaje': f"{diferencia_porcentaje:.1f}%" if diferencia_porcentaje else None
                }
            }
        except Exception as e:
            print(f"  ⚠ Error extrayendo info: {e}")
            return None
    
    def buscar_iphones_inteligente(self):
        """Busca iPhones con estrategia inteligente basada en prioridades"""
        print(f"\n{'='*60}")
        print(f"SCRAPING INTELIGENTE - EXITO.COM")
        print(f"{'='*60}\n")
        
        # Obtener productos de la API (ya optimizado con paralelización)
        print("📡 Consultando API de Éxito...")
        productos_api = self.obtener_productos_api()
        
        if not productos_api:
            print("⚠ No se obtuvieron productos")
            return []
        
        print(f"✓ {len(productos_api)} productos obtenidos\n")
        
        # Procesar productos con cache inteligente
        productos_procesados = []
        productos_actualizados = 0
        productos_skip = 0
        
        print("🔄 Procesando con cache inteligente...")
        
        # Procesar en lotes de 100 para no sobrecargar memoria
        batch_size = 100
        for i in range(0, len(productos_api), batch_size):
            batch = productos_api[i:i+batch_size]
            
            for prod_json in batch:
                codigo = prod_json.get('productId')
                if not codigo:
                    continue
                
                # Buscar producto existente
                producto_existente = next((p for p in self.productos if p.get('codigo') == codigo), None)
                
                if producto_existente:
                    # Clasificar por prioridad
                    prioridad = self.clasificar_producto(producto_existente)
                    
                    # Verificar si necesita actualización
                    if not self.necesita_actualizacion(codigo, prioridad):
                        productos_skip += 1
                        productos_procesados.append(producto_existente)
                        continue
                    
                    # Verificar hash para detectar cambios
                    hash_nuevo = self.calcular_hash_producto(prod_json)
                    hash_anterior = self.cache.get(f"{codigo}_hash")
                    
                    if hash_nuevo and hash_nuevo == hash_anterior:
                        # No cambió, usar cache
                        productos_skip += 1
                        productos_procesados.append(producto_existente)
                        self.cache[codigo] = time.time()
                        continue
                    
                    # Guardar nuevo hash
                    if hash_nuevo:
                        self.cache[f"{codigo}_hash"] = hash_nuevo
                
                # Procesar producto (nuevo o cambió)
                info = self.extraer_info_producto(prod_json)
                if info:
                    productos_procesados.append(info)
                    productos_actualizados += 1
                    self.cache[codigo] = time.time()
        
        print(f"\n📊 Estadísticas:")
        print(f"   Actualizados: {productos_actualizados}")
        print(f"   Desde cache: {productos_skip}")
        print(f"   Total: {len(productos_procesados)}\n")
        
        return productos_procesados

    def actualizar_productos(self, nuevos_productos):
        """Actualiza productos existentes o agrega nuevos"""
        cambios = []
        cambios_posicion_micelu = []  # Para email
        fecha_actual = datetime.now().isoformat()
        
        for nuevo in nuevos_productos:
            encontrado = False
            
            for i, existente in enumerate(self.productos):
                if existente.get('codigo') == nuevo['codigo']:
                    encontrado = True
                    
                    # Verificar cambios
                    cambio_pos1 = existente.get('posicion_1', {}).get('precio_numerico') != nuevo['posicion_1']['precio_numerico']
                    cambio_micelu = False
                    cambio_posicion_micelu = False
                    
                    if nuevo['micelu']['existe']:
                        if not existente.get('micelu', {}).get('existe'):
                            cambio_micelu = True
                            cambio_posicion_micelu = True  # Micelu apareció
                        elif existente.get('micelu', {}).get('precio_numerico') != nuevo['micelu']['precio_numerico']:
                            cambio_micelu = True
                        elif existente.get('micelu', {}).get('posicion') != nuevo['micelu']['posicion']:
                            cambio_micelu = True
                            cambio_posicion_micelu = True  # Cambió de posición
                    elif existente.get('micelu', {}).get('existe'):
                        cambio_micelu = True
                        cambio_posicion_micelu = True  # Micelu desapareció
                    
                    if cambio_pos1 or cambio_micelu:
                        # SOLO registrar en historial si Micelu cambió de posición
                        if cambio_posicion_micelu:
                            registro_historial = {
                                'producto': nuevo['nombre'],
                                'codigo': nuevo['codigo'],
                                'url': nuevo['url'],
                                'fecha': fecha_actual,
                                'posicion_1_anterior': existente.get('posicion_1', {}).get('precio'),
                                'posicion_1_nuevo': nuevo['posicion_1']['precio'],
                                'micelu_posicion_anterior': existente.get('micelu', {}).get('posicion'),
                                'micelu_posicion_nuevo': nuevo['micelu']['posicion'],
                                'micelu_precio_anterior': existente.get('micelu', {}).get('precio'),
                                'micelu_precio_nuevo': nuevo['micelu']['precio'],
                                'tipo_cambio': 'Cambio de posición Micelu'
                            }
                            self.historial.append(registro_historial)
                            cambios_posicion_micelu.append(registro_historial)  # Para email
                        
                        # Preparar reporte de cambios (se reporta todo)
                        cambios.append({
                            'producto': nuevo['nombre'],
                            'tipo_cambio': [],
                            'anterior': {
                                'posicion_1': existente.get('posicion_1', {}),
                                'micelu': existente.get('micelu', {})
                            },
                            'nuevo': {
                                'posicion_1': nuevo['posicion_1'],
                                'micelu': nuevo['micelu']
                            },
                            'fecha': fecha_actual
                        })
                        
                        if cambio_pos1:
                            cambios[-1]['tipo_cambio'].append('Posición #1')
                        if cambio_micelu:
                            cambios[-1]['tipo_cambio'].append('Micelu')
                        
                        # Actualizar producto con fecha de actualización
                        nuevo['fecha_actualizacion'] = fecha_actual
                        self.productos[i] = nuevo
                    else:
                        # Sin cambios, mantener fecha_actualizacion anterior
                        nuevo['fecha_actualizacion'] = existente.get('fecha_actualizacion')
                        self.productos[i] = nuevo
                    break
            
            if not encontrado:
                # Producto nuevo
                nuevo['fecha_actualizacion'] = fecha_actual
                self.productos.append(nuevo)
                
                # SOLO registrar en historial si Micelu existe en el producto nuevo
                if nuevo['micelu']['existe']:
                    registro_historial = {
                        'producto': nuevo['nombre'],
                        'codigo': nuevo['codigo'],
                        'url': nuevo['url'],
                        'fecha': fecha_actual,
                        'posicion_1_anterior': 'NUEVO',
                        'posicion_1_nuevo': nuevo['posicion_1']['precio'],
                        'micelu_posicion_anterior': None,
                        'micelu_posicion_nuevo': nuevo['micelu']['posicion'],
                        'micelu_precio_anterior': None,
                        'micelu_precio_nuevo': nuevo['micelu']['precio'],
                        'tipo_cambio': 'Producto nuevo con Micelu'
                    }
                    self.historial.append(registro_historial)
                    cambios_posicion_micelu.append(registro_historial)  # Para email
                
                cambios.append({
                    'producto': nuevo['nombre'],
                    'tipo_cambio': ['NUEVO'],
                    'anterior': None,
                    'nuevo': {
                        'posicion_1': nuevo['posicion_1'],
                        'micelu': nuevo['micelu']
                    },
                    'fecha': fecha_actual
                })
        
        return cambios, cambios_posicion_micelu
    
    def reportar_cambios(self, cambios):
        """Reporta cambios detectados de forma clara"""
        if not cambios:
            print("\n✓ Sin cambios detectados")
            return
        
        print("\n🔔 CAMBIOS DETECTADOS:")
        print("="*60)
        
        for cambio in cambios:
            print(f"\n📱 {cambio['producto']}")
            print(f"   Cambios en: {', '.join(cambio['tipo_cambio'])}")
            
            if 'NUEVO' not in cambio['tipo_cambio']:
                if 'Posición #1' in cambio['tipo_cambio']:
                    ant_pos1 = cambio['anterior']['posicion_1']
                    new_pos1 = cambio['nuevo']['posicion_1']
                    print(f"\n   Posición #1:")
                    print(f"   Antes: {ant_pos1.get('vendedor')} - {ant_pos1.get('precio')}")
                    print(f"   Ahora: {new_pos1['vendedor']} - {new_pos1['precio']}")
                
                if 'Micelu' in cambio['tipo_cambio']:
                    ant_micelu = cambio['anterior']['micelu']
                    new_micelu = cambio['nuevo']['micelu']
                    print(f"\n   Micelu:")
                    
                    if not ant_micelu.get('existe') and new_micelu['existe']:
                        print(f"   ✓ APARECIÓ en posición #{new_micelu['posicion']}")
                        print(f"   Precio: {new_micelu['precio']}")
                    elif ant_micelu.get('existe') and not new_micelu['existe']:
                        print(f"   ✗ DESAPARECIÓ (antes en pos #{ant_micelu.get('posicion')})")
                    else:
                        if ant_micelu.get('posicion') != new_micelu['posicion']:
                            print(f"   Posición: #{ant_micelu.get('posicion')} → #{new_micelu['posicion']}")
                        if ant_micelu.get('precio') != new_micelu['precio']:
                            print(f"   Precio: {ant_micelu.get('precio')} → {new_micelu['precio']}")
                        print(f"   Diferencia vs #1: {new_micelu['diferencia_vs_posicion1']} ({new_micelu['diferencia_porcentaje']})")
            else:
                new_pos1 = cambio['nuevo']['posicion_1']
                new_micelu = cambio['nuevo']['micelu']
                print(f"   Posición #1: {new_pos1['vendedor']} - {new_pos1['precio']}")
                if new_micelu['existe']:
                    print(f"   Micelu: Pos #{new_micelu['posicion']} - {new_micelu['precio']}")
                    print(f"   Diferencia: {new_micelu['diferencia_vs_posicion1']} ({new_micelu['diferencia_porcentaje']})")
                else:
                    print(f"   Micelu: No disponible")
        
        print(f"\n{'='*60}")
    
    def mostrar_resumen_prioridades(self):
        """Muestra resumen de productos por prioridad"""
        criticos = [p for p in self.productos if self.clasificar_producto(p) == 'critico']
        medios = [p for p in self.productos if self.clasificar_producto(p) == 'medio']
        bajos = [p for p in self.productos if self.clasificar_producto(p) == 'bajo']
        
        print(f"\n📊 RESUMEN DE PRIORIDADES:")
        print(f"   🔴 Críticos (Top 1-3): {len(criticos)} productos - cada 30 min")
        print(f"   🟡 Medios (Top 4-10): {len(medios)} productos - cada 3 horas")
        print(f"   🟢 Bajos (sin Micelu): {len(bajos)} productos - cada 12 horas")
    
    def monitorear_inteligente(self):
        """Monitoreo inteligente con intervalos adaptativos"""
        print(f"\n{'='*60}")
        print(f"MONITOREO INTELIGENTE INICIADO")
        print(f"{'='*60}")
        print(f"Estrategia:")
        print(f"  🔴 Críticos: cada 30 minutos")
        print(f"  🟡 Medios: cada 3 horas")
        print(f"  🟢 Bajos: cada 12 horas")
        print(f"{'='*60}\n")
        
        ciclo = 0
        
        while True:
            try:
                ciclo += 1
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ciclo #{ciclo}")
                
                # Scraping inteligente
                nuevos_productos = self.buscar_iphones_inteligente()
                
                if nuevos_productos:
                    # Detectar cambios
                    cambios, cambios_posicion = self.actualizar_productos(nuevos_productos)
                    
                    # Guardar datos, cache y historial
                    self.save_data()
                    self.save_cache()
                    self.save_historial()
                    
                    # Enviar email si hay cambios de posición
                    if cambios_posicion:
                        self.enviar_email_cambios(cambios_posicion)
                    
                    # Reportar
                    self.reportar_cambios(cambios)
                    self.mostrar_resumen_prioridades()
                else:
                    print("⚠ No se encontraron productos")
                
                # Próximo ciclo en 30 minutos (para revisar críticos)
                print(f"\n⏰ Próximo ciclo en 30 minutos...")
                time.sleep(30 * 60)
                
            except KeyboardInterrupt:
                print("\n\n✋ Monitoreo detenido por el usuario")
                break
            except Exception as e:
                print(f"\n❌ Error en monitoreo: {e}")
                print("⏰ Reintentando en 5 minutos...")
                time.sleep(5 * 60)

if __name__ == "__main__":
    API_KEY = os.getenv('SCRAPER_API_KEY')
    EMAILS_ADMIN = [os.getenv('EMAIL_ADMIN_1'), os.getenv('EMAIL_ADMIN_2')]
    
    scraper = ExitoScraper(API_KEY, email_destinatario=EMAILS_ADMIN)
    scraper.monitorear_inteligente()
