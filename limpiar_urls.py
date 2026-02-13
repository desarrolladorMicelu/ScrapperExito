import json

# Leer JSON actual
with open('iphones_exito.json', 'r', encoding='utf-8') as f:
    productos = json.load(f)

# Limpiar URLs
productos_limpios = 0
for producto in productos:
    url = producto.get('url', '')
    
    if url and url != 'N/A':
        # Remover duplicado de dominio
        url_limpia = url.replace('https://www.exito.comhttps://tienda.exito.com', 'https://www.exito.com')
        url_limpia = url_limpia.replace('https://tienda.exito.com', '')
        
        if url != url_limpia:
            producto['url'] = url_limpia
            productos_limpios += 1

# Guardar JSON limpio
with open('iphones_exito.json', 'w', encoding='utf-8') as f:
    json.dump(productos, f, indent=2, ensure_ascii=False)

print(f"✓ URLs limpiadas: {productos_limpios}")
print(f"✓ Total productos: {len(productos)}")
print(f"✓ JSON actualizado: iphones_exito.json")
