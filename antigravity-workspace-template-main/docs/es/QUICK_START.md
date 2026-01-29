# 🚀 Guía de Inicio Rápido

Comienza a usar la Plantilla Workspace de Antigravity en minutos.

## 📋 Requisitos Previos

- Python 3.9+
- pip o conda
- Git

## 🏃 Desarrollo Local

### 1. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 2. Ejecutar el Agente
```bash
python src/agent.py
```

El agente se iniciará y esperará tus comandos. Automáticamente:
- 🧠 Carga la memoria desde `agent_memory.json`
- 🛠️ Descubre herramientas en `src/tools/`
- 📚 Ingiere contexto desde `.context/`

### 3. Ejemplo de Uso
```bash
# En tu terminal o IDE:
> "Construye una función Python para calcular números Fibonacci"
```

El agente:
1. 📄 Crea un plan en `artifacts/plan_[id].md`
2. 💻 Escribe código en directorios apropiados
3. ✅ Proporciona logs de evidencia

## 🐳 Despliegue con Docker

### Compilar y Ejecutar
```bash
docker-compose up --build
```

Esto:
- Instala todas las dependencias
- Inicia el agente en un entorno containerizado
- Monta tu workspace para edición de código en vivo

Accede al agente mediante la interfaz expuesta.

### Personalizar Docker
Edita `docker-compose.yml` para:
- Cambiar variables de entorno
- Montar volúmenes adicionales
- Exponer diferentes puertos

## 🔧 Configuración

### Variables de Entorno
Crea un archivo `.env`:

```bash
# Configuración de LLM
GEMINI_API_KEY=tu-clave-api-aqui
GEMINI_MODEL=gemini-2.0-flash

# Configuración de MCP
MCP_ENABLED=true

# Configuración personalizada
LOG_LEVEL=INFO
ARTIFACTS_DIR=artifacts
```

### Gestión de Memoria
El agente gestiona automáticamente la memoria mediante `agent_memory.json`. Para reiniciar:

```bash
rm agent_memory.json
python src/agent.py
```

## 📁 Referencia de Estructura del Proyecto

```
├── src/
│   ├── agent.py         # Bucle principal del agente
│   ├── config.py        # Gestión de configuración
│   ├── memory.py        # Motor de memoria
│   ├── agents/          # Agentes especialistas
│   └── tools/           # Implementaciones de herramientas
├── artifacts/           # Artefactos de salida
├── .context/            # Base de conocimiento
└── .antigravity/        # Reglas de Antigravity
```

Consulta [Estructura del Proyecto](../README.md#project-structure) para detalles.

## 🧪 Ejecutar Pruebas

```bash
# Ejecutar todas las pruebas
pytest

# Ejecutar prueba específica
pytest tests/test_agent.py -v

# Con cobertura
pytest --cov=src tests/
```

## 🐛 Solución de Problemas

### El agente no se inicia
```bash
# Verifica si las dependencias están instaladas
pip list | grep -i google-generativeai

# Verifica que GEMINI_API_KEY esté configurada
echo $GEMINI_API_KEY
```

### Las herramientas no cargan
```bash
# Verifica que src/tools/ tenga archivos Python válidos
ls -la src/tools/

# Verifica errores de sintaxis
python -m py_compile src/tools/*.py
```

### Problemas de memoria
```bash
# Verifica el archivo de memoria
cat agent_memory.json | python -m json.tool

# Limpia la memoria
rm agent_memory.json
```

## 🔌 Integración de MCP

Para habilitar servidores MCP:

1. Configura `MCP_ENABLED=true` en `.env`
2. Configura servidores en `mcp_servers.json`
3. Reinicia el agente

Consulta [Guía de Integración de MCP](MCP_INTEGRATION.md) para configuración detallada.

## 📚 Próximos Pasos

- **Aprende Filosofía**: [Filosofía del Proyecto](PHILOSOPHY.md)
- **Explora MCP**: [Integración de MCP](MCP_INTEGRATION.md)
- **Multi-Agente**: [Protocolo de Swarm](SWARM_PROTOCOL.md)
- **Avanzado**: [Características Zero-Config](ZERO_CONFIG.md)
- **Hoja de Ruta**: [Hoja de Ruta de Desarrollo](ROADMAP.md)

---

**¿Preguntas?** Consulta el [Índice Completo](README.md) o abre un issue en GitHub.
