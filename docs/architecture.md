# Notas de arquitectura

## Visión general

Este sistema conecta tres servicios externos en un único pipeline RAG de voz:

```
[Micrófono usuario] → [ElevenLabs Agent] → [RAG Tool] → [Qdrant] → [ElevenLabs Agent] → [HeyGen Avatar] → [Navegador]
```

## Componentes

### 1. Base de conocimiento (Qdrant)
- Los documentos se dividen en chunks y se indexan offline via `ingest.py`
- Modelo de embeddings: `BAAI/bge-m3` (1024 dimensiones, multilingüe)
- Recuperación: MMR (Maximal Marginal Relevance) con k=6, fetch_k=20
- MMR reduce la redundancia entre chunks devueltos

### 2. ElevenLabs Conversational Agent
- Gestiona STT (speech-to-text) y TTS (text-to-speech)
- Contiene el system prompt que define la persona y las restricciones del asistente
- Tiene una herramienta personalizada `retrieve_context` que se activa cuando el usuario hace una pregunta
- La llamada a la herramienta llega al backend RAG e inyecta los chunks recuperados como contexto

### 3. HeyGen LiveAvatar
- Conectado a ElevenLabs via `elevenlabs_agent_config` nativo (sin piping manual de audio)
- Corre en modo LITE sobre LiveKit WebRTC
- Un viewer HTML local renderiza el vídeo + audio del avatar en el navegador

## Decisiones de diseño

**¿Por qué MMR en lugar de búsqueda por similitud simple?**
Los documentos clínicos repiten con frecuencia la misma información en distintas secciones. MMR garantiza que los chunks recuperados sean a la vez relevantes y diversos, reduciendo el contexto redundante enviado al LLM.

**¿Por qué BAAI/bge-m3?**
Alto rendimiento multilingüe (español/inglés), embeddings densos de alta calidad en 1024 dimensiones, y buenos resultados en recuperación de dominio específico sin fine-tuning.

**¿Por qué la integración nativa ElevenLabs↔HeyGen?**
Las versiones anteriores (v11–v13) usaban conexiones WebSocket manuales y resampleo de audio PCM (16kHz→24kHz). El parámetro nativo `elevenlabs_agent_config` elimina esto por completo — HeyGen gestiona el puente de audio de forma nativa, reduciendo latencia y complejidad.

**¿Por qué no está incluida la base de conocimiento?**
La base de conocimiento usada en producción contiene documentación clínica confidencial. El script `ingest.py` es completamente genérico y funciona con cualquier colección de PDFs.
