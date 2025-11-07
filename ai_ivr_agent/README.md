# AI IVR Agent (MCP-Enabled)

This is a fully modular AI IVR platform that uses the **Model Context Protocol (MCP)** so you can attach ANY external API as a tool — Epic FHIR, Azure Speech, Email providers, CRMs, insurance databases, or future APIs.

The IVR supports:

✅ Azure Speech (ASR + TTS)  
✅ Epic OAuth → FHIR appointments  
✅ Email appointment confirmations  
✅ Localized customer authentication  
✅ Logging + summarization  
✅ Future API integration through MCP tools (no IVR code changes)

---

# ✅ How MCP is used in this project

The IVR does **not** call Epic / Azure / Email directly.  
Instead it calls **MCP tools**, and each external API is a separate server:

