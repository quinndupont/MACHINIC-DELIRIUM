# Anti-Oedipus Reader

A modern web application for reading *Anti-Oedipus* by Gilles Deleuze and Félix Guattari, featuring an AI-powered teaching assistant.

## Features

- **Modern Typography**: Clean, serif-based reading experience (Merriweather).
- **Reading Aids**: Dark mode, font size/family toggles.
- **AI "Define"**: Highlight any text to get a context-aware definition from "Deleuze".
- **Chat Sidebar**: Discuss the text with an AI persona of Gilles Deleuze, with direct citations from the book.
- **Secure**: Password protected with option to use your own OpenAI API key (stored securely in session).

## Setup

1. **Install Dependencies**:
   ```bash
   pip install openai  # For pure Python solution (recommended)
   # OR if using FAISS:
   # pip install openai numpy faiss-cpu
   ```
   **Recommended**: Use pure Python solution (only needs `openai`). See [PURE_PYTHON_SETUP.md](PURE_PYTHON_SETUP.md)

2. **Configuration**:
   Create a `.env` file in the root directory with the following variables:
   - `OPENAI_API_KEY`: Server's OpenAI API Key (required for embeddings and LLM chat/define features).
   - `APP_PASSWORD`: The password to access the app (optional - users can provide their own API key).
   - `FLASK_SECRET_KEY`: Secret key for Flask sessions (required for production - generate a strong random key).
   - `FLASK_ENV`: Set to `production` for secure cookies (required for HTTPS deployments).

3. **Build Index** (Required for RAG):
   **Option A: Pure Python (Recommended - no FAISS/NumPy needed)**:
   ```bash
   python build_pure_python.py Anti-Oedipus.md
   ```
   Creates: `chunks.json` and `embeddings.json`
   
   **Option B: FAISS (if FAISS available)**:
   ```bash
   python build_faiss_openai.py Anti-Oedipus.md
   ```
   Creates: `faiss_index.bin` and `chunks.json`
   
   **Note**: 
   - This step only needs to be run once (or when the markdown file changes)
   - Uses OpenAI embeddings (~$0.01-0.02 one-time cost)
   - Takes about 10-15 seconds to build
   - Creates ~1500 overlapping chunks of ~800 characters each

4. **Run the Server**:
   ```bash
   ./start.sh
   ```
   Or manually:
   ```bash
   python app.py
   ```

## Access

Open your browser to `http://localhost:5001`.

**Login Options:**
- Enter the server password (if `APP_PASSWORD` is set in `.env`)
- Enter your own OpenAI API key (stored securely in session, never on server)

Your API key is stored securely in an HTTP-only session cookie and is only used for your session.

## Deployment

- **PHP Deployment**: See [PHP_DEPLOYMENT.md](PHP_DEPLOYMENT.md) for Apache/PHP setup and production configuration
- **FAISS Installation**: See [INSTALL_FAISS.md](INSTALL_FAISS.md) if you encounter installation issues

