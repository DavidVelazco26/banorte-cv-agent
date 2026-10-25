# Reto Banorte — etapa 2: herramientas y function calling



## ¿Qué cambió?

- `app/tools.py` (**nuevo**): cuatro herramientas de consulta **solo lectura**: `get_professional_profile`, `search_projects`, `get_project_details`, `get_technical_skills`.
- `app/agent.py` (**actualizado**): ciclo Responses API de `function_call` → ejecución local autorizada → `function_call_output` → respuesta final. Máximo 3 rondas de herramientas y 6 llamadas. Suma los tokens consumidos en todas las solicitudes. Primero requiere al menos una herramienta para fundamentar la respuesta.
- `tests/test_tools.py` (**nuevo**): pruebas de argumentos inválidos, consulta de CV y ciclo de function calling **simulado** sin gastar tokens.
- `requirements-dev.txt` (**actualizado**): agrega `pytest-asyncio`.
- `.env.example`: modelo predeterminado sugerido `gpt-6-luna`.

## En tu computadora Windows

1. Detén el servidor Uvicorn anterior con `Ctrl+C`.
2. Haz una **copia de seguridad** de la carpeta de proyecto actual. Descomprime este ZIP en otra carpeta y ábrela en VS Code, o copia los cuatro archivos modificados a tu carpeta actual.
3. En PowerShell, entra a la carpeta raíz del proyecto (la que contiene `app`, `data`, `requirements-dev.txt`) y activa el entorno virtual `LLMs` que ya tenías. No escribas `(LLMs) PS C:\...>`: eso es el prompt, no un comando.

```powershell
cd "C:\Users\David Velazco\Documents\Development\Banorte_Agente_CV_Dos_Proyectos\banorte-agente-cv"
& "C:\Users\David Velazco\Documents\Development\LLMs\Scripts\Activate.ps1"
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

> Si abriste la **nueva** carpeta descomprimida, ajusta únicamente el `cd` a esa carpeta.

4. En la **Terminal 1**, configura tu clave API sin imprimirla y arranca Uvicorn:

```powershell
$secureKey = Read-Host "API key de OpenAI" -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new("", $secureKey).Password
$env:LLM_BASE_URL = "https://api.openai.com/v1"
$env:LLM_MODEL = "gpt-6-luna"
$env:AGENT_API_KEY = ""    # SOLO para pruebas en localhost, NO para nube
python -m uvicorn app.main:app --reload
```

5. En la **Terminal 2**, prueba una pregunta de proyectos:

```powershell
$body = @{
    model = "cv-agent-v1"
    input = "¿Cuáles son los dos proyectos de José David y en qué consisten?"
    stream = $false
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/v1/responses" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

$response.output[0].content[0].text
```

6. Observa la **Terminal 1**: debería registrar al menos una línea `tool=search_projects success=True` (puede escoger otra herramienta, pues lo decide el modelo). **No necesitas escribir el nombre de una herramienta en PowerShell**; el modelo hace la selección y el backend la ejecuta.

7. Haz una segunda consulta:

```powershell
$body = @{
    model = "cv-agent-v1"
    input = "¿Qué tecnologías de IA generativa aparecen en su experiencia?"
    stream = $false
} | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/responses" -Method POST -ContentType "application/json" -Body $body
$response.output[0].content[0].text
```

## Verificación y limitaciones

- **17 pruebas locales** superadas al crear esta versión. Entre ellas, una simulación de un turno de function calling. Todavía necesitas verificarlo con tu **API real de Luna** en tu computadora.
- Se mantiene `POST /v1/responses` y la continuidad `previous_response_id` en memoria, sin base persistente.
- El streaming es SSE **diferido**, no de tokens en tiempo real. El endpoint implementa un **subconjunto textual** de Open Responses, no una conformidad completa certificada.
- No se ha desplegado esta versión en la nube, ni probado aún contra la interfaz de Banorte.
- `projects.json` es un borrador público a revisar antes de subirlo a GitHub, especialmente por la información industrial, las autorías y los resultados sin métricas confirmadas.
- **Nunca** publiques `OPENAI_API_KEY`. Para internet configura una `AGENT_API_KEY` larga y diferente.

## Próximo hito después de las pruebas

1. Obtener una respuesta real con herramientas y registrar las llamadas en consola.
2. Agregar pruebas de grounding y ataques de prompt injection, y registrar latencia/tokens.
3. Probar Docker.
4. Desplegar en HTTPS, comprobar la compatibilidad de Open Responses con Banorte y publicar GitHub tras revisar privacidad.
