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
   pip install -r requirements.txt
   ```
   (Dependencies: `flask`, `python-dotenv`, `openai`, `numpy`, `scikit-learn`, `tiktoken`)

2. **Configuration**:
   Create a `.env` file in the root directory with the following variables:
   - `OPENAI_API_KEY`: Server's OpenAI API Key (optional - users can provide their own).
   - `APP_PASSWORD`: The password to access the app (optional - users can provide their own API key).
   - `FLASK_SECRET_KEY`: Secret key for Flask sessions (required for production - generate a strong random key).
   - `FLASK_ENV`: Set to `production` for secure cookies (required for HTTPS deployments).

3. **Run the Server**:
   ```bash
   ./start.sh
   ```
   Or manually:
   ```bash
   python app.py
   ```

4. **First Run**:
   On the first run, the application will process `Anti-Oedipus.txt` to generate embeddings for the search/chat system. This may take 1-2 minutes.

## Access

Open your browser to `http://localhost:5001`.

**Login Options:**
- Enter the server password (if `APP_PASSWORD` is set in `.env`)
- Enter your own OpenAI API key (stored securely in session, never on server)

Your API key is stored securely in an HTTP-only session cookie and is only used for your session.

## Deployment

For production deployment on Apache (e.g., NearlyFreeSpeech), see [DEPLOYMENT.md](DEPLOYMENT.md).

