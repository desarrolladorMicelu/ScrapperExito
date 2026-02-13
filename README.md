# Monitor de Precios Micelu - Éxito Marketplace

Sistema completo de monitoreo de precios con gestión por Excel.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

### Opción 1: Todo en uno (RECOMENDADO)

Corre Flask + Scraper juntos:

```bash
python start.py
```

Esto inicia:
- ✅ Servidor web en http://localhost:5000
- ✅ Scraper monitoreando automáticamente

### Opción 2: Por separado

**Terminal 1 - Flask:**
```bash
python app.py
```

**Terminal 2 - Scraper:**
```bash
python scraper_exito.py
```

## Cómo usar

1. **Abre** http://localhost:5000
2. **Sube** tu Excel con columnas:
   - EAN
   - Nombre del Producto
   - Codigo OFIM
   - Color OFIM
3. **Listo** - El sistema scrapea automáticamente

## Desplegar en Railway

1. Sube el proyecto a GitHub
2. Conecta Railway a tu repo
3. Railway detecta Python automáticamente
4. Configura comando de inicio: `python start.py`
5. Actualiza `API_URL` en `index.html` con tu URL de Railway
6. Deploy

## Archivos importantes

- `start.py` - Inicia todo el sistema
- `app.py` - Servidor Flask (subir Excel)
- `scraper_exito.py` - Scraper de monitoreo
- `index.html` - Página web
- `requirements.txt` - Dependencias

## Cómo funciona

```
1. Subes Excel → Flask procesa → JSON a R2
2. Scraper lee JSON de R2
3. Busca productos por EAN/nombre
4. Extrae precios y posiciones
5. Detecta cambios
6. Envía emails si hay cambios
7. Sube resultados a R2
8. Página web muestra datos actualizados
```

## Características

- ✅ Monitoreo automático cada 30min/3h/12h según prioridad
- ✅ Detección de cambios de posición
- ✅ Emails automáticos
- ✅ Historial de cambios
- ✅ Gestión por Excel
- ✅ Página web en tiempo real
- ✅ Exportar a Excel
