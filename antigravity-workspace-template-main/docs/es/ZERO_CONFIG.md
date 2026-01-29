# ⚡ Características Zero-Config

## 🎯 La Filosofía Zero-Config

**Detén la escritura de boilerplate.** El Antigravity Workspace automáticamente descubre y carga tus herramientas y contexto sin configuración manual.

## 🛠️ Descubrimiento Automático de Herramientas

Coloca cualquier archivo Python en `src/tools/` y el agente lo usará inmediatamente—sin imports, sin registro, sin boilerplate.

### Cómo Funciona

1. **Define tu Herramienta**:
```python
# src/tools/sentiment_analyzer.py
def analyze_sentiment(text: str) -> dict:
    """Analiza el sentimiento del texto dado.
    
    Args:
        text: El texto a analizar
        
    Returns:
        Un diccionario con puntuación de sentimiento y etiqueta
    """
    if len(text) > 10:
        return {"score": 0.8, "label": "positivo"}
    return {"score": 0.3, "label": "neutral"}
```

2. **Reinicia Agente** (una sola vez):
```bash
python src/agent.py
```

3. **Úsala Inmediatamente** en prompts:
```
"Analiza el sentimiento de estas reseñas de clientes..."
```

El agente descubrirá y usará automáticamente `analyze_sentiment()`.

## 📚 Carga Automática de Contexto

Agrega conocimiento a `.context/` y se inyecta automáticamente en cada prompt del agente—sin configuración necesaria.

### Cómo Funciona

1. **Crea Archivos de Conocimiento**:
```bash
# Crea directorio de contexto
mkdir -p .context

# Agrega tu conocimiento
echo "# Estándares de Codificación del Proyecto
- Usa docstrings estilo Google
- Anota con tipo todas las funciones
- Límite de 80 caracteres por línea" > .context/coding_standards.md

echo "# Documentación de API
## Endpoint de Usuario
GET /api/users - obtener todos los usuarios
POST /api/users - crear nuevo usuario" > .context/api_docs.md
```

2. **Reinicia Agente** (una sola vez):
```bash
python src/agent.py
```

3. **Inyección Automática**:
Cada prompt al agente ahora incluye automáticamente todos los archivos `.context/`.

### Organizar Contexto

**Estructura de Ejemplo**:
```
.context/
├── README.md                      # Índice de todo el contexto
├── estandares_empresa/
│   ├── estandares_codificacion.md # Guía de estilo de código
│   └── politicas_seguridad.md     # Requisitos de seguridad
├── informacion_proyecto/
│   ├── arquitectura.md            # Diseño del sistema
│   └── esquema_base_datos.md      # Estructura de BD
└── docs_api/
    ├── api_publica.md             # Endpoints públicos
    └── api_interna.md             # Endpoints internos
```

## 🔗 Cómo Trabajan Juntas Herramientas + Contexto

**Escenario**: Construyendo una herramienta de análisis de datos

### Paso 1: Agrega Contexto (Lo que el agente debe saber)
```bash
# .context/database_schema.md
## Tabla de Usuarios
- id (int): Clave primaria
- email (string): Email del usuario
- created_at (timestamp): Fecha de creación de cuenta
```

### Paso 2: Agrega Herramientas (Lo que el agente puede hacer)
```python
# src/tools/db_query.py
def query_users(email_pattern: str) -> list:
    """Consulta usuarios por patrón de email."""
    # Implementación
    return results
```

### Paso 3: Úsalo Naturalmente
```
"Encuentra todos los usuarios creados en el último mes con emails que coincidan con 'admin'"
```

El agente:
- 🧠 **Sabe** el esquema de base de datos (desde contexto)
- 🛠️ **Puede** consultar la base de datos (desde herramientas)
- ✅ **Hace** exactamente lo que necesitas

---

**Siguiente:** [Hoja de Ruta de Desarrollo](ROADMAP.md) | [Índice Completo](README.md)
