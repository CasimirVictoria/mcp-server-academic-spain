# mcp-server-academic-spain 🔬🇪🇸

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-blue.svg)](https://modelcontextprotocol.io/)

An open-source **Model Context Protocol (MCP) server** for unified scientific literature search across Spanish academic repositories (**Dialnet**, **Teseo**, **CSIC**) and global scientific databases (**PubMed**, **OpenAlex**, **Europe PMC**, **Semantic Scholar**).

---

## ✨ Features

- **🇪🇸 Spanish Academic Repositories:** Direct querying of Dialnet, Teseo (doctoral theses), and CSIC repositories.
- **🌐 Global Open Access Databases:** Integrated searches across PubMed, OpenAlex, Europe PMC, and Semantic Scholar.
- **📊 Hybrid Relevance Ranking:** Sorts results using lexical match, journal impact score, citation count, and recency.
- **📥 Paper Download Helper:** Direct retrieval of Open Access and institutional full-text PDFs.

---

## 🛠️ Tools

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `search_academic_spain` | `query` (string), `max_results` (int, default 5) | Searches Spanish and international databases with hybrid scoring. |
| `unified_search` | `query` (string), `sources` (list of strings), `max_results` (int) | Multi-source academic query across selected scientific repositories. |
| `download_paper` | `url` (string) or `doi` (string), `filename` (optional string) | Downloads full-text research paper PDF to local workspace directory. |

---

## ⚙️ MCP Configuration

Add to your `mcp_config.json`:

```json
{
  "mcpServers": {
    "academic-spain": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/mcp-server-academic-spain",
        "server.py"
      ]
    }
  }
}
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
